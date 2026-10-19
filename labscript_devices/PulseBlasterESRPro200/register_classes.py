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

import labscript_devices

labscript_device_name = 'PulseBlasterESRPro200'
blacs_tab = 'labscript_devices.PulseBlasterESRPro200.blacs_tabs.PulseBlasterESRPro200Tab'
parser = 'labscript_devices.PulseBlasterESRPro200.runviewer_parsers.PulseBlasterESRPro200Parser'

labscript_devices.register_classes(
    labscript_device_name=labscript_device_name,
    BLACS_tab=blacs_tab,
    runviewer_parser=parser,
)
