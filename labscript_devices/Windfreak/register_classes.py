#####################################################################
#                                                                   #
# /labscript_devices/Windfreak/register_classes.py                  #
#                                                                   #
# Copyright 2022, Monash University and contributors                #
#                                                                   #
# This file is part of labscript_devices, in the labscript suite    #
# (see http://labscriptsuite.org), and is licensed under the        #
# Simplified BSD License. See the license.txt file in the root of   #
# the project for the full license.                                 #
#                                                                   #
#####################################################################
from labscript_devices import register_classes

register_classes(
    'WindfreakSynthHD',
    BLACS_tab='labscript_devices.Windfreak.blacs_tabs.WindfreakSynthHDTab',
    runviewer_parser=None,
)

register_classes(
    'WindfreakSynthHDPro',
    BLACS_tab='labscript_devices.Windfreak.blacs_tabs.WindfreakSynthHDTab',
    runviewer_parser=None,
)
