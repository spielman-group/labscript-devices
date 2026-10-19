#####################################################################
#                                                                   #
# /labscript_devices/PrawnBlaster/register_classes.py               #
#                                                                   #
# Copyright 2021, Philip Starkey                                    #
#                                                                   #
# This file is part of labscript_devices, in the labscript suite    #
# (see http://labscriptsuite.org), and is licensed under the        #
# Simplified BSD License. See the license.txt file in the root of   #
# the project for the full license.                                 #
#                                                                   #
#####################################################################
from labscript_devices import register_classes

register_classes(
    'PrawnBlaster',
    BLACS_tab='labscript_devices.PrawnBlaster.blacs_tabs.PrawnBlasterTab',
    runviewer_parser='labscript_devices.PrawnBlaster.runviewer_parsers.PrawnBlasterParser',
)
