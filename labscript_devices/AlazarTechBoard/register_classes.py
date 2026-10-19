# /labscript_devices/AlazarTechBoard/register_classes.py
#
# Hacked up from NIboard.py by LDT 2017-01-26
#
# Copyright (c) Monash University 2017


from labscript_devices import register_classes

register_classes(
    'AlazarTechBoard',
    BLACS_tab='labscript_devices.AlazarTechBoard.blacs_tabs.AlazarTechBoardTab',
    runviewer_parser=None,
)
