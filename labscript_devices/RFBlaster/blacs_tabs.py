#####################################################################
#                                                                   #
# /labscript_devices/RFBlaster/blacs_tabs.py                        #
#                                                                   #
# Copyright 2013, Monash University                                 #
#                                                                   #
# This file is part of labscript_devices, in the labscript suite    #
# (see http://labscriptsuite.org), and is licensed under the        #
# Simplified BSD License. See the license.txt file in the root of   #
# the project for the full license.                                 #
#                                                                   #
#####################################################################

from blacs.tab_base_classes import define_state
from blacs.tab_base_classes import (
    MODE_MANUAL,
    MODE_TRANSITION_TO_BUFFERED,
    MODE_TRANSITION_TO_MANUAL,
    MODE_BUFFERED,
)
from blacs.device_base_class import DeviceTab


class RFBlasterTab(DeviceTab):
    def initialise_GUI(self):
        self.base_units =     {'freq':'Hz',        'amp':'Arb',       'phase':'Degrees'}
        self.base_min =       {'freq':500000,      'amp':0.0,         'phase':0}
        self.base_max =       {'freq':350000000.0, 'amp':0.9999389648, 'phase':360}
        self.base_step =      {'freq':1000000,     'amp':0.01,        'phase':1}
        self.base_decimals =  {'freq':1,           'amp':5,           'phase':3}
        self.num_DDS = 2

        dds_prop = {}
        for i in range(self.num_DDS):
            dds_prop[f'dds {i}'] = {}
            for subchnl in ['freq', 'amp', 'phase']:
                dds_prop[f'dds {i}'][subchnl] = {'base_unit':self.base_units[subchnl],
                                                 'min':self.base_min[subchnl],
                                                 'max':self.base_max[subchnl],
                                                 'step':self.base_step[subchnl],
                                                 'decimals':self.base_decimals[subchnl]
                                                }
            dds_prop[f'dds {i}']['gate'] = {}

        self.create_dds_outputs(dds_prop)
        dds_widgets, ao_widgets, do_widgets = self.auto_create_widgets()
        self.auto_place_widgets(("DDS Outputs", dds_widgets))

        # The URL of the board's web interface, which the worker contacts.
        self.address = f"http://{self.BLACS_connection}:8080"

        self.supports_remote_value_check(True)
        self.supports_smart_programming(False)

    def initialise_workers(self):
        self.create_worker(
            "main_worker",
            'labscript_devices.RFBlaster.blacs_workers.RFBlasterWorker',
            {'address': self.address, 'num_DDS': self.num_DDS},
        )
        self.primary_worker = "main_worker"

    def get_child_from_connection_table(self, parent_device_name, port):
        if parent_device_name == self.device_name:
            device = self.connection_table.find_by_name(self.device_name)
            # An output of the board is on its RFBlasterDirectOutputs, the only child of
            # the clock line, which is the only child of the pseudoclock, the board's only
            # child. Look for the port there.
            pseudoclock = device.child_list[list(device.child_list.keys())[0]]
            clockline = pseudoclock.child_list[list(pseudoclock.child_list.keys())[0]]
            direct_outputs = clockline.child_list[list(clockline.child_list.keys())[0]]
            return DeviceTab.get_child_from_connection_table(self, direct_outputs.name, port)
        else:
            # Otherwise it is a child of a DDS, which the default lookup finds.
            return DeviceTab.get_child_from_connection_table(self, parent_device_name, port)

    # Unlike the base class's, this neither programs the device (slow) nor sets the last
    # programmed values to the front panel's, as the values the RFBlaster reports are
    # always the last manual ones programmed.
    @define_state(MODE_BUFFERED, False)
    def transition_to_manual(self, notify_queue, program=False):
        self.mode = MODE_TRANSITION_TO_MANUAL

        success = yield(self.queue_work(self._primary_worker, 'transition_to_manual'))
        for worker in self._secondary_workers:
            transition_success = yield(self.queue_work(worker, 'transition_to_manual'))
            if not transition_success:
                success = False
                # don't break here, so that as much of the device is returned to normal

        # Update the GUI with the final values of the run:
        for channel, value in self._final_values.items():
            if channel in self._AO:
                self._AO[channel].set_value(value, program=False)
            elif channel in self._DO:
                self._DO[channel].set_value(value, program=False)
            elif channel in self._DDS:
                self._DDS[channel].set_value(value, program=False)

        if success:
            notify_queue.put([self.device_name, 'success'])
            self.mode = MODE_MANUAL
        else:
            notify_queue.put([self.device_name, 'fail'])
            raise Exception(
                'Could not transition to manual. You must restart this device to continue'
            )
