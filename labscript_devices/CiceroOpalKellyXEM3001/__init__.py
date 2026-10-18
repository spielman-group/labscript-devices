#####################################################################
#                                                                   #
# /labscript_devices/CiceroOpalKellyXEM3001/__init__.py             #
#                                                                   #
# Copyright 2013, Monash University                                 #
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
    CiceroOpalKellyXEM3001,
)

__all__ = [
    'CiceroOpalKellyXEM3001',
]

__getattr__ = lazy_attributes(
    __name__,
    {
        'blacs_tabs': [
            'CiceroOpalKellyXEM3001Tab',
        ],
        'blacs_workers': [
            'int_to_bytes', 'bits_to_int', 'add_instruction_to_bytearray',
            'CiceroOpalKellyXEM3001Worker',
        ],
        'runviewer_parsers': [
            'RunviewerClass',
        ],
    },
)
