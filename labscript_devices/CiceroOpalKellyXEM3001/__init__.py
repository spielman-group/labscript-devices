#####################################################################
#                                                                   #
# /labscript_devices/CiceroOpalKellyXEM3001/__init__.py             #
#                                                                   #
# Copyright 2013, Monash University                                 #
#                                                                   #
# This file is part of the module labscript_devices, in the         #
# labscript suite (see http://labscriptsuite.org), and is           #
# licensed under the Simplified BSD License. See the license.txt    #
# file in the root of the project for the full license.             #
#                                                                   #
#####################################################################
from labscript_devices import BLACS_tab, BLACS_worker, labscript_device, lazy_attributes, runviewer_parser
from .labscript_devices import (
    Device, PseudoclockDevice, Pseudoclock, ClockLine, LabscriptError,
    set_passed_properties, compiler, IntermediateDevice, WaitMonitor,
    DigitalOut, np, CiceroOpalKellyXEM3001Pseudoclock,
    CiceroOpalKellyXEM3001DummyPseudoclock,
    CiceroOpalKellyXEM3001DummyClockLine,
    CiceroOpalKellyXEM3001DummyIntermediateDevice, CiceroOpalKellyXEM3001,
)

# Each name the old single-file module bound stays importable from here. Those
# of BLACS and runviewer load only when asked for, so a compile never imports
# BLACS.
__getattr__ = lazy_attributes(
    __name__,
    {
        'blacs_tabs': [
            'define_state', 'Tab', 'MODE_MANUAL',
            'MODE_TRANSITION_TO_BUFFERED', 'MODE_TRANSITION_TO_MANUAL',
            'MODE_BUFFERED', 'DeviceTab', 'CiceroOpalKellyXEM3001Tab',
        ],
        'blacs_workers': [
            'labscript_utils', 'ensure_str', 'int_to_bytes', 'bits_to_int',
            'add_instruction_to_bytearray', 'PseudoclockWorker',
            'CiceroOpalKellyXEM3001Worker',
        ],
        'runviewer_parsers': [
            'h5py', 'RunviewerClass',
        ],
    },
)
