#####################################################################
#                                                                   #
# /labscript_devices/PulseBlaster/blacs_tabs.py                     #
#                                                                   #
# Copyright 2013, Monash University                                 #
#                                                                   #
# This file is part of the module labscript_devices, in the         #
# labscript suite (see http://labscriptsuite.org), and is           #
# licensed under the Simplified BSD License. See the license.txt    #
# file in the root of the project for the full license.             #
#                                                                   #
#####################################################################

from blacs.tab_base_classes import define_state
from blacs.tab_base_classes import MODE_MANUAL, MODE_TRANSITION_TO_BUFFERED, MODE_TRANSITION_TO_MANUAL, MODE_BUFFERED

from blacs.device_base_class import DeviceTab
from labscript_devices import import_class_by_fullname
from labscript_devices.pseudoclock import PseudoclockTab

from qtutils import UiLoader
import qtutils.icons
from qtutils.icons import Icon
import os

from labscript_utils.file_utils import warn_legacy_file
from labscript_utils.unitconversions import get_unit_conversion_class

from qtutils.qt import QtGui


class PulseBlasterBaseTab(PseudoclockTab):
    """The tab of a PulseBlaster board's flags, as many as the connection table's
    ``n_flags``. A board's class sets ``worker_class``, the full import path of its
    worker."""

    # A lab's own tab may name its worker class here instead, by upstream's name.
    device_worker_class = None

    def initialise_GUI(self):
        connection_object = self.settings['connection_table'].find_by_name(self.device_name)
        # LEGACY CONNECTION TABLE COMPATIBILITY. DEPRECATED CODE, WILL BE REMOVED.
        # A table from before n_flags was saved gets the count from the board's
        # labscript class, in this tab's package.
        if 'n_flags' not in connection_object.properties:
            warn_legacy_file(
                self.settings['connection_table'].filepath,
                "lacks the PulseBlaster's n_flags, which a recompile writes",
            )
            package = type(self).__module__.rsplit('.', 1)[0]
            board = import_class_by_fullname(f'{package}.{connection_object.device_class}')
            self.n_flags = board.n_flags
        else:
            self.n_flags = connection_object.properties['n_flags']

        do_prop = {}
        for i in range(self.n_flags):
            do_prop['flag %d'%i] = {}

        self.create_digital_outputs(do_prop)
        *other_widgets, do_widgets = self.auto_create_widgets()

        def sort(channel):
            flag = channel.replace('flag ','')
            flag = int(flag)
            return '%02d'%(flag)

        # Any other outputs a subclass made come before the flags, in blacs' palettes.
        self.auto_place_widgets(*other_widgets, ("Flags", do_widgets, sort))

        self.board_number = int(connection_object.BLACS_connection)

        # How buffered output is programmed and triggered; a connection table from before
        # it existed lacks it, and gets the default.
        self.programming_scheme = connection_object.properties.get('programming_scheme', 'pb_start/BRANCH')
        # LEGACY CONNECTION TABLE COMPATIBILITY. DEPRECATED CODE, WILL BE REMOVED.
        if 'programming_scheme' not in connection_object.properties:
            warn_legacy_file(
                self.settings['connection_table'].filepath,
                "lacks the PulseBlaster's programming_scheme, which a recompile writes",
            )

        self.supports_smart_programming(True)

        ui = UiLoader().load(os.path.join(os.path.dirname(os.path.realpath(__file__)),'pulseblaster.ui'))
        self.get_tab_layout().addWidget(ui)
        ui.start_button.clicked.connect(self.start)
        ui.stop_button.clicked.connect(self.stop)
        ui.reset_button.clicked.connect(self.reset)
        ui.start_button.setIcon(QtGui.QIcon(':/qtutils/fugue/control'))
        ui.start_button.setToolTip('Start')
        ui.stop_button.setIcon(QtGui.QIcon(':/qtutils/fugue/control-stop-square'))
        ui.stop_button.setToolTip('Stop')
        ui.reset_button.setIcon(QtGui.QIcon(':/qtutils/fugue/arrow-circle'))
        ui.reset_button.setToolTip('Reset')

        self.status_states = ['stopped', 'reset', 'running', 'waiting']
        self.status = {}
        self.status_widgets = {}
        for state in self.status_states:
            self.status[state] = False
            self.status_widgets[state] = getattr(ui,'%s_label'%state)

        # Refresh the status widgets every 2 s, in every mode
        self.statemachine_timeout_add(2000, self.update_status)

    def initialise_workers(self):
        worker_class = self.device_worker_class or self.worker_class
        # BLACS passes the connection table's n_flags too; given here for a table without it.
        self.create_worker("main_worker",worker_class,
                           {'board_number':self.board_number,
                            'n_flags': self.n_flags,
                            'programming_scheme': self.programming_scheme})
        self.primary_worker = "main_worker"

    def get_child_from_connection_table(self, parent_device_name, port):
        # The port is a clock line of the pseudoclock, or a direct output, which is on
        # the internal intermediate device, PulseBlasterDirectOutputs.
        if parent_device_name == self.device_name:
            device = self.connection_table.find_by_name(self.device_name)
            pseudoclock = device.child_list[list(device.child_list.keys())[0]] # there should always be one (and only one) child, the Pseudoclock
            clockline = None
            for child_name, child in pseudoclock.child_list.items():
                if child.parent_port == 'internal':
                    clockline = child
                elif child.parent_port == port:
                    return child

            if clockline is not None:
                # There should only be one child of this clock line, the direct outputs
                direct_outputs = clockline.child_list[list(clockline.child_list.keys())[0]]
                return DeviceTab.get_child_from_connection_table(self, direct_outputs.name, port)
            else:
                return ''
        else:
            # A child of a DDS, which the default search finds
            return DeviceTab.get_child_from_connection_table(self, parent_device_name, port)

    @define_state(MODE_MANUAL|MODE_BUFFERED|MODE_TRANSITION_TO_BUFFERED|MODE_TRANSITION_TO_MANUAL,True)
    def update_status(self):
        self.status, _, _ = yield(self.queue_work(self._primary_worker,'check_status'))

        for state in self.status_states:
            if self.status[state]:
                icon = Icon(':/qtutils/fugue/tick')
            else:
                icon = Icon(':/qtutils/fugue/cross')
            self.status_widgets[state].setIcon(icon)

    @define_state(MODE_MANUAL|MODE_BUFFERED|MODE_TRANSITION_TO_BUFFERED|MODE_TRANSITION_TO_MANUAL,True)
    def start(self,widget=None):
        yield(self.queue_work(self._primary_worker,'start_run'))
        self.update_status()

    @define_state(MODE_MANUAL|MODE_BUFFERED|MODE_TRANSITION_TO_BUFFERED|MODE_TRANSITION_TO_MANUAL,True)
    def stop(self,widget=None):
        yield(self.queue_work(self._primary_worker,'pb_stop'))
        self.update_status()

    @define_state(MODE_MANUAL|MODE_BUFFERED|MODE_TRANSITION_TO_BUFFERED|MODE_TRANSITION_TO_MANUAL,True)
    def reset(self,widget=None):
        yield(self.queue_work(self._primary_worker,'pb_reset'))
        self.update_status()

    def shot_over(self):
        if self.programming_scheme == 'pb_stop_programming/STOP':
            # Not clear that on all models the outputs will be correct after being
            # stopped this way, so we do program_manual with current values to be sure:
            self.program_device()


