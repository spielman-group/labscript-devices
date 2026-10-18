# /labscript_devices/AlazarTechBoard/__init__.py
#
# Hacked up from NIboard.py by LDT 2017-01-26
#
# Copyright (c) Monash University 2017

# The labscript-side names are imported here and make up __all__, so a star
# import of this package never loads BLACS. Its tab, worker and parser names
# load only when asked for by name.
from labscript_devices import lazy_attributes
from .labscript_devices import (
    AlazarTechBoard,
)

__all__ = [
    'AlazarTechBoard',
]

__getattr__ = lazy_attributes(
    __name__,
    {
        'blacs_tabs': [
            'GuilessTab',
        ],
        'blacs_workers': [
            'tqdm_kwargs', 'atsRanges', 'atsSampleRates',
            'atsExternalClockAdvice', 'find_nearest_internal_clock',
            'find_clock_and_r', 'ats9462_clock', 'GuilessWorker',
        ],
    },
)
