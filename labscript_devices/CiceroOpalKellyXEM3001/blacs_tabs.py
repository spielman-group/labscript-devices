#####################################################################
#                                                                   #
# /labscript_devices/CiceroOpalKellyXEM3001/blacs_tabs.py           #
#                                                                   #
# Copyright 2013, Monash University                                 #
#                                                                   #
# This file is part of the module labscript_devices, in the         #
# labscript suite (see http://labscriptsuite.org), and is           #
# licensed under the Simplified BSD License. See the license.txt    #
# file in the root of the project for the full license.             #
#                                                                   #
#####################################################################

from blacs.tab_base_classes import define_state, Tab
from blacs.tab_base_classes import (
    MODE_MANUAL,
    MODE_TRANSITION_TO_BUFFERED,
    MODE_TRANSITION_TO_MANUAL,
    MODE_BUFFERED,
)

from blacs.device_base_class import DeviceTab
from labscript_devices.pseudoclock import PseudoclockTab

from qtutils.qt.QtWidgets import QPushButton


class CiceroOpalKellyXEM3001Tab(PseudoclockTab):
    def initialise_GUI(self):
        # True once flashing fails; get_save_data then leaves out the reference clock, so
        # the next start flashes again.
        self.failed_to_flash = False

        connection_object = self.settings['connection_table'].find_by_name(self.device_name)
        self.serial_number = str(connection_object.BLACS_connection)
        self.reference_clock = connection_object.properties.get('reference_clock', 'internal')
        self.logger.debug('reference clock scheme is: %s', self.reference_clock)

        # The worker programs the whole board for every shot.
        self.supports_smart_programming(False)

        self.flash_fpga_button = QPushButton(
            'Flash FPGA firmware (this should be handled automatically by BLACS, '
            'if the device is not working correctly, try this button!)'
        )
        self.flash_fpga_button.clicked.connect(self.flash_fpga)
        self.get_tab_layout().insertWidget(self.get_tab_layout().count()-1, self.flash_fpga_button)

    def initialise_workers(self):
        self.create_worker(
            "main_worker",
            'labscript_devices.CiceroOpalKellyXEM3001.blacs_workers.CiceroOpalKellyXEM3001Worker',
            {'serial_number': self.serial_number, "reference_clock": self.reference_clock},
        )
        self.primary_worker = "main_worker"
        # restore_save_data runs before the worker exists, so the flash it asked for waits
        # until now.
        if self.reflash:
            self.flash_fpga()

    def get_child_from_connection_table(self, parent_device_name, port):
        # An output of the board is a clock line, which hangs from its pseudoclock, the
        # child on 'clock'; a wait monitor's dummy pseudoclock is another child.
        if parent_device_name == self.device_name:
            device = self.connection_table.find_by_name(self.device_name)
            (pseudoclock,) = [c for c in device.child_list.values() if c.parent_port == 'clock']
            for child_name, child in pseudoclock.child_list.items():
                if child.parent_port == port:
                    return DeviceTab.get_child_from_connection_table(self, pseudoclock.name, port)

        return DeviceTab.get_child_from_connection_table(self, parent_device_name, port)

    def close_tab(self, *args, **kwargs):
        # Disconnect the button, so that it can be garbage collected when it is shortly
        # deleted.
        self.flash_fpga_button.clicked.disconnect(self.flash_fpga)
        return Tab.close_tab(self, *args, **kwargs)

    def restore_save_data(self, data):
        # Flash the FPGA if the type of reference clock has changed since last
        # time: now if its worker exists, else once initialise_workers makes it.
        self.reflash = (
            'reference_clock' not in data or self.reference_clock != data['reference_clock']
        )
        if self.reflash and self.primary_worker is not None:
            self.flash_fpga()

    @define_state(
        MODE_MANUAL | MODE_BUFFERED | MODE_TRANSITION_TO_BUFFERED | MODE_TRANSITION_TO_MANUAL,
        True,
    )
    def flash_fpga(self, ignore=None):
        ret = yield(self.queue_work(self.primary_worker, 'flash_FPGA'))
        if not ret:
            self.failed_to_flash = True

    def get_save_data(self):
        ret_data = {}
        # Leave out the current reference clock configuration if we failed to flash this
        # time. This forces a reflash the next time the device is initialised.
        if not self.failed_to_flash:
            ret_data['reference_clock'] = self.reference_clock
        return ret_data
