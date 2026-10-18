# /labscript_devices/AlazarTechBoard/__init__.py
#
# Hacked up from NIboard.py by LDT 2017-01-26
#
# Copyright (c) Monash University 2017

from labscript_devices import lazy_attributes
from .labscript_devices import AlazarTechBoard

__getattr__ = lazy_attributes(
    __name__,
    {
        'blacs_tabs': ['GuilessTab'],
        'blacs_workers': [
            'GuilessWorker', 'find_nearest_internal_clock', 'find_clock_and_r',
            'ats9462_clock', 'tqdm_kwargs', 'atsRanges', 'atsSampleRates',
            'atsExternalClockAdvice',
        ],
    },
)
