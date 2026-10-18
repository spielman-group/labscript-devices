#####################################################################
#                                                                   #
# /labscript_devices/DummyIntermediateDevice/__init__.py            #
#                                                                   #
# Copyright 2013, Monash University                                 #
#                                                                   #
# This file is part of labscript_devices, in the labscript suite    #
# (see http://labscriptsuite.org), and is licensed under the        #
# Simplified BSD License. See the license.txt file in the root of   #
# the project for the full license.                                 #
#                                                                   #
#####################################################################
from labscript_devices import BLACS_tab, BLACS_worker, labscript_device, lazy_attributes
from .labscript_devices import (
    IntermediateDevice, DigitalOut, AnalogOut, compiler, np,
    DummyIntermediateDevice,
)

# Each name the old single-file module bound stays importable from here. Those
# of BLACS and runviewer load only when asked for, so a compile never imports
# BLACS.
__getattr__ = lazy_attributes(
    __name__,
    {
        'blacs_tabs': [
            'DeviceTab', 'DummyIntermediateDeviceTab',
        ],
        'blacs_workers': [
            'Worker', 'DummyIntermediateDeviceWorker',
        ],
    },
)