class DDSPulseBlasterTabMixin:
    """The tab's part for the two DDS outputs of a PulseBlaster board that has
    them. It comes before :class:`PulseBlasterBaseTab` in a board's bases."""

    def initialise_GUI(self):
        self.base_units     = {'freq':'Hz',        'amp':'Arb', 'phase':'Degrees'}
        self.base_min       = {'freq':0.3,         'amp':0.0,   'phase':0}
        self.base_max       = {'freq':150000000.0, 'amp':1.0,   'phase':360}
        self.base_step      = {'freq':1000000,     'amp':0.01,  'phase':1}
        self.base_decimals  = {'freq':1,           'amp':3,     'phase':3}
        self.num_DDS = 2

        dds_prop = {}
        for i in range(self.num_DDS):
            dds_prop['dds %d'%i] = {}
            for subchnl in ['freq', 'amp', 'phase']:
                dds_prop['dds %d'%i][subchnl] = {'base_unit':self.base_units[subchnl],
                                                 'min':self.base_min[subchnl],
                                                 'max':self.base_max[subchnl],
                                                 'step':self.base_step[subchnl],
                                                 'decimals':self.base_decimals[subchnl]
                                                }
            dds_prop['dds %d'%i]['gate'] = {}
            dds_prop['dds %d'%i]['amp']['base_unit'] = self.legacy_amplitude_unit(i)

        # Create the output objects, before the base class makes the flags
        self.create_dds_outputs(dds_prop)
        super().initialise_GUI()

    # LEGACY VPP AMPLITUDE COMPATIBILITY. DEPRECATED CODE, WILL BE REMOVED.
    def legacy_amplitude_unit(self, i):
        """'Vpp', the amplitude's old name for the same 0 to 1, if DDS `i`'s
        amplitude calibration is written for it, else 'Arb'."""
        dds = self.get_child_from_connection_table(self.device_name, 'dds %d' % i)
        amplitude = dds and self.get_child_from_connection_table(dds.name, 'amp')
        if amplitude and amplitude.unit_conversion_class:
            try:
                cls = get_unit_conversion_class(amplitude.unit_conversion_class)
            except (ImportError, AttributeError, KeyError):
                return 'Arb'
            if cls.base_unit == 'Vpp':
                warn_legacy_file(
                    self.settings['connection_table'].filepath,
                    f"gives a PulseBlaster DDS amplitude {cls.__name__}, a calibration "
                    "in 'Vpp', not 'Arb'",
                )
                return 'Vpp'
        return 'Arb'


class PulseBlasterTab(DDSPulseBlasterTabMixin, PulseBlasterBaseTab):
    worker_class = 'labscript_devices.PulseBlaster.blacs_workers.PulseBlasterWorker'
