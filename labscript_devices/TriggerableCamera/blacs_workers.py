#####################################################################
#                                                                   #
# /labscript_devices/TriggerableCamera/blacs_workers.py             #
#                                                                   #
# Copyright 2019, Monash University and contributors                #
#                                                                   #
# This file is part of labscript_devices, in the labscript suite    #
# (see http://labscriptsuite.org), and is licensed under the        #
# Simplified BSD License. See the license.txt file in the root of   #
# the project for the full license.                                 #
#                                                                   #
#####################################################################


import sys
from time import perf_counter
from blacs.tab_base_classes import Worker
import threading
import numpy as np
from labscript_utils import dedent
import labscript_utils.h5_lock
import h5py
import labscript_utils.properties
import zmq

from labscript_utils.ls_zprocess import Context
from labscript_utils.shared_drive import path_to_local


def _unwritten(camera, method):
    """The message for a member of the camera contract a camera has not written."""
    msg = f"""{type(camera).__name__} does not implement {method}(). Write it in the
        camera's interface class, or override the method that calls it."""
    return dedent(msg)


class TriggerableCameraInterface:
    """What `TriggerableCameraWorker` calls on its camera; cameras subclass it."""

    # Set by the worker, from the device property of the same name, for each shot that
    # has exposures, and read by grab_multiple.
    exception_on_failed_shot = True

    # Set by abort_acquisition, from the aborting thread. Polled by grab_multiple
    # between frames, which clears it when it stops on seeing it; the worker's abort()
    # clears it too.
    _abort_acquisition = False

    def set_attributes(self, attributes):
        """Program a dict of attributes; the default calls `set_attribute` for each."""
        for name, value in attributes.items():
            self.set_attribute(name, value)

    # A member a camera must write raises rather than does nothing: a camera that
    # silently fails to program an attribute or stop an acquisition is worse than one
    # that does not start.
    def set_attribute(self, name, value):
        """Program one attribute; a camera writes this or `set_attributes`."""
        raise NotImplementedError(_unwritten(self, 'set_attribute'))

    def get_attribute(self, name):
        """Return the current value of the named attribute.

        A camera that overrides `get_attributes_as_dict` need not write this or
        `get_attribute_names`.
        """
        raise NotImplementedError(_unwritten(self, 'get_attribute'))

    def get_attribute_names(self, visibility_level):
        """Return the names of the attributes at a visibility level."""
        raise NotImplementedError(_unwritten(self, 'get_attribute_names'))

    def snap(self):
        """Return one image, arranging its own acquisition."""
        self.configure_acquisition(continuous=False, buffer_count=1)
        image = self.grab()
        self.stop_acquisition()
        return image

    def grab(self):
        """Return the next image of an acquisition already configured.

        The array must stay valid after the next grab, as `grab_multiple` keeps
        them: a camera whose API reuses its buffer copies the image out.
        """
        raise NotImplementedError(_unwritten(self, 'grab'))

    def configure_acquisition(self, continuous=True, buffer_count=None):
        """Ready the camera to grab; `buffer_count` None leaves it to the camera.

        The worker calls this with no arguments for manual-mode continuous
        acquisition, and with ``continuous=False`` and the shot's number of
        exposures for a buffered one.
        """
        raise NotImplementedError(_unwritten(self, 'configure_acquisition'))

    def stop_acquisition(self):
        """End an acquisition: a shot's, however it ended, or a continuous one's."""
        raise NotImplementedError(_unwritten(self, 'stop_acquisition'))

    def close(self):
        """Release the camera; the worker calls this when it shuts down."""
        raise NotImplementedError(_unwritten(self, 'close'))

    def get_attributes_as_dict(self, visibility_level):
        """Return a dict of the attributes at a visibility level.

        The worker reads them for the shot file and the BLACS dialog. This
        composes `get_attribute_names` and `get_attribute`; a camera whose API
        hands over every attribute at once overrides it.
        """
        names = self.get_attribute_names(visibility_level)
        return {name: self.get_attribute(name) for name in names}

    def is_transient_grab_error(self, exception):
        """Whether this exception from `grab` means "no frame yet, ask again".

        `grab_multiple` asks again at once, so a camera that says True must have
        blocked for its own timeout in `grab` before raising, or the loop spins
        until it is aborted.
        """
        return False

    def is_skippable_grab_error(self, exception):
        """Whether this exception from `grab` is one the camera's own API reported.

        With ``exception_on_failed_shot`` False, `grab_multiple` gives up the frame
        and goes on to the next when this is True.
        """
        return False

    def abort_acquisition(self):
        """Ask `grab_multiple` to stop at its next frame.

        This runs in the worker's thread while `grab_multiple` runs in its own, so
        it only raises the flag. A camera whose `grab` blocks in the vendor's API
        overrides it to make the call that unblocks it, then calls this one.
        """
        self._abort_acquisition = True

    def grab_multiple(self, n_images, images):
        """Grab `n_images` frames, appending each to `images` as it arrives.

        The worker runs this in a thread for the shot, having configured the
        acquisition for the same `n_images`. A camera whose acquisition is not one
        frame per `grab`, such as a kinetic series, overrides it wholesale.
        """
        print(f"Attempting to grab {n_images} images.")
        for i in range(n_images):
            while True:
                if self._abort_acquisition:
                    print("Abort during acquisition.")
                    self._abort_acquisition = False
                    return
                try:
                    image = self.grab()
                except Exception as exception:
                    if self.is_transient_grab_error(exception):
                        print('.', end='')
                        continue
                    if (
                        self.is_skippable_grab_error(exception)
                        and not self.exception_on_failed_shot
                    ):
                        print(exception, file=sys.stderr)
                        break
                    raise
                images.append(image)
                print(f"Got image {i+1} of {n_images}.")
                break
        print(f"Got {len(images)} of {n_images} images.")


