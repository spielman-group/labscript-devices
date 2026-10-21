#####################################################################
#                                                                   #
# /labscript_devices/LightCrafterDMD/labscript_devices.py           #
#                                                                   #
# Copyright 2017, Monash University                                 #
#                                                                   #
# This file is part of labscript_devices, in the labscript suite    #
# (see http://labscriptsuite.org), and is licensed under the        #
# Simplified BSD License. See the license.txt file in the root of   #
# the project for the full license.                                 #
#                                                                   #
#####################################################################

import os
import struct
import PIL.Image
from io import BytesIO

from labscript import (
    Device, IntermediateDevice, LabscriptError, Output, compiler, renamed_keyword,
)
import numpy as np


def arr_to_bmp(arr):
    """Return the bytes of a 1-bit BMP of the 2-D array `arr`, white wherever it is nonzero."""
    binary_arr = 255 * (arr != 0).astype(np.uint8)
    im = PIL.Image.fromarray(binary_arr, mode='L').convert('1')
    f = BytesIO()
    im.save(f, "BMP")
    return f.getvalue()


# The size of the DLP 0.3 WVGA, in pixels.
WIDTH = 608
HEIGHT = 684
BLANK_BMP = arr_to_bmp(np.zeros((HEIGHT, WIDTH)))


class ImageSet(Output):
    """The images a LightCrafterDMD shows, each a 1-bit BMP set at a time."""

    description = 'A set of images to be displayed on an SLM or DMD'
    width = WIDTH
    height = HEIGHT
    default_value = BLANK_BMP
    """bytes: A black image.

    Raw bitmap data hidden from docs.

    :meta hide-value:
    """

    def __init__(self, name, parent_device, connection='Mirror', **kwargs):
        """
        Parameters
        ----------
        name : str
            Python variable name of the device.
        parent_device : :class:`LightCrafterDMD`
            The DMD that shows the images.
        connection : str, optional
            Connection to the DMD: any string, since a DMD has one ImageSet;
            ``'Mirror'`` by default.
        **kwargs
            Passed to :class:`~labscript.Output`.
        """
        Output.__init__(self, name, parent_device, connection, **kwargs)

    def set_array(self, t, arr):
        """Show the image `arr` from time `t`, until the next image.

        Parameters
        ----------
        t : float
            Time, in seconds, to show the image.
        arr : numpy.ndarray
            2-D array of 684 rows by 608 columns, the display's height and width, white
            wherever it is nonzero.
        """
        self.set_image(t, raw=arr_to_bmp(arr))

    def set_image(self, t, path=None, raw=None):
        """Show a BMP image from time `t`, until the next image.

        Parameters
        ----------
        t : float
            Time, in seconds, to show the image.
        path : str, optional
            Path of a 1-bit bmp file, 608 pixels wide by 684 high, whose name ends in
            ``.bmp``. Required unless `raw` is given.
        raw : bytes, optional
            The contents of such a file. If given, `path` is not read.
        """
        if raw is not None:
            raw_data = raw
        else:
            if not os.path.exists(path):
                raise LabscriptError(
                    f'Cannot load the image for DMD output {self.name}: '
                    f'there is no file at {path}.'
                )
            if len(path) < 5 or path[-4:] != '.bmp':
                raise LabscriptError(
                    f'Cannot load the image for DMD output {self.name}: '
                    f"the file name {path!r} must end in '.bmp', in lower case."
                )
            with open(path, 'rb') as f:
                raw_data = f.read()
        # A BMP starts with "BM", and its header must be long enough to hold the fields
        # read below.
        if raw_data[0:2] != b"BM" or len(raw_data) < 30:
            raise LabscriptError(
                f'The image for DMD output {self.name} (path: {path}) is not a bmp: '
                'it must start with "BM" and be at least 30 bytes long. '
                'Save it as a 1-bit bmp.'
            )
        # The width and height are stored in bytes 18-21 and 22-25.
        width = struct.unpack("<i", raw_data[18:22])[0]
        height = struct.unpack("<i", raw_data[22:26])[0]

        if width != self.width or height != self.height:
            raise LabscriptError(
                f'The image for DMD output {self.name} (path: {path}) is {width} x '
                f'{height} pixels, but it must be {self.width} x {self.height}.'
            )

        bitdepth = struct.unpack("<h", raw_data[28:30])[0]
        if bitdepth != 1:
            raise LabscriptError(
                f'The image for DMD output {self.name} (path: {path}) has a bit depth '
                f'of {bitdepth}, but it must be 1. Re-save it as a 1-bit bmp.'
            )
        self.add_instruction(t, raw_data)

    def expand_timeseries(self, *args, **kwargs):
        """Make the raw output the timeseries of bytestrings, not floats."""
        self.raw_output = np.array(self.timeseries)
        return


class LightCrafterDMD(IntermediateDevice):
    """A LightCrafter DLPC300 DMD controller, which shows the images of one :class:`ImageSet`."""

    description = 'LightCrafter DMD controller'
    allowed_children = [ImageSet]

    # These numbers are for the DLPC300; another model, with a different resolution and
    # so on, needs its own. Only black and white images, of bit depth 1, are used.
    max_instructions = 96
    clock_limit = 4000
    width = WIDTH
    height = HEIGHT

    def __init__(self, name, parent_device, host='192.168.1.100', port=21845, **kwargs):
        """
        Parameters
        ----------
        name : str
            Python variable name of the device.
        parent_device : :class:`~labscript.ClockLine`
            Clock line that clocks the device.
        host : str, optional
            IP address or host name of the LightCrafter, without a colon;
            ``'192.168.1.100'`` by default. The old keyword `server` still works, with
            a FutureWarning.
        port : int, optional
            TCP port of the LightCrafter; 21845 by default.
        **kwargs
            Passed to :class:`~labscript.IntermediateDevice`.
        """
        # LEGACY SERVER KEYWORD COMPATIBILITY. DEPRECATED CODE, WILL BE REMOVED.
        host = renamed_keyword(kwargs, 'server', 'host', host, 'LightCrafterDMD')
        IntermediateDevice.__init__(self, name, parent_device, **kwargs)
        self.BLACS_connection = f'{host}:{port:d}'

    def add_device(self, device):
        Device.add_device(self, device)

        # An ImageSet checks its images against its parent's dimensions.
        device.width = self.width
        device.height = self.height

    def generate_code(self, hdf5_file):
        """Write the images, in the order they are shown, to the shot file's IMAGE_TABLE."""
        if len(self.child_devices) != 1:
            raise LabscriptError(
                f'The LightCrafter {self.name} needs exactly one ImageSet, '
                f'but has {len(self.child_devices)}.'
            )
        output = self.child_devices[0]
        if len(output.raw_output) > self.max_instructions:
            raise LabscriptError(
                f'The shot has {len(output.raw_output)} images for the LightCrafter '
                f'{self.name}, which takes at most {self.max_instructions}. The count '
                'includes one at the start of the shot and one at its end. '
                'Set fewer images.'
            )

        # np.void stores the images as opaque binary data, which the worker reads back
        # with tobytes().
        out_table = np.void(output.raw_output)
        grp = self.init_device_group(hdf5_file)
        grp.create_dataset('IMAGE_TABLE', compression=compiler.compression, data=out_table)
