#####################################################################
#                                                                   #
# /labscript_devices/PrawnBlaster/__init__.py                       #
#                                                                   #
# Copyright 2021, Philip Starkey                                    #
#                                                                   #
# This file is part of labscript_devices, in the labscript suite    #
# (see http://labscriptsuite.org), and is licensed under the        #
# Simplified BSD License. See the license.txt file in the root of   #
# the project for the full license.                                 #
#                                                                   #
#####################################################################

# The labscript-side names are imported here and make up __all__, so a star
# import of this package never loads BLACS. Its tab, worker and parser names
# load only when asked for by name.
from labscript_devices import lazy_attributes
from .labscript_devices import (
    PrawnBlaster,
)

__all__ = [
    'PrawnBlaster',
]

__getattr__ = lazy_attributes(
    __name__,
    {
        'blacs_tabs': [
            'PrawnBlasterTab',
        ],
        'blacs_workers': [
            'PrawnBlasterWorker',
        ],
        'runviewer_parsers': [
            'PrawnBlasterParser',
        ],
    },
)
