#####################################################################
#                                                                   #
# /labscript_devices/PineBlaster/blacs_tabs.py                      #
#                                                                   #
# Copyright 2013, Monash University                                 #
#                                                                   #
# This file is part of the module labscript_devices, in the         #
# labscript suite (see http://labscriptsuite.org), and is           #
# licensed under the Simplified BSD License. See the license.txt    #
# file in the root of the project for the full license.             #
#                                                                   #
#####################################################################


from blacs.device_base_class import DeviceTab
from labscript_devices.common.pseudoclock import PseudoclockTab


class PineBlasterTab(PseudoclockTab):
    def initialise_GUI(self):
        # The board's one output is its clock line, 'internal'.
        self.create_digital_outputs({'internal': {}})
        _, _, do_widgets = self.auto_create_widgets()
        self.auto_place_widgets(("Flags", do_widgets))

        self.com_port = str(
            self.settings['connection_table'].find_by_name(self.device_name).BLACS_connection
        )

        self.supports_smart_programming(True)

    def initialise_workers(self):
        self.create_worker(
            "main_worker",
            'labscript_devices.PineBlaster.blacs_workers.PineBlasterWorker',
            {'com_port': self.com_port},
        )
        self.primary_worker = "main_worker"

    def get_child_from_connection_table(self, parent_device_name, port):
        # The 'internal' output is a clock line, whose parent is the board's Pseudoclock,
        # so the default search under the board's name would not find it.
        if parent_device_name == self.device_name:
            device = self.connection_table.find_by_name(self.device_name)
            # The board has one child, its Pseudoclock.
            pseudoclock = device.child_list[list(device.child_list.keys())[0]]
            for child_name, child in pseudoclock.child_list.items():
                if child.parent_port == port:
                    return DeviceTab.get_child_from_connection_table(
                        self, pseudoclock.name, port
                    )

        return DeviceTab.get_child_from_connection_table(self, parent_device_name, port)
