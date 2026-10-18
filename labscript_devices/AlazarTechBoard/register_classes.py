# /labscript_devices/AlazarTechBoard/register_classes.py
#
# Hacked up from NIboard.py by LDT 2017-01-26
#
# Copyright (c) Monash University 2017

import labscript_devices

labscript_device_name = 'AlazarTechBoard'
blacs_tab = 'labscript_devices.AlazarTechBoard.blacs_tabs.AlazarTechBoardTab'

labscript_devices.register_classes(
    labscript_device_name=labscript_device_name,
    BLACS_tab=blacs_tab,
    runviewer_parser=None,
)
