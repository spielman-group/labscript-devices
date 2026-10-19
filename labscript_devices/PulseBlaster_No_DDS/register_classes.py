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

import labscript_devices

labscript_device_name = 'PulseBlaster_No_DDS'
blacs_tab = 'labscript_devices.PulseBlaster_No_DDS.blacs_tabs.PulseBlaster_No_DDS_Tab'
parser = 'labscript_devices.PulseBlaster_No_DDS.runviewer_parsers.PulseBlaster_No_DDS_Parser'

labscript_devices.register_classes(
    labscript_device_name=labscript_device_name,
    BLACS_tab=blacs_tab,
    runviewer_parser=parser,
)
