#####################################################################
#                                                                   #
# /labscript_devices/GenICamCamera/__init__.py                      #
#                                                                   #
# Copyright 2026, Christopher Billington                            #
#                                                                   #
# This file is part of labscript_devices, in the labscript suite    #
# (see http://labscriptsuite.org), and is licensed under the        #
# Simplified BSD License. See the license.txt file in the root of   #
# the project for the full license.                                 #
#                                                                   #
#####################################################################

# The labscript-side names are imported here and make up __all__, so a star
# import of this package never loads BLACS. Its tab and worker names load
# only when asked for by name.
from labscript_devices import lazy_attributes
from .labscript_devices import (
    GenICamCamera,
)

__all__ = [
    'GenICamCamera',
]

__getattr__ = lazy_attributes(
    __name__,
    {
        'blacs_tabs': [
            'GenICamCameraTab',
        ],
        'blacs_workers': [
            'GenICamCameraWorker',
        ],
    },
)
