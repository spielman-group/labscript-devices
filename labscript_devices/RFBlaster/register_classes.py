#####################################################################
#                                                                   #
# /labscript_devices/RFBlaster/register_classes.py                  #
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
    'RFBlaster',
    BLACS_tab='labscript_devices.RFBlaster.blacs_tabs.RFBlasterTab',
    runviewer_parser=None,
)
