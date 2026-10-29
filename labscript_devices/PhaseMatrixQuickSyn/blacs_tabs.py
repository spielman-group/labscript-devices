#####################################################################
#                                                                   #
# /labscript_devices/PhaseMatrixQuickSyn/blacs_tabs.py              #
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
from qtutils import UiLoader
import os


class PhaseMatrixQuickSynTab(DeviceTab):
    def initialise_GUI(self):
        # The limits are in Hz, those of PhaseMatrixQuickSyn.quantise_freq.
        dds_prop = {'dds 0': {'freq': {'base_unit': 'Hz',
                                       'min': 0.5e9,
                                       'max': 10e9,
                                       'step': 1e6,
                                       'decimals': 3},
                              'gate': {}}}

        self.create_dds_outputs(dds_prop)
        dds_widgets, ao_widgets, do_widgets = self.auto_create_widgets()
        self.auto_place_widgets(("DDS Outputs", dds_widgets))

        self.status_ui = UiLoader().load(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'phasematrixquicksyn.ui'))
        self.get_tab_layout().addWidget(self.status_ui)
        self.status_ui.ref_button.clicked.connect(self.update_reference_out)
        self.status_ui.blanking_button.clicked.connect(self.update_blanking)
        self.status_ui.lock_recovery_button.clicked.connect(self.update_lock_recovery)

        # The serial port the worker opens, from the connection table.
        self.address = str(self.settings['connection_table'].find_by_name(self.settings["device_name"]).BLACS_connection)

        self.supports_remote_value_check(True)
        self.supports_smart_programming(False)
        # Refresh the status widgets every 2 s, in every mode
        self.statemachine_timeout_add(2000, self.update_status)

    def initialise_workers(self):
        self.create_worker("main_worker", 'labscript_devices.PhaseMatrixQuickSyn.blacs_workers.PhaseMatrixQuickSynWorker', {'address': self.address})
        self.primary_worker = "main_worker"

    @define_state(MODE_MANUAL|MODE_BUFFERED|MODE_TRANSITION_TO_BUFFERED|MODE_TRANSITION_TO_MANUAL, True)
    def update_status(self):
        """Show the status the worker reports in the status widgets and buttons."""
        self.status = yield(self.queue_work(self._primary_worker, 'check_status'))
        self.status_ui.temperature_label.setText(str(self.status['temperature']))

        if self.status['freqlock']:
            self.status_ui.freq_lock_label.setText('locked')
        else:
            self.status_ui.freq_lock_label.setText('unlocked')

        if self.status['reflock'] and self.status['ref']:
            self.status_ui.ref_lock_label.setText('locked')
        elif self.status['ref']:
            self.status_ui.ref_lock_label.setText('unlocked')
        else:
            self.status_ui.ref_lock_label.setText('disconnected')

        self.status_ui.ref_button.setChecked(self.status['ref_output'])
        self.status_ui.blanking_button.setChecked(self.status['blanking'])
        self.status_ui.lock_recovery_button.setChecked(self.status['lock_recovery'])

    @define_state(MODE_MANUAL|MODE_BUFFERED|MODE_TRANSITION_TO_BUFFERED|MODE_TRANSITION_TO_MANUAL, True, True)
    def update_reference_out(self, button=None):
        value = self.status_ui.ref_button.isChecked()
        yield(self.queue_work(self._primary_worker, 'update_reference_out', value))

    @define_state(MODE_MANUAL|MODE_BUFFERED|MODE_TRANSITION_TO_BUFFERED|MODE_TRANSITION_TO_MANUAL, True, True)
    def update_blanking(self, button=None):
        value = self.status_ui.blanking_button.isChecked()
        yield(self.queue_work(self._primary_worker, 'update_blanking', value))

    @define_state(MODE_MANUAL|MODE_BUFFERED|MODE_TRANSITION_TO_BUFFERED|MODE_TRANSITION_TO_MANUAL, True, True)
    def update_lock_recovery(self, button=None):
        value = self.status_ui.lock_recovery_button.isChecked()
        yield(self.queue_work(self._primary_worker, 'update_lock_recovery', value))
