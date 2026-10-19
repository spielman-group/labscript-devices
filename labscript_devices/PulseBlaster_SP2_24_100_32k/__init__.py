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

# The labscript-side names are imported here and make up __all__, so a star
# import of this package never loads BLACS. Its tab, worker and parser names
# load only when asked for by name.
from labscript_devices import lazy_attributes
from .labscript_devices import (
    PulseBlaster_No_DDS, PulseBlaster_SP2_24_100_32k,
)

__all__ = [
    'PulseBlaster_No_DDS', 'PulseBlaster_SP2_24_100_32k',
]

__getattr__ = lazy_attributes(
    __name__,
    {
        'blacs_tabs': [
            'PulseBlaster_No_DDSTab', 'PulseBlaster_SP2_24_100_32kTab',
        ],
        'blacs_workers': [
            'PulseBlaster_No_DDSWorker', 'PulseBlaster_SP2_24_100_32kWorker',
        ],
        'runviewer_parsers': [
            'PulseBlaster_SP2_24_100_32kParser',
        ],
        'labscript_devices.PulseBlaster.runviewer_parsers': [
            'PulseBlasterParser',
        ],
    },
)
