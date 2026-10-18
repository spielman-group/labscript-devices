#####################################################################
#                                                                   #
# /labscript_devices/LightCrafterDMD/register_classes.py            #
#                                                                   #
# Copyright 2017, Monash University                                 #
#                                                                   #
# This file is part of labscript_devices, in the labscript suite    #
# (see http://labscriptsuite.org), and is licensed under the        #
# Simplified BSD License. See the license.txt file in the root of   #
# the project for the full license.                                 #
#                                                                   #
#####################################################################

import labscript_devices

labscript_device_name = 'LightCrafterDMD'
blacs_tab = 'labscript_devices.LightCrafterDMD.blacs_tabs.LightCrafterTab'

labscript_devices.register_classes(
    labscript_device_name=labscript_device_name,
    BLACS_tab=blacs_tab,
    runviewer_parser=None,
)