class DictAttributesMixin:
    """Attributes held in the dict ``self.attributes`` instead of in the camera."""

    def set_attribute(self, name, value):
        self.attributes[name] = value

    def get_attribute(self, name):
        return self.attributes[name]

    def get_attribute_names(self, visibility_level=None, writeable_only=True):
        return list(self.attributes.keys())


class TriggerableCameraWorker(Worker):
    # The camera interface class this worker drives. A subclass names its own here if
    # it takes only the serial number as an instantiation argument, otherwise it
    # reimplements get_camera().
    interface_class = None

    def init(self):
        # get_attributes_as_dict is called on the camera, so a worker that
        # overrides it would have the override skipped without a word.
        for cls in type(self).__mro__:
            if cls is TriggerableCameraWorker:
                break
            if 'get_attributes_as_dict' in vars(cls):
                raise RuntimeError(
                    f"{cls.__name__} overrides get_attributes_as_dict(), which is "
                    "called on the camera, not the worker. Move it to the camera class."
                )
        self.camera = self.get_camera()
        print("Setting attributes...")
        self.smart_cache = {}
        self.set_attributes_smart(self.camera_attributes)
        self.set_attributes_smart(self.manual_mode_camera_attributes)
        print("Initialisation complete")
        self._clear_shot_state()
        self.continuous_stop = threading.Event()
        self.continuous_thread = None
        self.continuous_dt = None
        self.image_socket = Context().socket(zmq.REQ)
        self.image_socket.connect(
            f'tcp://{self.parent_host}:{self.image_receiver_port}'
        )

    def _clear_shot_state(self):
        """Forget the shot just finished, or the one that never started."""
        self.images = None
        self.n_images = None
        self.attributes_to_save = None
        self.exposures = None
        self.acquisition_thread = None
        self.acquisition_error = None
        self.h5_file = None
        self.stop_acquisition_timeout = None
        self.exception_on_failed_shot = None

    def get_camera(self):
        """Return the camera; override if it takes more than the serial number."""
        return self.interface_class(self.serial_number)

    def load_shot_data(self, shot_file):
        """Read what else this worker needs from the open shot file.

        `transition_to_buffered` calls this with the shot file open, after reading
        the exposures and the camera attributes. A camera that needs more overrides
        it, so that the file is not opened and locked a second time.
        """
        pass

    def set_attributes_smart(self, attributes):
        """Set the attributes new or changed since `smart_cache`, and update it."""
        uncached_attributes = {}
        for name, value in attributes.items():
            if name not in self.smart_cache or self.smart_cache[name] != value:
                uncached_attributes[name] = value
                self.smart_cache[name] = value
        self.camera.set_attributes(uncached_attributes)

    def get_attributes_as_text(self, visibility_level):
        """Return the attributes at a visibility level as connection table text."""
        attrs = self.camera.get_attributes_as_dict(visibility_level)
        lines = [f'    {repr(key)}: {repr(value)},' for key, value in attrs.items()]
        dict_repr = '\n'.join(['{'] + lines + ['}'])
        return self.device_name + '_camera_attributes = ' + dict_repr

    def snap(self):
        """Acquire one image in manual mode and send it to the tab."""
        image = self.camera.snap()
        self._send_image_to_parent(image)

    def _send_image_to_parent(self, image):
        """Send an image to the tab and wait for its ack, so frames do not back up."""
        metadata = dict(dtype=str(image.dtype), shape=image.shape)
        self.image_socket.send_json(metadata, zmq.SNDMORE)
        self.image_socket.send(image, copy=False)
        response = self.image_socket.recv()
        assert response == b'ok', response

    def continuous_loop(self, dt):
        """Grab and send images until stopped, at least `dt` seconds apart."""
        while True:
            if dt is not None:
                t = perf_counter()
            image = self.camera.grab()
            self._send_image_to_parent(image)
            if dt is None:
                timeout = 0
            else:
                timeout = t + dt - perf_counter()
            if self.continuous_stop.wait(timeout):
                self.continuous_stop.clear()
                break

    def start_continuous(self, dt):
        """Start continuous acquisition in a thread; see `continuous_loop`."""
        assert self.continuous_thread is None
        self.camera.configure_acquisition()
        self.continuous_thread = threading.Thread(
            target=self.continuous_loop, args=(dt,), daemon=True
        )
        self.continuous_thread.start()
        self.continuous_dt = dt

    def stop_continuous(self, pause=False):
        """Stop the continuous acquisition thread."""
        assert self.continuous_thread is not None
        self.continuous_stop.set()
        self.continuous_thread.join()
        self.continuous_thread = None
        self.camera.stop_acquisition()
        # With pause, continuous_dt is kept, which tells transition_to_manual and abort
        # to resume at that interval without asking the tab for it again.
        if not pause:
            self.continuous_dt = None

    def transition_to_buffered(self, device_name, h5_file, front_panel_values, fresh):
        if getattr(self, 'is_remote', False):
            h5_file = path_to_local(h5_file)
        if self.continuous_thread is not None:
            self.stop_continuous(pause=True)
        with h5py.File(h5_file, 'r') as f:
            group = f['devices'][self.device_name]
            if not 'EXPOSURES' in group:
                return {}
            self.h5_file = h5_file
            self.exposures = group['EXPOSURES'][:]
            self.n_images = len(self.exposures)

            device_properties = labscript_utils.properties.get(
                f, self.device_name, 'device_properties'
            )
            camera_attributes = device_properties['camera_attributes']
            self.stop_acquisition_timeout = device_properties['stop_acquisition_timeout']
            self.exception_on_failed_shot = device_properties['exception_on_failed_shot']
            saved_attr_level = device_properties['saved_attribute_visibility_level']
            self.camera.exception_on_failed_shot = self.exception_on_failed_shot
            self.load_shot_data(f)
        # Only reprogram attributes that differ from those last programmed in, or all of
        # them if a fresh reprogramming was requested:
        if fresh:
            self.smart_cache = {}
        self.set_attributes_smart(camera_attributes)
        # Get the camera attributes, so that we can save them to the H5 file:
        if saved_attr_level is not None:
            self.attributes_to_save = self.camera.get_attributes_as_dict(
                saved_attr_level
            )
        else:
            self.attributes_to_save = None
        print(f"Configuring camera for {self.n_images} images.")
        # LEGACY BUFFERCOUNT COMPATIBILITY. DEPRECATED CODE, WILL BE REMOVED.
        # Positional, as a camera on IMAQdxCameraWorker's deprecated route names it
        # bufferCount.
        self.camera.configure_acquisition(False, self.n_images)
        self.images = []

        def grab_multiple():
            try:
                self.camera.grab_multiple(self.n_images, self.images)
            except Exception as e:
                # Kept for transition_to_manual, which fails the shot with it.
                self.acquisition_error = e
                raise

        self.acquisition_thread = threading.Thread(target=grab_multiple, daemon=True)
        self.acquisition_thread.start()
        return {}

    def transition_to_manual(self):
        if self.h5_file is None:
            print('No camera exposures in this shot.\n')
            if self.continuous_dt is not None:
                self.start_continuous(self.continuous_dt)
            return True
        assert self.acquisition_thread is not None
        self.acquisition_thread.join(timeout=self.stop_acquisition_timeout)
        if self.acquisition_thread.is_alive():
            msg = f"""The camera {self.device_name} had acquired {len(self.images)} of
                {len(self.exposures)} images {self.stop_acquisition_timeout} s after the
                shot ended. Check that the triggers are connected and the camera is
                configured to accept them."""
            if self.exception_on_failed_shot:
                self.abort()
                raise RuntimeError(dedent(msg))
            else:
                self.camera.abort_acquisition()
                self.acquisition_thread.join()
                print(dedent(msg), file=sys.stderr)
        if self.acquisition_error is not None and self.exception_on_failed_shot:
            error = self.acquisition_error
            self.abort()
            raise error
        self.acquisition_thread = None

        print("Stopping acquisition.")
        self.camera.stop_acquisition()

        print(f"Saving {len(self.images)}/{len(self.exposures)} images.")

        with h5py.File(self.h5_file, 'r+') as f:
            # Use orientation for image path, device_name if orientation unspecified
            if self.orientation is not None:
                image_path = 'images/' + self.orientation
            else:
                image_path = 'images/' + self.device_name
            image_group = f.require_group(image_path)
            image_group.attrs['camera'] = self.device_name

            if self.attributes_to_save is not None:
                labscript_utils.properties.set_attributes(
                    image_group, self.attributes_to_save
                )

            # Whether we failed to get all the expected exposures:
            image_group.attrs['failed_shot'] = len(self.images) != len(self.exposures)

            # Key the images by name and frametype. Several images with the same name
            # and frametype are saved as an array in a single dataset.
            images = {
                (exposure['name'], exposure['frametype']): []
                for exposure in self.exposures
            }

            # Iterate over expected exposures, sorted by acquisition time, to match them
            # up with the acquired images:
            self.exposures.sort(order='t')
            for image, exposure in zip(self.images, self.exposures):
                images[(exposure['name'], exposure['frametype'])].append(image)

            for (name, frametype), imagelist in images.items():
                data = imagelist[0] if len(imagelist) == 1 else np.array(imagelist)
                print(f"Saving frame(s) {name}/{frametype}.")
                group = image_group.require_group(name)
                dset = group.create_dataset(
                    frametype, data=data, dtype='uint16', compression='gzip'
                )
                # Specify this dataset should be viewed as an image
                dset.attrs['CLASS'] = np.bytes_('IMAGE')
                dset.attrs['IMAGE_VERSION'] = np.bytes_('1.2')
                dset.attrs['IMAGE_SUBCLASS'] = np.bytes_('IMAGE_GRAYSCALE')
                dset.attrs['IMAGE_WHITE_IS_ZERO'] = np.uint8(0)

        # If the images are all the same shape, send them to the GUI for display:
        try:
            image_block = np.stack(self.images)
        except ValueError:
            print("Cannot display images in the GUI, they are not all the same shape")
        else:
            self._send_image_to_parent(image_block)

        self._clear_shot_state()
        print("Setting manual mode camera attributes.\n")
        self.set_attributes_smart(self.manual_mode_camera_attributes)
        if self.continuous_dt is not None:
            # Continuous manual mode acquisition was paused for the shot; resume it.
            self.start_continuous(self.continuous_dt)
        return True

    def abort(self):
        if self.acquisition_thread is not None:
            self.camera.abort_acquisition()
            self.acquisition_thread.join()
            self.acquisition_thread = None
            self.camera.stop_acquisition()
        self.camera._abort_acquisition = False
        self._clear_shot_state()
        if self.continuous_dt is not None and self.continuous_thread is None:
            self.start_continuous(self.continuous_dt)
        return True

    def abort_buffered(self):
        return self.abort()

    def abort_transition_to_buffered(self):
        return self.abort()

    def program_manual(self, front_panel_values):
        return {}

    def shutdown(self):
        if self.continuous_thread is not None:
            self.stop_continuous()
        self.camera.close()
