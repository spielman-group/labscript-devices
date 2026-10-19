#####################################################################
#                                                                   #
# /labscript_devices/DummyPseudoclock/register_classes.py           #
#                                                                   #
# Copyright 2017, Christopher Billington                            #
#                                                                   #
# This file is part of labscript_devices, in the labscript suite    #
# (see http://labscriptsuite.org), and is licensed under the        #
# Simplified BSD License. See the license.txt file in the root of   #
# the project for the full license.                                 #
#                                                                   #
#####################################################################
from labscript_devices import register_classes

register_classes(
    'DummyPseudoclock',
    BLACS_tab='labscript_devices.DummyPseudoclock.blacs_tabs.DummyPseudoclockTab',
    runviewer_parser='labscript_devices.DummyPseudoclock.runviewer_parsers.DummyPseudoclockParser',
)
