#####################################################################
#                                                                   #
# /labscript_devices/atsapi.py                                      #
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
import warnings

# LEGACY ATSAPI IMPORT PATH COMPATIBILITY. DEPRECATED CODE, WILL BE REMOVED.
warnings.warn(
    "labscript_devices.atsapi will be removed; import "
    "labscript_devices.AlazarTechBoard.atsapi.",
    FutureWarning,
    stacklevel=2,
)
from labscript_devices.AlazarTechBoard.atsapi import *
