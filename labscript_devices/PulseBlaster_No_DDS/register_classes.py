#####################################################################
#                                                                   #
# /labscript_devices/PulseBlaster_No_DDS/register_classes.py        #
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
    'PulseBlaster_No_DDS',
    BLACS_tab='labscript_devices.PulseBlaster_No_DDS.blacs_tabs.PulseBlaster_No_DDSTab',
    runviewer_parser='labscript_devices.PulseBlaster_No_DDS.runviewer_parsers.PulseBlaster_No_DDSParser',
)
