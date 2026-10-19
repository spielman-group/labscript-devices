#####################################################################
#                                                                   #
# /labscript_devices/PulseBlasterESRPro500/register_classes.py      #
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
    'PulseBlasterESRPro500',
    BLACS_tab='labscript_devices.PulseBlasterESRPro500.blacs_tabs.PulseBlasterESRPro500Tab',
    runviewer_parser='labscript_devices.PulseBlasterESRPro500.runviewer_parsers.PulseBlasterESRPro500Parser',
)
