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

from labscript_devices import lazy_attributes
from .labscript_devices import PulseBlaster_SP2_24_100_32k

__getattr__ = lazy_attributes(
    __name__,
    {
        'blacs_tabs': ['PulseBlaster_SP2_24_100_32k_Tab'],
        'blacs_workers': ['PulseBlaster_SP2_24_100_32k_Worker'],
        'runviewer_parsers': ['PulseBlaster_SP2_24_100_32k_Parser'],
    },
)
