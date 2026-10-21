#####################################################################
#                                                                   #
# /labscript_devices/DummyCamera/labscript_devices.py               #
#                                                                   #
# Copyright 2026, Ian Spielman and contributors                     #
#                                                                   #
# This file is part of labscript_devices, in the labscript suite    #
# (see http://labscriptsuite.org), and is licensed under the        #
# Simplified BSD License. See the license.txt file in the root of   #
# the project for the full license.                                 #
#                                                                   #
#####################################################################

import re

import numpy as np
from labscript_utils import dedent

from labscript_devices.DummyCamera.sensor import (
    IMAGE_DTYPE,
    blank_image,
    sensor_size,
)
from labscript_devices.TriggerableCamera.labscript_devices import TriggerableCamera


# The bit depth used when PixelFormat does not give one, and the most there can be:
# images are saved as uint16.
DEFAULT_BIT_DEPTH = 16


class DummyCamera(TriggerableCamera):
    """A camera with no hardware; functions compute its images as the shot compiles."""

    description = 'Dummy Camera'

    def __init__(self, name, parent_device, connection, serial_number=0x0, **kwargs):
        """
        Parameters
        ----------
        name : str
            Python variable name of the device.
        parent_device : IntermediateDevice or Trigger
            The device whose digital output triggers the camera.
        connection : str
            Name of the digital output port on the parent device; ``'trigger'`` if the
            parent is a `Trigger`.
        serial_number : str or int, optional
            As for `TriggerableCamera`, but a dummy camera identifies no hardware, so
            this only sets its BLACS connection; 0 by default.
        **kwargs
            Passed to `TriggerableCamera`. Its `camera_attributes` must give
            ``'Width'`` and ``'Height'``, the size of the images in pixels. A
            ``'PixelFormat'`` attribute ending in a number of bits, such as
            ``'Mono12'``, sets the depth at which pixels saturate, at 2**bits - 1
            counts; the default is 16 bits, which is also the most.
        """
        self.image_functions = []
        TriggerableCamera.__init__(
            self, name, parent_device, connection, serial_number, **kwargs
        )
        # Checked here, not in generate_code: a failure there leaves a half-written
        # shot file, which labscript will not compile again.
        sensor_size(self.camera_attributes)

    def expose(
        self,
        t,
        name,
        frametype='frame',
        trigger_duration=None,
        *args,
        function=None,
        **kwargs
    ):
        """Request an exposure at `t`, with the function that makes its image.

        The function is called once, as the shot compiles, so the shot's globals are
        in scope in it. Only the image it returns is saved in the shot file, so it can
        be any callable, a lambda included. Frames that have to agree, such as an
        absorption image's atoms and probe frames, are exposures that share one
        function and differ in `args` and `kwargs`.

        Parameters
        ----------
        t : float
            Time in seconds of the trigger edge.
        name : str
            What the image shows, such as ``'insitu_absorption'``. With `frametype` it
            sets where the image is stored in the shot file, under
            ``images/<orientation>/<name>/<frametype>``.
        frametype : str, optional
            The type of frame, for imaging methods that take several, such as
            ``'probe'``, ``'atoms'`` and ``'background'``; ``'frame'`` by default.
        trigger_duration : float, optional
            Duration in seconds of the trigger pulse, greater than 0; the device's
            `trigger_duration` by default.
        *args
            Positional arguments for `function`, after `X` and `Y`. They follow
            `trigger_duration` in the call.
        function : callable, optional
            Passed by keyword. Called as ``function(X, Y, *args, **kwargs)``, where `X`
            and `Y` are arrays, height by width, of each pixel's position in the object
            plane in micrometres, from the sensor's centre: its offset in pixels times
            `pixel_size`, divided by `magnification`. It returns an array of counts of
            that shape, clipped from 0 to a pixel's saturation count (see
            `camera_attributes`) and stored as uint16; an array of another shape, or
            holding a NaN or an infinity, stops the shot compiling. `None`, the default,
            gives a blank frame of zero counts.
        **kwargs
            Keyword arguments for `function`, other than those named `t`, `name`,
            `frametype`, `trigger_duration` or `function`, which `expose` takes.

        Returns
        -------
        float
            The trigger duration used.
        """
        trigger_duration = TriggerableCamera.expose(
            self, t, name, frametype, trigger_duration
        )
        self.image_functions.append((function, args, kwargs))
        return trigger_duration

    def coordinate_grid(self):
        """Return the X, Y grid of pixel positions in object-plane micrometres."""
        width, height = sensor_size(self.camera_attributes)
        pixel_x, pixel_y = self.pixel_size
        x = (np.arange(width) - (width - 1) / 2) * pixel_x / self.magnification
        y = (np.arange(height) - (height - 1) / 2) * pixel_y / self.magnification
        return np.meshgrid(x, y)

    def saturation(self):
        """Return the largest pixel count, from the bit depth `PixelFormat` ends in."""
        pixel_format = str(self.camera_attributes.get('PixelFormat', ''))
        match = re.search(r'(\d+)$', pixel_format)
        bit_depth = int(match.group(1)) if match else DEFAULT_BIT_DEPTH
        return 2 ** min(bit_depth, DEFAULT_BIT_DEPTH) - 1

    def generate_code(self, hdf5_file):
        """Write the exposures and, if there are any, their images to the shot file."""
        TriggerableCamera.generate_code(self, hdf5_file)
        if not self.exposures:
            return
        group = hdf5_file['devices'][self.name]
        width, height = sensor_size(self.camera_attributes)
        X, Y = self.coordinate_grid()
        images = []
        # The images go in time order, the order transition_to_manual matches them to
        # the exposures sorted by t. Sorting whole exposures breaks ties on the
        # remaining fields, in dtype order, as numpy's sort(order='t') does.
        for i in sorted(range(len(self.exposures)), key=self.exposures.__getitem__):
            function, args, kwargs = self.image_functions[i]
            if function is None:
                images.append(blank_image(width, height))
                continue
            image = np.asarray(function(X, Y, *args, **kwargs))
            complaint = None
            if image.shape != X.shape:
                complaint = f"""returned an array of shape {image.shape}, but this
                    camera's images are {X.shape}, height by width. Return an array of
                    the shape of X and Y."""
            elif not np.isfinite(image).all():
                # np.clip passes a NaN through, and casting it to counts is undefined.
                complaint = """returned a NaN or an infinity, which cannot be stored as
                    camera counts. Return only finite values."""
            if complaint is not None:
                t, name, frametype, _ = self.exposures[i]
                msg = (
                    f"The image function {getattr(function, '__name__', function)} for "
                    f"exposure '{name}', frametype '{frametype}', of {self.name} at "
                    f"t = {t} {dedent(complaint)}"
                )
                raise ValueError(msg)
            counts = np.clip(image.astype(float), 0, self.saturation())
            images.append(counts.astype(IMAGE_DTYPE))
        group.create_dataset('IMAGES', data=np.array(images), compression='gzip')
