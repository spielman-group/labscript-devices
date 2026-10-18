#####################################################################
#                                                                   #
# /labscript_devices/PulseBlaster_No_DDS/__init__.py                #
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
    PulseBlaster, PulseBlaster_No_DDS,
)

__all__ = [
    'PulseBlaster', 'PulseBlaster_No_DDS',
]

__getattr__ = lazy_attributes(
    __name__,
    {
        'blacs_tabs': [
            'Pulseblaster_No_DDS_Tab',
        ],
        'blacs_workers': [
            'PulseblasterNoDDSWorker',
        ],
        'runviewer_parsers': [
            'PulseBlasterParser', 'PulseBlaster_No_DDS_Parser',
        ],
    },
)
