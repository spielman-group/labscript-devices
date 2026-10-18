#####################################################################
#                                                                   #
# /labscript_devices/PhaseMatrixQuickSyn/__init__.py                #
#                                                                   #
# Copyright 2013, Monash University                                 #
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
    BLACS_tab, lazy_attributes, runviewer_parser,
)
from .labscript_devices import (
    np, Device, StaticDDS, StaticAnalogQuantity, StaticDigitalOut, compiler,
    LabscriptError, set_passed_properties, labscript_utils, QuickSynDDS,
    PhaseMatrixQuickSyn,
)

__getattr__ = lazy_attributes(
    __name__,
    {
        'blacs_tabs': [
            'define_state', 'MODE_MANUAL', 'MODE_TRANSITION_TO_BUFFERED',
            'MODE_TRANSITION_TO_MANUAL', 'MODE_BUFFERED', 'DeviceTab',
            'UiLoader', 'os', 'PhaseMatrixQuickSynTab',
        ],
        'blacs_workers': [
            'Worker', 'QuickSynWorker',
        ],
    },
)
