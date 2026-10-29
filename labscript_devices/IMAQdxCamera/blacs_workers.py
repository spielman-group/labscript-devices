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

from labscript_utils import dedent
from labscript_devices.common.triggerable_camera.blacs_workers import (
    CameraInterface,
    TriggerableCameraWorker,
)

# The NI-IMAQdx bindings are imported when an IMAQdxCameraInterface is created, not
# here: a subclass imports this module for its classes, and that must not require the
# NI libraries.
nv = None


class IMAQdxCameraInterface(CameraInterface):
    """A camera driven through NI-IMAQdx, found by serial number."""

    def __init__(self, serial_number):
        global nv
        from labscript_devices.IMAQdxCamera import imaqdx as nv

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
            self.camera.InterfaceName.decode('utf8'),
            nv.IMAQdxCameraControlModeController,
        )
        # Keep an img attribute so we don't have to create it every time
        self.img = nv.imaqCreateImage(nv.IMAQ_IMAGE_U16, 0)

    def set_attribute(self, name, value):
        try:
            nv.IMAQdxSetAttribute(self.imaqdx, name, value)
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
        for a in nv.IMAQdxEnumerateAttributes2(self.imaqdx, '', visibility_level):
            if writeable_only and not a.Writable:
                continue
            if not a.Readable:
                continue
            attributes.append(a.Name.decode('utf8'))
        return attributes

    def get_attribute(self, name):
        try:
            return nv.IMAQdxGetAttribute(self.imaqdx, name)
        except Exception as e:
            raise Exception(f"Failed to get attribute {name}") from e

    def snap(self):
        nv.IMAQdxSnap(self.imaqdx, self.img)
        return nv.imaqImageToArray(self.img)

    def configure_acquisition(self, continuous=True, buffer_count=None):
        if buffer_count is None:
            buffer_count = 5
        nv.IMAQdxConfigureAcquisition(self.imaqdx, continuous, buffer_count)
        nv.IMAQdxStartAcquisition(self.imaqdx)

    def grab(self):
        nv.IMAQdxGrab(self.imaqdx, self.img, waitForNextBuffer=True)
        return nv.imaqImageToArray(self.img)

    def is_transient_grab_error(self, exception):
        """IMAQdx reports a frame that has not arrived yet as a timeout."""
        return (
            isinstance(exception, nv.IMAQdxError)
            and exception.code == nv.IMAQdxErrorTimeout
        )

    def is_skippable_grab_error(self, exception):
        """Any error that IMAQdx itself reports, a timeout included."""
        return isinstance(exception, nv.IMAQdxError)

    def stop_acquisition(self):
        nv.IMAQdxStopAcquisition(self.imaqdx)
        nv.IMAQdxUnconfigureAcquisition(self.imaqdx)

    def close(self):
        nv.IMAQdxCloseCamera(self.imaqdx)
        nv.imaqDispose(self.img)


class IMAQdxCameraWorker(TriggerableCameraWorker):
    """Worker for IMAQdxCameraInterface; a subclass may name another camera class."""

    interface_class = IMAQdxCameraInterface

    def init(self):
        super().init()
        # A camera without get_attributes_as_dict, such as one that does not subclass
        # CameraInterface, is given that class's, with a deprecation warning.
        # Here, not in get_camera, which a lab's own worker may override.
        if not hasattr(self.camera, 'get_attributes_as_dict'):
            msg = f"""Warning: {type(self.camera).__name__} does not subclass
                CameraInterface. Driving such a camera by subclassing
                IMAQdxCameraWorker is deprecated. Use the TriggerableCamera
                device, with a camera class that subclasses
                CameraInterface and a worker that subclasses
                TriggerableCameraWorker."""
            print(dedent(msg), file=sys.stderr)
            self.camera.get_attributes_as_dict = MethodType(
                CameraInterface.get_attributes_as_dict, self.camera
            )
