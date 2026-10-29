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
from labscript_devices.common.deprecation import deprecated_names

# LEGACY DEVICE MODULE IMPORT PATH COMPATIBILITY. DEPRECATED CODE, WILL BE REMOVED.
__getattr__ = deprecated_names(
    __name__,
    {
        'labscript_devices': [
            'CiceroOpalKellyXEM3001',
        ],
        'blacs_tabs': [
            'CiceroOpalKellyXEM3001Tab',
        ],
        'blacs_workers': [
            'int_to_bytes',
            'bits_to_int',
            'add_instruction_to_bytearray',
            'CiceroOpalKellyXEM3001Worker',
        ],
    },
)
__all__ = ['CiceroOpalKellyXEM3001']
