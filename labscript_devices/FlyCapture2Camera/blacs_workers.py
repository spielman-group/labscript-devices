#####################################################################
#                                                                   #
# /labscript_devices/FlyCapture2Camera/blacs_workers.py             #
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
# Original PyCapture2_camera_server by dsbarker
# Ported to BLACS worker by dihm

import numpy as np
from labscript_utils import dedent
from enum import IntEnum

from labscript_devices.TriggerableCamera.blacs_workers import (
    TriggerableCameraInterface,
    TriggerableCameraWorker,
)

# PyCapture2 is imported when a FlyCapture2CameraInterface is created, not here: a
# subclass imports this module for its classes, and that must not require PyCapture2.
PyCapture2 = None


class FlyCapture2CameraInterface(TriggerableCameraInterface):
    """A FLIR camera driven through PyCapture2, found by serial number."""

    def __init__(self, serial_number):
        """Connect to the camera and send it the default Format7, Mode 0 settings."""
        global PyCapture2
        import PyCapture2

        ver = PyCapture2.getLibraryVersion()
        min_ver = (2, 12, 3, 31)  # first release with python 3.6 support
        if ver < min_ver:
            raise RuntimeError(
                f"PyCapture2 version {ver} is older than the required {min_ver}. "
                "Install a newer PyCapture2."
            )

        print(f"Connecting to SN:{serial_number} ...")
        bus = PyCapture2.BusManager()
        self.camera = PyCapture2.Camera()
        self.camera.connect(bus.getCameraFromSerialNumber(serial_number))

        # The fields of each property that get_attribute returns.
        self.get_props = [
            'present', 'absControl', 'absValue', 'onOff', 'autoManualMode', 'valueA',
            'valueB',
        ]

        fmts = {
            prop: getattr(PyCapture2.PIXEL_FORMAT, prop)
            for prop in dir(PyCapture2.PIXEL_FORMAT)
            if not prop.startswith('_')
        }
        self.pixel_formats = IntEnum('pixel_formats', fmts)

        # For a GigE camera, ensure the maximum packet size is used.
        cam_info = self.camera.getCameraInfo()
        if cam_info.interfaceType == PyCapture2.INTERFACE_TYPE.GIGE:
            print('Checking Packet size for GigE Camera...')
            # The generic camera is closed first, to avoid strange interactions.
            self.camera.disconnect()
            gige_camera = PyCapture2.GigECamera()
            gige_camera.connect(bus.getCameraFromSerialNumber(serial_number))
            mtu = gige_camera.discoverGigEPacketSize()
            if mtu <= 1500:
                msg = f"""WARNING: the maximum transmission unit (MTU) of the ethernet
                    NIC that camera SN:{serial_number} is connected to is only {mtu}.
                    Reliable operation is not expected. Enable jumbo frames on the
                    NIC."""
                print(dedent(msg))

            gige_pkt_size = gige_camera.getGigEProperty(
                PyCapture2.GIGE_PROPERTY_TYPE.GIGE_PACKET_SIZE
            )
            if gige_pkt_size.value != mtu:
                gige_pkt_size.value = mtu
                gige_camera.setGigEProperty(gige_pkt_size)
                print(f"  Packet size set to {mtu}")
            else:
                print(f"  GigE Packet size is {gige_pkt_size.value}")

            gige_camera.disconnect()
            self.camera.connect(bus.getCameraFromSerialNumber(serial_number))

        config = self.camera.getConfiguration()
        config.grabTimeout = 1000  # in ms
        config.highPerformanceRetrieveBuffer = True
        self.camera.setConfiguration(config)

        fmt7_info, supported = self.camera.getFormat7Info(0)
        if supported:
            # Format7 is entered by sending custom image settings; the defaults are the
            # full sensor size and MONO8 pixels.
            print('Initializing to default Format7, Mode 0 configuration...')
            fmt7_default = PyCapture2.Format7ImageSettings(
                0,
                0,
                0,
                fmt7_info.maxWidth,
                fmt7_info.maxHeight,
                self.pixel_formats['MONO8'].value,
            )
            self._send_format7_config(fmt7_default)
        else:
            msg = """This camera does not support Format7, Mode 0 custom image
                configuration, which the FlyCapture2Camera driver needs."""
            raise RuntimeError(dedent(msg))

    def set_attributes(self, attributes):
        """Set each attribute; TriggerMode and ImageMode have setters of their own."""
        for prop, vals in attributes.items():
            if prop == 'TriggerMode':
                self.set_trigger_mode(vals)

            elif prop == 'ImageMode':
                self.set_image_mode(vals)

            else:
                self.set_attribute(prop, vals)

    # Allowed keys of trig_dict: 'onOff': bool, 'polarity': 0,1, 'source': int,
    # 'mode': int.
    def set_trigger_mode(self, trig_dict):
        trig_mode = self.camera.getTriggerMode()
        for k, v in trig_dict.items():
            setattr(trig_mode, k, v)

        try:
            self.camera.setTriggerMode(trig_mode)
        except Exception as e:
            msg = f"Failed to set the trigger mode to {trig_dict}"
            raise Exception(msg) from e

    # Allowed keys of image_settings: 'pixelFormat': a pixel format name such as
    # 'MONO8', 'offsetX': int, 'offsetY': int, 'width': int, 'height': int.
    def set_image_mode(self, image_settings):
        image_info, supported = self.camera.getFormat7Info(0)
        Hstep = image_info.offsetHStepSize
        Vstep = image_info.offsetVStepSize
        image_dict = image_settings.copy()
        if supported:
            image_mode, packetSize, percentage = self.camera.getFormat7Configuration()
            image_mode.mode = 0

            # Round the offsets and sizes down to a multiple of the offset step size,
            # horizontal for X and width, vertical for Y and height.
            if 'offsetX' in image_dict:
                image_dict['offsetX'] -= image_dict['offsetX'] % Hstep
            if 'offsetY' in image_dict:
                image_dict['offsetY'] -= image_dict['offsetY'] % Vstep
            if 'width' in image_dict:
                image_dict['width'] -= image_dict['width'] % Hstep
            if 'height' in image_dict:
                image_dict['height'] -= image_dict['height'] % Vstep

            # The pixel format is a name here; the camera takes its enum value.
            if 'pixelFormat' in image_dict:
                fmt = image_dict.pop('pixelFormat')
                image_mode.pixelFormat = self.pixel_formats[fmt].value

            for k, v in image_dict.items():
                setattr(image_mode, k, v)

            self._send_format7_config(image_mode)

        else:
            msg = """This camera does not support Format7, Mode 0 custom image
                configuration, which the FlyCapture2Camera driver needs."""
            raise RuntimeError(dedent(msg))

    # Allowed keys of value: 'onOff', 'autoManualMode', 'absControl', 'onePush' (bool),
    # 'absValue' (float), 'valueA', 'valueB' (int). Generally absControl should be used
    # to configure settings. Invalid settings tend to coerce instead of raising.
    def set_attribute(self, name, value):
        try:
            prop = self.camera.getProperty(getattr(PyCapture2.PROPERTY_TYPE, name))

            for key, val in value.items():
                setattr(prop, key, val)
            self.camera.setProperty(prop)
        except Exception as e:
            msg = f"Failed to set attribute {name} to {value}"
            raise Exception(msg) from e

    def get_attributes_as_dict(self, visibility_level, writeable_only=True):
        """Return all the attributes as nested dicts; both arguments are ignored."""
        props = {}
        prop_names = {
            prop
            for prop in dir(PyCapture2.PROPERTY_TYPE)
            if not prop.startswith('_') and not prop == 'UNSPECIFIED_PROPERTY_TYPE'
        }

        props['TriggerMode'] = {}
        trig_mode = self.camera.getTriggerMode()
        trig_props = [prop for prop in dir(trig_mode) if not prop.startswith('_')]
        props['ImageMode'] = {}
        image_mode, packetSize, percentage = self.camera.getFormat7Configuration()
        image_props = [prop for prop in dir(image_mode) if not prop.startswith('_')]

        for name in prop_names:
            props[name] = self.get_attribute(name)

        for name in trig_props:
            props['TriggerMode'][name] = getattr(trig_mode, name)

        # The pixel format is read separately, as its name rather than its number.
        if 'pixelFormat' in image_props:
            image_props.remove('pixelFormat')
            props['ImageMode']['pixelFormat'] = self.pixel_formats(
                image_mode.pixelFormat
            ).name
        for name in image_props:
            props['ImageMode'][name] = getattr(image_mode, name)

        return props

    def get_attribute(self, name):
        """Return the fields of property `name` that `get_props` lists, as a dict."""
        try:
            prop_dict = {}
            prop = self.camera.getProperty(getattr(PyCapture2.PROPERTY_TYPE, name))
            for key in self.get_props:
                prop_dict[key] = getattr(prop, key)
            return prop_dict
        except Exception as e:
            raise Exception(f"Failed to get attribute {name}") from e

    def configure_acquisition(self, continuous=True, buffer_count=None):
        """Set the buffer count (10 by default) and grab mode, and start capture."""
        if buffer_count is None:
            buffer_count = 10
        config = self.camera.getConfiguration()
        config.numBuffers = buffer_count
        # DROP_FRAMES keeps only the most recent frames in the buffer; BUFFER_FRAMES
        # keeps all the acquired frames and errors if the buffer is exceeded.
        if continuous:
            config.grabMode = PyCapture2.GRAB_MODE.DROP_FRAMES
            self.camera.setConfiguration(config)
        else:
            config.grabMode = PyCapture2.GRAB_MODE.BUFFER_FRAMES
            self.camera.setConfiguration(config)

        image_mode, packetSize, percentage = self.camera.getFormat7Configuration()

        # _decode_image_data formats each grabbed image with these, so grab needs this
        # call first.
        self.width = image_mode.width
        self.height = image_mode.height
        self.pixelFormat = self.pixel_formats(image_mode.pixelFormat).name

        self.camera.startCapture()

    def grab(self):
        result = self.camera.retrieveBuffer()

        img = result.getData()

        return self._decode_image_data(img)

    def _decode_image_data(self, img):
        """Return a copy of the 1-D buffer `img`, shaped `height` by `width`."""
        pix_fmt = self.pixelFormat
        if pix_fmt.startswith('MONO'):
            if pix_fmt.endswith('8'):
                dtype = 'uint8'
            else:
                dtype = 'uint16'
            image = np.frombuffer(img, dtype=dtype).reshape(self.height, self.width)
        else:
            msg = f"""Pixel format {pix_fmt} is not supported, only MONO formats are. To
                add another, convert the returned uint8 data to the desired format in
                _decode_image_data."""
            raise ValueError(dedent(msg))
        return image.copy()

    def _send_format7_config(self, image_config):
        """Send `image_config` to the camera if it validates."""
        try:
            fmt7PktInfo, valid = self.camera.validateFormat7Settings(image_config)
            if valid:
                self.camera.setFormat7ConfigurationPacket(
                    fmt7PktInfo.recommendedBytesPerPacket, image_config
                )
        except PyCapture2.Fc2error as e:
            raise RuntimeError('Failed to configure the Format7 image settings') from e

    def is_transient_grab_error(self, exception):
        """A frame not yet arrived is an Fc2error, like every fault; all are retried."""
        return isinstance(exception, PyCapture2.Fc2error)

    def stop_acquisition(self):
        self.camera.stopCapture()

    def close(self):
        self.camera.disconnect()


class FlyCapture2CameraWorker(TriggerableCameraWorker):
    """Worker for FlyCapture2CameraInterface."""

    interface_class = FlyCapture2CameraInterface
