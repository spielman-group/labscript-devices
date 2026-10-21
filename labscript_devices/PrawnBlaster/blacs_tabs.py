#####################################################################
#                                                                   #
# /labscript_devices/PrawnBlaster/blacs_tabs.py                     #
#                                                                   #
# Copyright 2021, Philip Starkey                                    #
#                                                                   #
# This file is part of labscript_devices, in the labscript suite    #
# (see http://labscriptsuite.org), and is licensed under the        #
# Simplified BSD License. See the license.txt file in the root of   #
# the project for the full license.                                 #
#                                                                   #
#####################################################################
from blacs.device_base_class import (
    DeviceTab,
    define_state,
    MODE_BUFFERED,
    MODE_MANUAL,
    MODE_TRANSITION_TO_BUFFERED,
    MODE_TRANSITION_TO_MANUAL,
)
import labscript_utils.properties

from qtutils.qt import QtWidgets
from labscript_devices.pseudoclock import PseudoclockTab


class PrawnBlasterTab(PseudoclockTab):
    """BLACS Tab for the PrawnBlaster Device."""

    def initialise_GUI(self):
        self.connection_table_properties = (
            self.settings["connection_table"].find_by_name(self.device_name).properties
        )

        digital_outs = {}
        for pin in self.connection_table_properties["out_pins"]:
            digital_outs[f"GPIO {pin:02d}"] = {}

        self.create_digital_outputs(digital_outs)
        _, _, do_widgets = self.auto_create_widgets()
        self.auto_place_widgets(("Flags", do_widgets))

        self.status_label = QtWidgets.QLabel("Status: Unknown")
        self.clock_status_label = QtWidgets.QLabel("Clock status: Unknown")
        self.get_tab_layout().addWidget(self.status_label)
        self.get_tab_layout().addWidget(self.clock_status_label)

        self.supports_smart_programming(True)

        # Refresh the status labels every 2 s, in every mode
        self.statemachine_timeout_add(2000, self.update_status)

    def get_child_from_connection_table(self, parent_device_name, port):
        """Finds the attached ClockLines."""

        # Pass down channel name search to the pseudoclocks (so we can find the
        # clocklines)
        if parent_device_name == self.device_name:
            device = self.connection_table.find_by_name(self.device_name)

            for pseudoclock_name, pseudoclock in device.child_list.items():
                for child_name, child in pseudoclock.child_list.items():
                    if child.parent_port == port:
                        return DeviceTab.get_child_from_connection_table(
                            self, pseudoclock.name, port
                        )

        return None

    def initialise_workers(self):
        com_port = str(
            self.settings["connection_table"]
            .find_by_name(self.device_name)
            .BLACS_connection
        )

        worker_initialisation_kwargs = {
            "com_port": com_port,
            "num_pseudoclocks": self.connection_table_properties["num_pseudoclocks"],
            "out_pins": self.connection_table_properties["out_pins"],
            "in_pins": self.connection_table_properties["in_pins"],
        }
        self.create_worker(
            "main_worker",
            "labscript_devices.PrawnBlaster.blacs_workers.PrawnBlasterWorker",
            worker_initialisation_kwargs,
        )
        self.primary_worker = "main_worker"

    @define_state(
        MODE_MANUAL
        | MODE_BUFFERED
        | MODE_TRANSITION_TO_BUFFERED
        | MODE_TRANSITION_TO_MANUAL,
        True,
    )
    def update_status(self):
        """Shows the PrawnBlaster's run and clock status."""
        status, clock_status, _ = yield (
            self.queue_work(self.primary_worker, "check_status")
        )
        self.status_label.setText(f"Status: {status}")
        self.clock_status_label.setText(f"Clock status: {clock_status}")
