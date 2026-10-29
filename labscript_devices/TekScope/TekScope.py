#####################################################################
#                                                                   #
# /labscript_devices/TekScope/TekScope.py                           #
#                                                                   #
# Copyright 2026, JQI                                               #
# Author: Ian Spielman                                              #
#                                                                   #
# This file is part of labscript_devices, in the labscript suite    #
# (see http://labscriptsuite.org), and is licensed under the        #
# Simplified BSD License. See the license.txt file in the root of   #
# the project for the full license.                                 #
#                                                                   #
#####################################################################
from labscript_devices.common.deprecation import deprecated_names

# LEGACY TEKSCOPE DRIVER MODULE COMPATIBILITY. DEPRECATED CODE, WILL BE REMOVED.
# The driver is labscript_devices.TekScope.driver; importing this module still
# shadows the package's TekScope class, as it always did.
__getattr__ = deprecated_names(
    __name__,
    {
        'labscript_devices.TekScope.driver': [
            'TekScope',
        ],
    },
)
__all__ = ['TekScope']
