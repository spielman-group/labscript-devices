#####################################################################
#                                                                   #
# /labscript_devices/SpinnakerCamera/blacs_workers.py               #
#                                                                   #
# Copyright 2019, Monash University and contributors                #
#                                                                   #
# This file is part of labscript_devices, in the labscript suite    #
# (see http://labscriptsuite.org), and is licensed under the        #
# Simplified BSD License. See the license.txt file in the root of   #
# the project for the full license.                                 #
#                                                                   #
#####################################################################

# Original imaqdx_camera server by dt, with modifications by rpanderson and cbillington.
# Refactored as a BLACS worker by cbillington
# PsSpin implementation by spe

import numpy as np
from labscript_utils import dedent
from time import sleep

from labscript_devices.common.triggerable_camera.blacs_workers import (
    CameraInterface,
    TriggerableCameraWorker,
)


class SpinnakerCameraInterface(CameraInterface):
    """A FLIR camera driven through PySpin."""

    def __init__(self, serial_number):
        """Connect to the camera with this serial number, an int or a str."""
        # PySpin is imported when an interface is created, not at module level, so
        # importing this module does not require PySpin.
        global PySpin
        import PySpin

        self.system = PySpin.System.GetInstance()

        camList = None
        try:
            ver = self.system.GetLibraryVersion()
            min_ver = (1, 23, 0, 27)  # first release with python 3.6 support
            if (ver.major, ver.minor, ver.type, ver.build) < min_ver:
                raise RuntimeError(
                    f"PySpin version {ver.major}.{ver.minor}.{ver.type}.{ver.build} is "
                    f"older than the required {'.'.join(map(str, min_ver))}. "
                    "Install a newer PySpin."
                )

            camList = self.system.GetCameras()
            numCams = camList.GetSize()

            if numCams == 0:
                raise ValueError(
                    'No cameras found. Check that the camera is connected and powered on.'
                )

            if isinstance(serial_number, int):
                self.camera = camList.GetBySerial(f"{serial_number:d}")
            else:
                self.camera = camList.GetBySerial(serial_number)
            self.camera.Init()
        except Exception:
            # The system is released only once no camera is held.
            self.camera = None
            if camList is not None:
                camList.Clear()
            self.system.ReleaseInstance()
            raise
        camList.Clear()

        # The timeout grab passes to GetNextImage, in ms.
        self.timeout = 5000

    def get_attribute_names(self, visibility):
        """Return readable feature names as Category::Name, at `visibility` or below."""
        # GenICam's visibility levels, which Spinnaker implements; an Invisible
        # feature is never saved.
        max_visibility = {
            'simple': PySpin.Beginner,
            'intermediate': PySpin.Expert,
            'advanced': PySpin.Guru,
        }[visibility.lower()]
        names = []

        def get_node_names_in_category(node_category, prefix=''):
            for node_feature in node_category.GetFeatures():
                if (
                    not PySpin.IsAvailable(node_feature)
                    or not PySpin.IsReadable(node_feature)
                ):
                    continue

                feature_name = node_feature.GetName()

                # Category nodes must be dealt with separately, to retrieve their
                # subnodes recursively.
                if node_feature.GetPrincipalInterfaceType() == PySpin.intfICategory:
                    get_node_names_in_category(
                        PySpin.CCategoryPtr(node_feature), prefix=feature_name + '::'
                    )
                elif node_feature.GetVisibility() <= max_visibility:
                    names.append(prefix + feature_name)

        node = self.camera.GetNodeMap()
        get_node_names_in_category(PySpin.CCategoryPtr(node.GetNode('Root')))

        return names

    def get_attribute(self, name):
        return self._get_node_value(self.camera.GetNodeMap(), name)

    def _get_node_value(self, nodemap, name):
        """Return the feature's value, or None if it is unavailable or unreadable."""
        node = nodemap.GetNode(name.split('::')[-1])

        if PySpin.IsAvailable(node) and PySpin.IsReadable(node):
            if node.GetPrincipalInterfaceType() == PySpin.intfIInteger:
                return PySpin.CIntegerPtr(node).GetValue()
            elif node.GetPrincipalInterfaceType() == PySpin.intfIFloat:
                return PySpin.CFloatPtr(node).GetValue()
            elif node.GetPrincipalInterfaceType() == PySpin.intfIBoolean:
                return PySpin.CBooleanPtr(node).GetValue()
            else:
                return PySpin.CValuePtr(node).ToString()

    def set_attribute(self, name, value):
        self._set_node_value(self.camera.GetNodeMap(), name, value)

    def set_stream_attribute(self, name, value):
        self._set_node_value(self.camera.GetTLStreamNodeMap(), name, value)

    def _set_node_value(self, nodemap, name, value):
        name = name.split('::')
        node = nodemap.GetNode(name[-1])

        if PySpin.IsAvailable(node) and PySpin.IsWritable(node):
            if node.GetPrincipalInterfaceType() == PySpin.intfIInteger:
                PySpin.CIntegerPtr(node).SetValue(value)
            elif node.GetPrincipalInterfaceType() == PySpin.intfIFloat:
                PySpin.CFloatPtr(node).SetValue(value)
            elif node.GetPrincipalInterfaceType() == PySpin.intfIBoolean:
                PySpin.CBooleanPtr(node).SetValue(value)
            else:
                PySpin.CValuePtr(node).FromString(value)

            sleep(0.05)
            # Sometimes the set does not take effect, so read the value back and warn
            # if it differs.
            name = '::'.join(name)
            return_value = self._get_node_value(nodemap, name)
            if return_value != value:
                print(
                    f"WARNING: setting attribute {name} to {value} failed; the camera "
                    f"reads back {return_value}."
                )
            else:
                print(f"Successfully set {name} to {return_value}.")
        else:
            print(
                f"WARNING: attribute {'::'.join(name)} is unavailable or not writable, "
                "so it was not set."
            )

    def snap(self):
        self.configure_acquisition(continuous=False, buffer_count=1)
        image = self.grab()
        self.camera.EndAcquisition()
        return image

    def grab(self):
        image_result = self.camera.GetNextImage(self.timeout)
        try:
            return self._decode_image_data(image_result.GetData())
        finally:
            image_result.Release()

    def trigger(self):
        """Execute a software trigger."""
        nodemap = self.camera.GetNodeMap()
        trigger_cmd = PySpin.CCommandPtr(nodemap.GetNode('TriggerSoftware'))
        if not PySpin.IsAvailable(trigger_cmd) or not PySpin.IsWritable(trigger_cmd):
            print(
                'WARNING: cannot execute a software trigger: TriggerSoftware is '
                'unavailable or not writable.'
            )
        else:
            trigger_cmd.Execute()

    def configure_acquisition(self, continuous=True, buffer_count=None):
        """Set the buffer count (10 if None) and the mode, then begin acquiring."""
        if buffer_count is None:
            buffer_count = 10
        # _decode_image_data formats each grabbed image with these, so grab needs this
        # call first.
        self.pix_fmt = self.get_attribute('PixelFormat')
        self.height = self.get_attribute('Height')
        self.width = self.get_attribute('Width')

        # Unless the camera settings are set properly, in continuous mode the camera
        # generally moves faster than BLACS, so the buffer fills up. With a Flea3 this
        # was not easily solved.
        if continuous:
            self.set_stream_attribute('StreamBufferCountMode', 'Manual')
            self.set_stream_attribute('StreamBufferCountManual', buffer_count)
            self.set_stream_attribute('StreamBufferHandlingMode', 'NewestFirst')
            self.set_attribute('AcquisitionMode', 'Continuous')
        elif buffer_count == 1:
            # StreamBufferCountMode 'Auto' was deprecated by Spinnaker version
            # 3.0.0.118, so 'Manual' is set.
            self.set_stream_attribute('StreamBufferCountMode', 'Manual')
            self.set_stream_attribute('StreamBufferCountManual', 1)
            self.set_stream_attribute('StreamBufferHandlingMode', 'OldestFirst')
            self.set_attribute('AcquisitionMode', 'SingleFrame')
        else:
            self.set_stream_attribute('StreamBufferCountMode', 'Manual')
            self.set_stream_attribute('StreamBufferCountManual', buffer_count)
            self.set_stream_attribute('StreamBufferHandlingMode', 'OldestFirst')
            self.set_attribute('AcquisitionMode', 'MultiFrame')
            self.set_attribute('AcquisitionFrameCount', buffer_count)

        self.camera.BeginAcquisition()

    def _decode_image_data(self, img):
        """Return a copy of the buffer `img`, shaped `height` by `width`."""
        if self.pix_fmt.startswith('Mono'):
            if self.pix_fmt.endswith('8'):
                dtype = 'uint8'
            else:
                dtype = 'uint16'
            image = np.frombuffer(img, dtype=dtype).reshape(self.height, self.width)
        else:
            msg = f"""Pixel format {self.pix_fmt} is not supported, only Mono formats
                are. To add another, convert the returned uint8 data to the desired
                format in _decode_image_data."""
            raise ValueError(dedent(msg))
        return image.copy()

    def stop_acquisition(self):
        print('Stopping acquisition...')
        self.camera.EndAcquisition()

        # This is supposed to provide debugging info, but it appears to be completely
        # useless.
        stream = self.camera.GetTLStreamNodeMap()
        num_frames = self._get_node_value(stream, 'StreamTotalBufferCount')
        failed_frames = self._get_node_value(stream, 'StreamFailedBufferCount')
        underrun_frames = self._get_node_value(stream, 'StreamBufferUnderrunCount')
        print(
            f"Stream info: {num_frames} frames acquired, {failed_frames} failed, "
            f"{underrun_frames} underrun"
        )

    def close(self):
        print('Closing down the camera...')
        self.camera.DeInit()
        self.system.ReleaseInstance()


class SpinnakerCameraWorker(TriggerableCameraWorker):
    """Worker for SpinnakerCameraInterface."""

    interface_class = SpinnakerCameraInterface
