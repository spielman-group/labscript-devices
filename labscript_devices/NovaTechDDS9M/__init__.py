#####################################################################
#                                                                   #
# /labscript_devices/NovaTechDDS9M/__init__.py                      #
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
    IntermediateDevice, DDS, StaticDDS, Device, compiler, LabscriptError,
    set_passed_properties, NovaTechDDS9mFreqConversion,
    NovaTechDDS9mAmpConversion, np, bauds, NovaTechDDS9M,
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
            'NovatechDDS9MTab',
        ],
        'blacs_workers': [
            'time', 'Worker', 'NovatechDDS9mWorker',
        ],
        'runviewer_parsers': [
            'labscript_utils', 'h5py', 'RunviewerClass',
        ],
    },
)
