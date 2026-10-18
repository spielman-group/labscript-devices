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
from labscript_devices import BLACS_tab, lazy_attributes, runviewer_parser
from .labscript_devices import (
    dedent, Device, PseudoclockDevice, Pseudoclock, ClockLine,
    IntermediateDevice, DigitalQuantity, DigitalOut, DDS, DDSQuantity,
    LabscriptError, set_passed_properties, compiler, np, PulseBlasterDDS,
    PulseBlaster, PulseBlasterDirectOutputs,
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
            'UiLoader', 'qtutils', 'os', 'QtCore', 'QtGui', 'PulseBlasterTab',
        ],
        'blacs_workers': [
            'PseudoclockWorker', 'PulseblasterWorker',
        ],
        'runviewer_parsers': [
            'labscript_utils', 'h5py', 'time', 'profiles', 'profile',
            'start_profile', 'stop_profile', 'PulseBlasterParser',
        ],
    },
)
