#####################################################################
#                                                                   #
# /labscript_devices/PulseBlaster/__init__.py                       #
#                                                                   #
# Copyright 2013, Monash University                                 #
#                                                                   #
# This file is part of the module labscript_devices, in the         #
# labscript suite (see http://labscriptsuite.org), and is           #
# licensed under the Simplified BSD License. See the license.txt    #
# file in the root of the project for the full license.             #
#                                                                   #
#####################################################################

from labscript_devices import lazy_attributes
from .labscript_devices import PulseBlasterDDS, PulseBlaster, PulseBlasterDirectOutputs

__getattr__ = lazy_attributes(
    __name__,
    {
        'blacs_tabs': ['PulseBlasterTab'],
        'blacs_workers': ['PulseblasterWorker'],
        'runviewer_parsers': [
            'profiles',
            'profile',
            'start_profile',
            'stop_profile',
            'PulseBlasterParser',
        ],
    },
)
