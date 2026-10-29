#####################################################################
#                                                                   #
# /labscript_devices/PylonCamera/blacs_workers.py                   #
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
# Ported to Pylon API by dihm

from labscript_devices.common.triggerable_camera.blacs_workers import (
    TriggerableCameraInterface,
    TriggerableCameraWorker,
)

# pylon and genicam are imported from pypylon when a PylonCameraInterface is created,
# not here: a subclass imports this module for its classes, and that must not require
# pypylon.
pylon = None
genicam = None


class PylonCameraInterface(TriggerableCameraInterface):
    """A Basler camera driven through pypylon, found by serial number."""

    def __init__(self, serial_number):
        global pylon
        global genicam
        from pypylon import pylon, genicam

        factory = pylon.TlFactory.GetInstance()
        print("Connecting to camera...")
        sn = pylon.CDeviceInfo()
        sn.SetSerialNumber(str(serial_number))
        self.camera = pylon.InstantCamera(factory.CreateDevice(sn))
        self.camera.Open()
        self.timeout = 1000  # in ms
        self.camera.RegisterConfiguration(
            pylon.SoftwareTriggerConfiguration(),
            pylon.RegistrationMode_ReplaceAll,
            pylon.Cleanup_Delete,
        )
        # Keep a nodeMap reference so we don't have to re-create a lot
        self.nodeMap = self.camera.GetNodeMap()

    def set_attributes(self, attributes):
        # Work on a copy: the ROI values are popped off it as they are set.
        attributes = attributes.copy()
        # Pylon cameras require the ROI settings to be done in the correct order. When
        # given, Width with OffsetX and Height with OffsetY are set first: the offset
        # ahead of the size if the current size fits at the new offset, else behind it.
        ROIx = ['Width', 'OffsetX']
        ROIy = ['Height', 'OffsetY']
        if set(ROIx).issubset(attributes):
            if attributes['OffsetX'] <= (self.camera.WidthMax() - self.camera.Width()):
                ROIx.reverse()
            ROIx_settings = [attributes.pop(k) for k in ROIx]
            for k, v in zip(ROIx, ROIx_settings):
                self.set_attribute(k, v)

        if set(ROIy).issubset(attributes):
            if attributes['OffsetY'] <= (self.camera.HeightMax() - self.camera.Height()):
                ROIy.reverse()
            ROIy_settings = [attributes.pop(k) for k in ROIy]
            for k, v in zip(ROIy, ROIy_settings):
                self.set_attribute(k, v)

        for k, v in attributes.items():
            self.set_attribute(k, v)

    def set_attribute(self, name, value):
        try:
            self.nodeMap.GetNode(name).SetValue(value)
        except Exception as e:
            msg = f"Failed to set attribute {name} to {value}"
            raise Exception(msg) from e

    def get_attributes_as_dict(self, visibility_level, writeable_only=True):
        """Return the attributes at a visibility level; writeable ones by default."""
        visibilities = {
            'simple': ['Beginner'],
            'intermediate': ['Beginner', 'Expert'],
            'advanced': ['Beginner', 'Expert', 'Guru'],
        }
        if writeable_only:
            modes = ['RW']
        else:
            modes = ['RW', 'RO']
        visibility_level = visibilities[visibility_level.lower()]
        attributes = []
        filters = [
            lambda n: n.GetNode().IsFeature(),
            lambda n: genicam.EVisibilityClass.ToString(n.GetNode().GetVisibility())
            in visibility_level,
            lambda n: genicam.EAccessModeClass.ToString(n.GetNode().GetAccessMode())
            in modes,
        ]
        params = filter(lambda n: all([f(n) for f in filters]), self.nodeMap.GetNodes())
        attributes = {}
        for n in params:
            try:
                attributes[n.GetNode().GetName()] = n.GetValue()
            except AttributeError:
                attributes[n.GetNode().GetName()] = n.ToString()
        return attributes

    def get_attribute(self, name):
        try:
            return self.nodeMap.GetNode(name).GetValue()
        except Exception as e:
            raise Exception(f"Failed to get attribute {name}") from e

    def snap(self):
        result = self.camera.GrabOne(self.timeout, pylon.TimeoutHandling_ThrowException)
        if result.GrabSucceeded():
            img = result.Array
            result.Release()
            return img
        else:
            raise RuntimeError(
                f'Snap error {result.ErrorCode}: {result.ErrorDescription}'
            )

    def configure_acquisition(self, continuous=True, buffer_count=None):
        """Start grabbing with LatestImageOnly if continuous, else OneByOne."""
        if buffer_count is None:
            buffer_count = 10
        self.camera.MaxNumBuffer = buffer_count
        if continuous:
            self.camera.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)
        else:
            self.camera.StartGrabbing(pylon.GrabStrategy_OneByOne)

    def grab(self):
        result = self.camera.RetrieveResult(
            self.timeout, pylon.TimeoutHandling_ThrowException
        )
        if result.GrabSucceeded():
            img = result.Array
            result.Release()
            return img
        else:
            raise RuntimeError(
                f'Grab error {result.ErrorCode}: {result.ErrorDescription}'
            )

    def is_transient_grab_error(self, exception):
        """Pylon reports a frame that has not arrived yet as a timeout."""
        return isinstance(exception, pylon.TimeoutException)

    def stop_acquisition(self):
        self.camera.StopGrabbing()

    def close(self):
        self.camera.Close()


class PylonCameraWorker(TriggerableCameraWorker):
    """Worker for PylonCameraInterface."""

    interface_class = PylonCameraInterface
