# /labscript_devices/AlazarTechBoard/blacs_tabs.py
#
# Hacked up from NIboard.py by LDT 2017-01-26
#
# Copyright (c) Monash University 2017

from blacs.tab_base_classes import define_state
from blacs.tab_base_classes import MODE_MANUAL, MODE_TRANSITION_TO_BUFFERED, MODE_TRANSITION_TO_MANUAL, MODE_BUFFERED
from blacs.device_base_class import DeviceTab


# A BLACS tab for a purely remote device which does not need configuration of parameters in BLACS

class GuilessTab(DeviceTab):
    def initialise_GUI(self):
        pass

    def get_save_data(self):
        return {}

    def restore_save_data(self, save_data):
        pass

    def initialise_workers(self):
        # Create and set the primary worker
        self.create_worker("main_worker", 'labscript_devices.AlazarTechBoard.blacs_workers.GuilessWorker', {})
        self.primary_worker = "main_worker"
