#####################################################################
#                                                                   #
# /labscript_devices/AD9959DDSSweeper/blacs_tabs.py                 #
#                                                                   #
# Copyright 2025, Carter Turnbaugh                                  #
#                                                                   #
# This file is part of the module labscript_devices, in the         #
# labscript suite (see http://labscriptsuite.org), and is           #
# licensed under the Simplified BSD License. See the license.txt    #
# file in the root of the project for the full license.             #
#                                                                   #
#####################################################################
# The labscript-side names are imported here and make up __all__, so a star
# import of this package never loads BLACS. Its tab, worker and parser names
# load only when asked for by name.
from labscript_devices import lazy_attributes
from .labscript_devices import (
    AD9959DDSSweeper,
)

__all__ = [
    'AD9959DDSSweeper',
]

__getattr__ = lazy_attributes(
    __name__,
    {
        'blacs_tabs': [
            'AD9959DDSSweeperTab',
        ],
        'blacs_workers': [
            'AD9959DDSSweeperWorker',
        ],
        'runviewer_parsers': [
            'AD9959DDSSweeperParser',
        ],
    },
)
