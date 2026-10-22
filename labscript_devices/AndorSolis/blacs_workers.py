#####################################################################
#                                                                   #
# /labscript_devices/AndorSolis/blacs_workers.py                    #
#                                                                   #
# Copyright 2019, Monash University and contributors                #
#                                                                   #
# This file is part of labscript_devices, in the labscript suite    #
# (see http://labscriptsuite.org), and is licensed under the        #
# Simplified BSD License. See the license.txt file in the root of   #
# the project for the full license.                                 #
#                                                                   #
#####################################################################

from zprocess import rich_print
from labscript_devices.TriggerableCamera.blacs_workers import (
    DictAttributesMixin,
    TriggerableCameraInterface,
    TriggerableCameraWorker,
)


class AndorSolisInterface(DictAttributesMixin, TriggerableCameraInterface):
    """An Andor camera driven through `AndorCam`."""

    def __init__(self):
        # Imported here, not at the top: importing andor_utils loads Andor's SDK
        # library, which importing this module must not require.
        global AndorCam
        from .andor_sdk.andor_utils import AndorCam
        self.camera = AndorCam()
        self.attributes = self.camera.default_acquisition_attrs.copy()

    def snap(self):
        """Acquire and return the stack of number_kinetics images."""
        self.configure_acquisition()
        self.camera.acquire()
        images = self.camera.download_acquisition()
        print(f'Exposure time was {self.camera.exposure_time}')
        # A 3D array: the first axis holds the number_kinetics images.
        return images

    def configure_acquisition(self, continuous=True, buffer_count=None):
        """Set up and arm the camera with the attributes; the arguments are unused."""
        self.camera.setup_acquisition(self.attributes)

    def grab(self):
        """Return the stack of images `snap` acquires."""
        # Consider using run til abort acquisition mode...
        img = self.snap()
        return img

    def grab_multiple(self, n_images, images):
        """Acquire as the acquisition mode says and add the images to `images`."""
        print(f"Camera configured in {self.camera.acquisition_mode} mode.")
        print(f"Actual readout time is {self.camera.readout_time} s.")
        print(f"Keep clean cycle time is {self.camera.keepClean_time} s.")
        if 'kinetic_series' in self.camera.acquisition_mode:
            print(f"Kinetics number is {self.camera.acquisition_attributes['number_kinetics']}.")
            print(f"Actual kinetics period is {self.camera.kinetics_timing} s.")
        print(f"Actual exposure time is {self.camera.exposure_time} s.")
        print(f"Actual digitization speed (HSpeed) is {self.camera.horizontal_shift_speed} MHz.")
        print(f"Actual vertical shift speed is {self.camera.vs_speed} us.")
        rich_print(f" ---> EMCCD Gain value is {self.camera.emccd_gain}.", color='magenta')
        if 'fast_kinetics' in self.camera.acquisition_mode:
            print(f"FK mode Kinetics Number is {self.camera.number_fast_kinetics}.")
        print(f"    ---> Attempting to grab {n_images} acquisition(s).")

        # acquire() disarms the camera. The loops below arm it again after each
        # download, for the next acquire(), and disarm it after the last.
        if 'single' in self.camera.acquisition_mode:
            for image_number in range(n_images):
                self.camera.acquire()
                if self._abort_acquisition:
                    print("Abort during acquisition.")
                    self._abort_acquisition = False
                    self.camera.armed = False
                    return
                print(f"    {image_number}: Acquire complete")
                downloaded = self.camera.download_acquisition()
                print(f"    {image_number}: Download complete")
                images.append(downloaded)
                self.camera.armed = True
            self.camera.armed = False
            print(f"Got {len(images)} of {n_images} acquisition(s).")
        elif 'fast_kinetics' in self.camera.acquisition_mode:
            nacquisitions = n_images // self.camera.number_fast_kinetics
            for image_number in range(nacquisitions):
                self.camera.acquire()
                if self._abort_acquisition:
                    print("Abort during acquisition.")
                    self._abort_acquisition = False
                    self.camera.armed = False
                    return
                print(f"    {image_number}: Acquire complete")
                downloaded = self.camera.download_acquisition()
                print(f"    {image_number}: Download complete")
                images.extend(list(downloaded))
                self.camera.armed = True
            self.camera.armed = False
            print(f"Got {len(images)} images in {nacquisitions} FK series acquisition(s).")
        else:
            self.camera.acquire()
            print(f"    Acquire complete")
            downloaded = self.camera.download_acquisition()
            print(f"    images {len(images)}-{len(images) + len(downloaded)}: Download complete")
            images.extend(list(downloaded))
            self.camera.armed = False
            print(f"Got {len(images)} of {n_images} acquisition(s).")

    def stop_acquisition(self):
        """Do nothing; acquire() waits for each acquisition to end."""
        pass

    def abort_acquisition(self):
        # The flag first, so grab_multiple stops once the SDK call has ended its
        # acquisition, and the camera starts none after it.
        TriggerableCameraInterface.abort_acquisition(self)
        self.camera.abort_acquisition()

    def close(self):
        self.camera.shutdown()


class AndorSolisWorker(TriggerableCameraWorker):
    """Worker for AndorSolisInterface."""

    interface_class = AndorSolisInterface

    def get_camera(self):
        """Return the camera. Andor cameras may not be specified by serial numbers."""
        return self.interface_class()
