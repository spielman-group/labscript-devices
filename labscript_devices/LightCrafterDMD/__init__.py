#####################################################################
#                                                                   #
# /labscript_devices/LightCrafterDMD/__init__.py                    #
#                                                                   #
# Copyright 2017, Monash University                                 #
#                                                                   #
# This file is part of labscript_devices, in the labscript suite    #
# (see http://labscriptsuite.org), and is licensed under the        #
# Simplified BSD License. See the license.txt file in the root of   #
# the project for the full license.                                 #
#                                                                   #
#####################################################################

# The names this package gives. The compile side's are imported here; those of
# BLACS and runviewer load only when asked for, so a compile never imports
# BLACS.
from labscript_devices import (
    BLACS_tab, BLACS_worker, labscript_device, lazy_attributes,
    runviewer_parser,
)
from .labscript_devices import (
    os, struct, PIL, BytesIO, Device, IntermediateDevice, LabscriptError,
    Output, compiler, np, arr_to_bmp, WIDTH, HEIGHT, BLANK_BMP, ImageSet,
    LightCrafterDMD,
)

__getattr__ = lazy_attributes(
    __name__,
    {
        'blacs_tabs': [
            'define_state', 'MODE_MANUAL', 'MODE_TRANSITION_TO_BUFFERED',
            'MODE_TRANSITION_TO_MANUAL', 'MODE_BUFFERED', 'DeviceTab',
            'Signal', 'LightCrafterTab',
        ],
        'blacs_workers': [
            'base64', 'time', 'labscript_utils', 'h5py', 'Worker',
            'LightCrafterWorker',
        ],
    },
)
