#####################################################################
#                                                                   #
# /labscript_devices/PulseBlaster_SP2_24_100_32k/__init__.py        #
#                                                                   #
# Copyright 2013, Monash University                                 #
#                                                                   #
# This file is part of labscript_devices, in the labscript suite    #
# (see http://labscriptsuite.org), and is licensed under the        #
# Simplified BSD License. See the license.txt file in the root of   #
# the project for the full license.                                 #
#                                                                   #
#####################################################################
from labscript_devices import BLACS_tab, lazy_attributes, runviewer_parser
from .labscript_devices import (
    PulseBlaster_No_DDS, PulseBlaster_SP2_24_100_32k,
)

# Each name the old single-file module bound stays importable from here. Those
# of BLACS and runviewer load only when asked for, so a compile never imports
# BLACS.
__getattr__ = lazy_attributes(
    __name__,
    {
        'blacs_tabs': [
            'Pulseblaster_No_DDS_Tab', 'PulseBlaster_SP2_24_100_32k_Tab',
        ],
        'blacs_workers': [
            'PulseblasterNoDDSWorker', 'PulseBlaster_SP2_24_100_32k_Worker',
        ],
        'runviewer_parsers': [
            'PulseBlasterParser', 'PulseBlaster_SP2_24_100_32k_Parser',
        ],
    },
)
