#####################################################################
#                                                                   #
# /labscript_devices/IMAQdxCamera/blacs_workers.py                  #
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

import sys
from types import MethodType

import numpy as np

from labscript_utils import dedent
from labscript_devices.TriggerableCamera.blacs_workers import (
    TriggerableCameraInterface,
    TriggerableCameraWorker,
)

# nivision is imported when an IMAQdxCameraInterface is created, not here: a subclass
# imports this module for its classes, and that must not require nivision.
nv = None


def _monkeypatch_imaqdispose():
    """Fix a memory leak in pynivision, whose project is no longer active."""

    import nivision.core
    import ctypes

    _imaqDispose = nivision.core._imaqDispose

    def imaqDispose(obj):
        if getattr(obj, "_contents", None) is not None:
            _imaqDispose(ctypes.byref(obj._contents))
            obj._contents = None
        if getattr(obj, "value", None) is not None:
            _imaqDispose(obj)
            obj.value = None
        # This is the bugfix: pointers as raw ints were not being disposed:
        if isinstance(obj, int):
            _imaqDispose(obj)

    nivision.core.imaqDispose = nv.imaqDispose = imaqDispose


class IMAQdxCameraInterface(TriggerableCameraInterface):
    """A camera driven through nivision's IMAQdx functions, found by serial number."""

    def __init__(self, serial_number):
        global nv
        import nivision as nv
        _monkeypatch_imaqdispose()

        print("Finding camera...")
        for cam in nv.IMAQdxEnumerateCameras(True):
            if serial_number == (cam.SerialNumberHi << 32) + cam.SerialNumberLo:
                self.camera = cam
                break
        else:
            msg = (
                f"No connected camera has serial number {serial_number:X}. Check that "
                "the camera is connected and that serial_number is right."
            )
            raise Exception(msg)
        print("Connecting to camera...")
        self.imaqdx = nv.IMAQdxOpenCamera(
            self.camera.InterfaceName, nv.IMAQdxCameraControlModeController
        )
        # Keep an img attribute so we don't have to create it every time
        self.img = nv.imaqCreateImage(nv.IMAQ_IMAGE_U16)

    def set_attribute(self, name, value):
        # A str is encoded to bytes for IMAQdx; value stays as given, for the error
        # message.
        _value = value
        if isinstance(_value, str):
            _value = _value.encode('utf8')
        try:
            nv.IMAQdxSetAttribute(self.imaqdx, name.encode('utf8'), _value)
        except Exception as e:
            msg = f"Failed to set attribute {name} to {value}"
            raise Exception(msg) from e

    def get_attribute_names(self, visibility_level, writeable_only=True):
        """Return the readable attributes' names; by default only the writeable ones."""
        visibilities = {
            'simple': nv.IMAQdxAttributeVisibilitySimple,
            'intermediate': nv.IMAQdxAttributeVisibilityIntermediate,
            'advanced': nv.IMAQdxAttributeVisibilityAdvanced,
        }
        visibility_level = visibilities[visibility_level.lower()]
        attributes = []
        for a in nv.IMAQdxEnumerateAttributes2(self.imaqdx, b'', visibility_level):
            if writeable_only and not a.Writable:
                continue
            if not a.Readable:
                continue
            attributes.append(a.Name.decode('utf8'))
        return attributes

    def get_attribute(self, name):
        try:
            value = nv.IMAQdxGetAttribute(self.imaqdx, name.encode('utf8'))
            if isinstance(value, nv.core.IMAQdxEnumItem):
                value = value.Name
            if isinstance(value, bytes):
                value = value.decode('utf8')
            return value
        except Exception as e:
            raise Exception(f"Failed to get attribute {name}") from e

    def snap(self):
        nv.IMAQdxSnap(self.imaqdx, self.img)
        return self._decode_image_data(self.img)

    def configure_acquisition(self, continuous=True, buffer_count=None):
        if buffer_count is None:
            buffer_count = 5
        nv.IMAQdxConfigureAcquisition(
            self.imaqdx, continuous=continuous, bufferCount=buffer_count
        )
        nv.IMAQdxStartAcquisition(self.imaqdx)

    def grab(self):
        nv.IMAQdxGrab(self.imaqdx, self.img, waitForNextBuffer=True)
        return self._decode_image_data(self.img)

    def is_transient_grab_error(self, exception):
        """IMAQdx reports a frame that has not arrived yet as a timeout."""
        return (
            isinstance(exception, nv.ImaqDxError)
            and exception.code == nv.IMAQdxErrorTimeout.value
        )

    def is_skippable_grab_error(self, exception):
        """Any error that IMAQdx itself reports, a timeout included."""
        return isinstance(exception, nv.ImaqDxError)

    def stop_acquisition(self):
        nv.IMAQdxStopAcquisition(self.imaqdx)
        nv.IMAQdxUnconfigureAcquisition(self.imaqdx)

    def _decode_image_data(self, img):
        img_array = nv.imaqImageToArray(img)
        img_array_shape = (img_array[2], img_array[1])
        # bitdepth in bytes
        bitdepth = len(img_array[0]) // (img_array[1] * img_array[2])
        dtype = {1: np.uint8, 2: np.uint16, 4: np.uint32}[bitdepth]
        data = np.frombuffer(img_array[0], dtype=dtype).reshape(img_array_shape)
        return data.copy()

    def close(self):
        nv.IMAQdxCloseCamera(self.imaqdx)


class IMAQdxCameraWorker(TriggerableCameraWorker):
    """Worker for IMAQdxCameraInterface; a subclass may name another camera class."""

    interface_class = IMAQdxCameraInterface

    def init(self):
        super().init()
        # A camera without get_attributes_as_dict, such as one that does not subclass
        # TriggerableCameraInterface, is given that class's, with a deprecation warning.
        # Here, not in get_camera, which a lab's own worker may override.
        if not hasattr(self.camera, 'get_attributes_as_dict'):
            msg = f"""Warning: {type(self.camera).__name__} does not subclass
                TriggerableCameraInterface. Driving such a camera by subclassing
                IMAQdxCameraWorker is deprecated. Use the TriggerableCamera
                device, with a camera class that subclasses
                TriggerableCameraInterface and a worker that subclasses
                TriggerableCameraWorker."""
            print(dedent(msg), file=sys.stderr)
            self.camera.get_attributes_as_dict = MethodType(
                TriggerableCameraInterface.get_attributes_as_dict, self.camera
            )
