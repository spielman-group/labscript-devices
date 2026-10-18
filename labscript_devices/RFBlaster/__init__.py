#####################################################################
#                                                                   #
# /labscript_devices/RFBlaster/__init__.py                          #
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
    os, PseudoclockDevice, Pseudoclock, ClockLine, IntermediateDevice, DDS,
    compiler, startupinfo, LabscriptError, set_passed_properties, np,
    RFBlasterPseudoclock, RFBlaster, RFBlasterDirectOutputs,
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
            'RFBlasterTab',
        ],
        'blacs_workers': [
            'setup_logging', 'PseudoclockWorker', 'MultiPartForm',
            'RFBlasterWorker',
        ],
    },
)
