#####################################################################
#                                                                   #
# /labscript_devices/PulseBlasterESRPro200/register_classes.py      #
#                                                                   #
# Copyright 2013, Monash University                                 #
#                                                                   #
# This file is part of labscript_devices, in the labscript suite    #
# (see http://labscriptsuite.org), and is licensed under the        #
# Simplified BSD License. See the license.txt file in the root of   #
# the project for the full license.                                 #
#                                                                   #
#####################################################################
from labscript_devices import register_classes

register_classes(
    'PulseBlasterESRPro200',
    BLACS_tab='labscript_devices.PulseBlasterESRPro200.blacs_tabs.PulseBlasterESRPro200Tab',
    runviewer_parser='labscript_devices.PulseBlasterESRPro200.runviewer_parsers.PulseBlasterESRPro200Parser',
)
