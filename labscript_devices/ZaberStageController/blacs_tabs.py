#####################################################################
#                                                                   #
# /labscript_devices/ZaberStageController/blacs_tabs.py             #
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
from .utils import get_device_number


class ZaberStageControllerTab(DeviceTab):
    def initialise_GUI(self):
        self.base_units = 'steps'
        self.base_min = 0
        self.base_step = 100
        self.base_decimals = 0

        device = self.settings['connection_table'].find_by_name(self.device_name)
        self.com_port = device.BLACS_connection
        self.mock = device.properties['mock']

        # One analog output for each stage, limited to the stage's `limits`.
        ao_prop = {}
        for stage in device.child_list.values():
            connection = stage.parent_port
            base_min, base_max = stage.properties['limits']
            ao_prop[connection] = {
                'base_unit': self.base_units,
                'min': base_min,
                'max': base_max,
                'step': self.base_step,
                'decimals': self.base_decimals,
            }
        # The outputs, and so child_connections, are in device-number order.
        ao_prop = {c: ao_prop[c] for c in sorted(ao_prop, key=get_device_number)}
        self.child_connections = list(ao_prop.keys())
        self.create_analog_outputs(ao_prop)
        _, ao_widgets, _ = self.auto_create_widgets()
        self.auto_place_widgets(("Zaber Stages", ao_widgets, get_device_number))

        self.supports_remote_value_check(True)
        self.supports_smart_programming(False)

    def initialise_workers(self):
        self.create_worker(
            "main_worker",
            "labscript_devices.ZaberStageController.blacs_workers.ZaberStageControllerWorker",
            {
                'com_port': self.com_port,
                'mock': self.mock,
                'child_connections': self.child_connections,
            },
        )
        self.primary_worker = "main_worker"
