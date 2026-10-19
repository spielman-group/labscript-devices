#####################################################################
#                                                                   #
# /labscript_devices/PhaseMatrixQuickSyn/register_classes.py        #
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
    'PhaseMatrixQuickSyn',
    BLACS_tab='labscript_devices.PhaseMatrixQuickSyn.blacs_tabs.PhaseMatrixQuickSynTab',
    runviewer_parser=None,
)
