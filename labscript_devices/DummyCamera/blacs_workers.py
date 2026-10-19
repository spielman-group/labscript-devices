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
from labscript_devices.TriggerableCamera.blacs_workers import (
    DictAttributesMixin,
    TriggerableCameraInterface,
    TriggerableCameraWorker,
)


class DummyCameraInterface(DictAttributesMixin, TriggerableCameraInterface):
    """A camera whose frames were computed when the shot was compiled.

    It presents the interface every camera interface class presents, and
    acquires the way any camera acquires -- one frame per grab, in the order the
    triggers arrive -- but the frames come from the shot file rather than from a
    sensor. In manual mode there is no shot and so no image function, and it
    produces the default image on its own pixels instead.
    """

    # What marks these images as not real data once they are in the shot file.
    # It is a camera attribute rather than pixels drawn onto the image because a
    # watermark does not cancel in OD = -log((atoms - dark) / (probe - dark)),
    # and would ruin the absorption analysis this camera exists to feed. The
    # attribute path every camera already uses saves it beside the images.
    identifying_attributes = {'NOT_REAL_DATA': True}

    def __init__(self, serial_number=None):
        print("Starting device worker as a dummy camera")
        self.attributes = dict(self.identifying_attributes)
        self.images = None
        self.index = 0

    def configure_acquisition(self, continuous=True, bufferCount=5):
        # A continuous acquisition is manual mode, where there is no shot and
        # so no compiled frames. Whatever the last shot left behind is not
        # live data, and handing it back would show it as though it were.
        if continuous:
            self.images = None
        self.index = 0

    def load_images(self, images):
        """Take the frames this shot compiled, to be returned one per grab."""
        self.images = images
        self.index = 0

    def snap(self):
        """A frame with no shot behind it, for manual mode.

        There is no shot and so no image function, and a camera that invented
        something to show here would be modelling data on its own account.
        So this is a blank frame at the size the sensor is configured for:
        a real image, of nothing.
        """
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
    """Thin sub-class of :obj:`TriggerableCameraWorker`.

    It names :obj:`DummyCameraInterface` as its interface class, and hands that camera
    the images the shot compiled before the acquisition starts. Everything
    after that -- the acquisition thread, saving the images to the shot file
    and displaying them in the tab -- is inherited unchanged, which is what
    makes these images indistinguishable from a real camera's downstream."""

    interface_class = DummyCameraInterface

    def load_shot_data(self, shot_file):
        """Hand the camera the frames this shot compiled."""
        group = shot_file['devices'][self.device_name]
        images = group['IMAGES'][:] if 'IMAGES' in group else None
        self.camera.load_images(images)

    def transition_to_buffered(self, device_name, h5_file, front_panel_values, fresh):
        return_value = TriggerableCameraWorker.transition_to_buffered(
            self, device_name, h5_file, front_panel_values, fresh
        )
        # NOT_REAL_DATA is not camera metadata anyone may decide not to save:
        # it is the only thing in the shot file saying these images were made
        # up, so it does not travel by saved_attribute_visibility_level, which
        # switches the rest of them off. Merging it last also keeps a camera
        # attribute of the same name from overriding it.
        self.attributes_to_save = dict(
            self.attributes_to_save or {}, **DummyCameraInterface.identifying_attributes
        )
        return return_value
