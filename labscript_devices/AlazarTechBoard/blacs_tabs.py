# /labscript_devices/AlazarTechBoard/blacs_tabs.py
#
# Hacked up from NIboard.py by LDT 2017-01-26
#
# Copyright (c) Monash University 2017

import labscript_devices.guiless as guiless


class AlazarTechBoardTab(guiless.GuilessTab):
    worker_class = 'labscript_devices.AlazarTechBoard.blacs_workers.AlazarTechBoardWorker'


# labscript_devices.AlazarTechBoard.GuilessTab is this board's tab.
GuilessTab = AlazarTechBoardTab
