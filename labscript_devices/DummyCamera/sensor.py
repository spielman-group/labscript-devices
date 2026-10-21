#####################################################################
#                                                                   #
# /labscript_devices/DummyCamera/sensor.py                          #
#                                                                   #
# Copyright 2026, Ian Spielman and contributors                     #
#                                                                   #
# This file is part of labscript_devices, in the labscript suite    #
# (see http://labscriptsuite.org), and is licensed under the        #
# Simplified BSD License. See the license.txt file in the root of   #
# the project for the full license.                                 #
#                                                                   #
#####################################################################

"""The size, count type and blank frame of a dummy camera's images."""

# Imported by both labscript_devices.py and blacs_workers.py, so it needs neither
# labscript, which loads pylab, nor blacs.
import numpy as np

from labscript_utils import dedent


# Images are whole counts, as a sensor reads them. They are saved as uint16, so
# generate_code casts an image function's floats to this type before storing them.
IMAGE_DTYPE = np.uint16


def sensor_size(camera_attributes):
    """Return (width, height) in pixels from the `Width` and `Height` attributes."""
    # A dummy camera has no sensor to say its size, so they are required, not defaulted.
    missing = [key for key in ('Width', 'Height') if key not in camera_attributes]
    if missing:
        msg = f"""A dummy camera's image size comes from its camera_attributes, which
            do not give {' and '.join(missing)}. Pass
            camera_attributes={{'Width': ..., 'Height': ...}}."""
        raise ValueError(dedent(msg))
    return int(camera_attributes['Width']), int(camera_attributes['Height'])


def blank_image(width, height):
    """Return a frame of zero counts, `height` rows by `width` columns."""
    return np.zeros((height, width), dtype=IMAGE_DTYPE)
