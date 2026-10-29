#####################################################################
#                                                                   #
# /NI_DAQmx/blacs_tabs.py                                           #
#                                                                   #
# Copyright 2018, Monash University, JQI, Christopher Billington    #
#                                                                   #
# This file is part of the module labscript_devices, in the         #
# labscript suite (see http://labscriptsuite.org), and is           #
# licensed under the Simplified BSD License. See the license.txt    #
# file in the root of the project for the full license.             #
#                                                                   #
#####################################################################
import labscript_utils.h5_lock
import h5py
from labscript_utils import dedent
from labscript_profile.legacy_files import warn_legacy_file

from blacs.device_base_class import DeviceTab
from .utils import split_conn_AO, split_conn_DO
from . import models


class NI_DAQmxTab(DeviceTab):
    def initialise_GUI(self):
        connection_table = self.settings['connection_table']
        properties = connection_table.find_by_name(self.device_name).properties

        # Raise an error on old connection tables, since we are not backward compatible
        # with them. BLACS rejects old shot files queued once it has started, as their
        # connection table properties won't match, so they need no check here.
        version = properties.get('__version__', None)
        if version is None:
            msg = """Connection table was compiled with the old version of the NI_DAQmx
                device class. The new BLACS tab is not backward compatible with old shot
                files (including connection tables). Either downgrade labscript_devices
                to 2.4.0 or less, or recompile the connection table with
                labscript_devices 2.5.0 or greater.
                """
            raise RuntimeError(dedent(msg))

        num_AO = properties['num_AO']

        ports = properties['ports']

        AO_base_units = 'V'
        if num_AO > 0:
            AO_base_min, AO_base_max = properties['AO_range']
        else:
            AO_base_min, AO_base_max = None, None
        AO_base_step = 0.1
        AO_base_decimals = 3

        # The Measurement and Automation Explorer (MAX) name, which we need to
        # communicate with the device:
        self.MAX_name = properties['MAX_name']

        AO_prop = {}
        for i in range(num_AO):
            AO_prop[f'ao{i}'] = {
                'base_unit': AO_base_units,
                'min': AO_base_min,
                'max': AO_base_max,
                'step': AO_base_step,
                'decimals': AO_base_decimals,
            }

        DO_proplist = []
        for port_num in range(len(ports)):
            port_str = f'port{port_num}'
            port_props = {}
            for line in range(ports[port_str]['num_lines']):
                hardware_name = f'port{port_num}/line{line}'
                port_props[hardware_name] = {}
            DO_proplist.append((port_str, port_props))

        self.create_analog_outputs(AO_prop)

        # Create widgets for outputs defined so far (i.e. analog outputs only)
        _, AO_widgets, _ = self.auto_create_widgets()

        for _, DO_prop in DO_proplist:
            self.create_digital_outputs(DO_prop)

        # Manually create the digital output widgets so they are grouped separately
        DO_widgets_by_port = {}
        for port_str, DO_prop in DO_proplist:
            DO_widgets_by_port[port_str] = self.create_digital_widgets(DO_prop)

        # Auto place the widgets in the UI, specifying sort keys for ordering them:
        widget_list = [("Analog outputs", AO_widgets, split_conn_AO)]
        for port_num in range(len(ports)):
            port_str = f'port{port_num}'
            DO_widgets = DO_widgets_by_port[port_str]
            name = f"Digital outputs: {port_str}"
            if ports[port_str]['supports_buffered']:
                name += ' (buffered)'
            else:
                name += ' (static)'
            widget_list.append((name, DO_widgets, split_conn_DO))
        self.auto_place_widgets(*widget_list)

        self.supports_remote_value_check(False)
        self.supports_smart_programming(False)

    def initialise_workers(self):
        connection_table = self.settings['connection_table']
        properties = connection_table.find_by_name(self.device_name).properties
        num_AO = properties['num_AO']
        ports = properties['ports']
        if num_AO > 0:
            AO_base_min, AO_base_max = properties['AO_range']
        else:
            AO_base_min, AO_base_max = None, None
        num_AI = properties['num_AI']
        try:
            AI_chans = properties['AI_chans']
        except KeyError:
            # LEGACY MODEL SPECIFICATION COMPATIBILITY. DEPRECATED CODE, WILL BE REMOVED.
            # A table compiled from an older model specification file, without
            # AI_chans: assume the old behaviour, and warn.
            AI_chans = [f'ai{i:d}' for i in range(num_AI)]
            warn_legacy_file(
                connection_table.filepath,
                f"was compiled from {properties['MAX_name']}'s old model specification, "
                "without the AI_chans a recompile writes",
            )
        num_CI = properties['num_CI']
        clock_terminal = properties['clock_terminal']
        clock_mirror_terminal = properties['clock_mirror_terminal']
        static_AO = properties['static_AO']
        static_DO = properties['static_DO']
        clock_limit = properties['clock_limit']
        min_semiperiod_measurement = properties['min_semiperiod_measurement']

        with h5py.File(connection_table.filepath, 'r') as f:
            waits = f['waits']
            wait_acq_device = waits.attrs['wait_monitor_acquisition_device']
            wait_acq_connection = waits.attrs['wait_monitor_acquisition_connection']
            wait_timeout_device = waits.attrs['wait_monitor_timeout_device']
            wait_timeout_connection = waits.attrs['wait_monitor_timeout_connection']
            try:
                timeout_trigger_type = waits.attrs['wait_monitor_timeout_trigger_type']
            except KeyError:
                timeout_trigger_type = 'rising'

        self.create_worker(
            "main_worker",
            'labscript_devices.NI_DAQmx.blacs_workers.NI_DAQmxWorker',
            {
                'MAX_name': self.MAX_name,
                'Vmin': AO_base_min,
                'Vmax': AO_base_max,
                'num_AO': num_AO,
                'ports': ports,
                'clock_limit': clock_limit,
                'clock_terminal': clock_terminal,
                'clock_mirror_terminal': clock_mirror_terminal,
                'static_AO': static_AO,
                'static_DO': static_DO,
                'DO_hardware_names': list(self._DO),
                'wait_timeout_device': wait_timeout_device,
                'wait_timeout_connection': wait_timeout_connection,
                'wait_timeout_rearm_value': int(timeout_trigger_type == 'falling')
            },
        )
        self.primary_worker = "main_worker"

        # We only need a wait monitor worker if we are in fact the device with the wait
        # monitor input.
        if wait_acq_device == self.device_name:
            if wait_timeout_device:
                wait_timeout_device = connection_table.find_by_name(wait_timeout_device)
                wait_timeout_MAX_name = wait_timeout_device.properties['MAX_name']
            else:
                wait_timeout_MAX_name = None

            if num_CI == 0:
                msg = f"""{self.device_name} has no counter inputs, so it cannot be the
                    wait monitor acquisition device. Set the WaitMonitor's
                    acquisition_device to a device with counter inputs."""
                raise RuntimeError(dedent(msg))

            self.create_worker(
                "wait_monitor_worker",
                'labscript_devices.NI_DAQmx.blacs_workers.NI_DAQmxWaitMonitorWorker',
                {
                    'MAX_name': self.MAX_name,
                    'wait_acq_connection': wait_acq_connection,
                    'wait_timeout_MAX_name': wait_timeout_MAX_name,
                    'wait_timeout_connection': wait_timeout_connection,
                    'timeout_trigger_type': timeout_trigger_type,
                    'min_semiperiod_measurement': min_semiperiod_measurement,
                },
            )
            self.add_secondary_worker("wait_monitor_worker")

        # Add the acquisition worker after the wait monitor worker: BLACS runs secondary
        # workers' transition_to_manual in the order they were added, and the acquisition
        # processing needs the wait durations that the wait monitor works out there.
        if num_AI > 0:
            self.create_worker(
                "acquisition_worker",
                'labscript_devices.NI_DAQmx.blacs_workers.NI_DAQmxAcquisitionWorker',
                {
                    'MAX_name': self.MAX_name,
                    'num_AI': num_AI,
                    'AI_chans': AI_chans,
                    'AI_term': properties['AI_term'],
                    'AI_range': properties['AI_range'],
                    'AI_start_delay': properties['AI_start_delay'],
                    'AI_start_delay_ticks': properties['AI_start_delay_ticks'],
                    'AI_timebase_terminal': properties.get('AI_timebase_terminal',None),
                    'AI_timebase_rate': properties.get('AI_timebase_rate',None),
                    'clock_terminal': clock_terminal,
                },
            )
            self.add_secondary_worker("acquisition_worker")
