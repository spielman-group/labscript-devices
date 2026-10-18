#####################################################################
#                                                                   #
# /labscript_devices/PineBlaster/__init__.py                        #
#                                                                   #
# Copyright 2013, Monash University                                 #
#                                                                   #
# This file is part of the module labscript_devices, in the         #
# labscript suite (see http://labscriptsuite.org), and is           #
# licensed under the Simplified BSD License. See the license.txt    #
# file in the root of the project for the full license.             #
#                                                                   #
#####################################################################
from labscript_devices import BLACS_tab, lazy_attributes, runviewer_parser
from .labscript_devices import (
    PseudoclockDevice, Pseudoclock, ClockLine, compiler, LabscriptError,
    set_passed_properties, np, PineBlasterPseudoclock, PineBlaster,
)

# Each name the old single-file module bound stays importable from here. Those
# of BLACS and runviewer load only when asked for, so a compile never imports
# BLACS.
__getattr__ = lazy_attributes(
    __name__,
    {
        'blacs_tabs': [
            'define_state', 'MODE_MANUAL', 'MODE_TRANSITION_TO_BUFFERED',
            'MODE_TRANSITION_TO_MANUAL', 'MODE_BUFFERED', 'DeviceTab',
            'PineblasterTab',
        ],
        'blacs_workers': [
            'labscript_utils', 'PseudoclockWorker', 'PineblasterWorker',
        ],
        'runviewer_parsers': [
            'h5py', 'RunviewerClass',
        ],
    },
)
