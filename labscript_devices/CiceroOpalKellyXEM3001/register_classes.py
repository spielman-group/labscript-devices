#####################################################################
#                                                                   #
# /labscript_devices/CiceroOpalKellyXEM3001/register_classes.py     #
#                                                                   #
# Copyright 2013, Monash University                                 #
#                                                                   #
# This file is part of the module labscript_devices, in the         #
# labscript suite (see http://labscriptsuite.org), and is           #
# licensed under the Simplified BSD License. See the license.txt    #
# file in the root of the project for the full license.             #
#                                                                   #
#####################################################################

import labscript_devices

labscript_device_name = 'CiceroOpalKellyXEM3001'
blacs_tab = 'labscript_devices.CiceroOpalKellyXEM3001.blacs_tabs.CiceroOpalKellyXEM3001Tab'
parser = 'labscript_devices.CiceroOpalKellyXEM3001.runviewer_parsers.CiceroOpalKellyXEM3001Parser'

labscript_devices.register_classes(
    labscript_device_name=labscript_device_name,
    BLACS_tab=blacs_tab,
    runviewer_parser=parser,
)
