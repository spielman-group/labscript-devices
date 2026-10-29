#####################################################################
#                                                                   #
# /labscript_devices/DummyCamera/blacs_workers.py                   #
#                                                                   #
# Copyright 2026, Ian Spielman and contributors                     #
#                                                                   #
# This file is part of labscript_devices, in the labscript suite    #
# (see http://labscriptsuite.org), and is licensed under the        #
# Simplified BSD License. See the license.txt file in the root of   #
# the project for the full license.                                 #
#                                                                   #
#####################################################################


from labscript_devices.DummyCamera.sensor import blank_image, sensor_size
from labscript_devices.common.triggerable_camera.blacs_workers import (
    DictAttributesMixin,
    CameraInterface,
    TriggerableCameraWorker,
)


class DummyCameraInterface(DictAttributesMixin, CameraInterface):
    """A camera that grabs the shot's compiled images; in manual mode, blank frames."""

    # Marks the images as mock data. It is an attribute saved beside them, not a
    # watermark over their pixels, which every frame would carry and so make the OD
    # there 0/0.
    identifying_attributes = {'mock_data': True}

    def __init__(self, serial_number=None):
        print("Starting device worker as a dummy camera")
        self.attributes = dict(self.identifying_attributes)
        self.images = None
        self.index = 0

    def configure_acquisition(self, continuous=True, buffer_count=None):
        # A continuous acquisition is manual mode, with no shot behind it. Images left
        # by the last shot are not live, so grab must not return them.
        if continuous:
            self.images = None
        self.index = 0

    def load_images(self, images):
        """Take the shot's compiled images, to be returned one per grab."""
        self.images = images
        self.index = 0

    def snap(self):
        """Return a blank frame of the sensor's size, for manual mode."""
        return blank_image(*sensor_size(self.attributes))

    def grab(self):
        if self.images is None:
            return self.snap()
        image = self.images[self.index]
        self.index += 1
        return image

    def stop_acquisition(self):
        pass

    def close(self):
        pass


class DummyCameraWorker(TriggerableCameraWorker):
    """Worker for DummyCameraInterface; it loads the shot's compiled images into it."""

    interface_class = DummyCameraInterface

    def load_shot_data(self, shot_file):
        """Load the shot's compiled images into the camera."""
        group = shot_file['devices'][self.device_name]
        images = group['IMAGES'][:] if 'IMAGES' in group else None
        self.camera.load_images(images)

    def transition_to_buffered(self, device_name, h5_file, front_panel_values, fresh):
        return_value = TriggerableCameraWorker.transition_to_buffered(
            self, device_name, h5_file, front_panel_values, fresh
        )
        # mock_data is saved even when saved_attribute_visibility_level is None,
        # and goes last so that a camera attribute of the same name cannot override it.
        self.attributes_to_save = dict(
            self.attributes_to_save or {}, **DummyCameraInterface.identifying_attributes
        )
        return return_value
