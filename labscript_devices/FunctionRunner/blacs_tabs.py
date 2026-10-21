#####################################################################
#                                                                   #
# /labscript_devices/FunctionRunner/blacs_tabs.py                   #
#                                                                   #
# Copyright 2019, Monash University and contributors                #
#                                                                   #
# This file is part of labscript_devices, in the labscript suite    #
# (see http://labscriptsuite.org), and is licensed under the        #
# Simplified BSD License. See the license.txt file in the root of   #
# the project for the full license.                                 #
#                                                                   #
#####################################################################

from blacs.device_base_class import DeviceTab


class FunctionRunnerTab(DeviceTab):
    """A tab with no controls, showing the output of the functions its worker runs."""

    def restore_builtin_save_data(self, data):
        DeviceTab.restore_builtin_save_data(self, data)
        # Whatever was restored, show the output box and give it the whole tab.
        self.set_terminal_visible(True)
        self._ui.splitter.setSizes([0, 0, 1])

    def initialise_workers(self):
        self.create_worker(
            'main_worker',
            'labscript_devices.FunctionRunner.blacs_workers.FunctionRunnerWorker',
            {},
        )
        self.primary_worker = 'main_worker'
