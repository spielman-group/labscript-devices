# /labscript_devices/AlazarTechBoard/__init__.py
#
# Hacked up from NIboard.py by LDT 2017-01-26
#
# Copyright (c) Monash University 2017
from labscript_devices import BLACS_tab, lazy_attributes
from .labscript_devices import (
    np, signal, ats, Device, AnalogIn, compiler, set_passed_properties,
    AlazarTechBoard, os, copy,
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
            'GuilessTab',
        ],
        'blacs_workers': [
            'ctypes', 'sys', 'time', 'tqdm', 'tqdm_kwargs', 'atsRanges',
            'atsSampleRates', 'atsExternalClockAdvice', 'LabscriptError',
            'labscript_utils', 'h5py', 'Worker', 'find_nearest_internal_clock',
            'find_clock_and_r', 'ats9462_clock', 'GuilessWorker',
        ],
    },
)
