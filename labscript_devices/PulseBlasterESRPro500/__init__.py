#####################################################################
#                                                                   #
# /labscript_devices/PulseBlasterESRPro500/__init__.py              #
#                                                                   #
# Copyright 2013, Monash University                                 #
#                                                                   #
# This file is part of labscript_devices, in the labscript suite    #
# (see http://labscriptsuite.org), and is licensed under the        #
# Simplified BSD License. See the license.txt file in the root of   #
# the project for the full license.                                 #
#                                                                   #
#####################################################################

# The names this package gives. The compile side's are imported here; those of
# BLACS and runviewer load only when asked for, so a compile never imports
# BLACS.
from labscript_devices import (
    BLACS_tab, lazy_attributes, runviewer_parser,
)
from .labscript_devices import (
    PulseBlaster_No_DDS, PulseBlasterESRPro500,
)

__getattr__ = lazy_attributes(
    __name__,
    {
        'blacs_tabs': [
            'Pulseblaster_No_DDS_Tab', 'pulseblasteresrpro500',
        ],
        'blacs_workers': [
            'PulseblasterNoDDSWorker', 'PulseblasterESRPro500Worker',
        ],
    },
)
