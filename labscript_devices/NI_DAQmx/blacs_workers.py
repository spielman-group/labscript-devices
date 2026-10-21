#####################################################################
#                                                                   #
# /NI_DAQmx/blacs_workers.py                                        #
#                                                                   #
# Copyright 2018, Monash University, JQI, Christopher Billington    #
#                                                                   #
# This file is part of the module labscript_devices, in the         #
# labscript suite (see http://labscriptsuite.org), and is           #
# licensed under the Simplified BSD License. See the license.txt    #
# file in the root of the project for the full license.             #
#                                                                   #
#####################################################################
import sys
import time
import threading
from PyDAQmx import *
from PyDAQmx.DAQmxConstants import *
from PyDAQmx.DAQmxTypes import *
from PyDAQmx.DAQmxCallBack import *

import numpy as np
from numpy.lib.recfunctions import structured_to_unstructured
import labscript_utils.h5_lock
import h5py
from zprocess import Event
from zprocess.utils import _reraise

import labscript_utils.properties as properties
from labscript_utils import dedent
from labscript_utils import ensure_str

from blacs.tab_base_classes import Worker

from ..deadline import Deadline
from .utils import split_conn_port, split_conn_DO, split_conn_AI
from .daqmx_utils import incomplete_sample_detection


class NI_DAQmxWorker(Worker):
    def init(self):
        self.check_version()
        # Reset Device: clears previously added routes etc. Note: is insufficient for
        # some devices, which require power cycling to truly reset.
        DAQmxResetDevice(self.MAX_name)
        self.start_manual_mode_tasks()

    def stop_tasks(self):
        if self.AO_task is not None:
            self.AO_task.StopTask()
            self.AO_task.ClearTask()
            self.AO_task = None
        if self.DO_task is not None:
            self.DO_task.StopTask()
            self.DO_task.ClearTask()
            self.DO_task = None

    def shutdown(self):
        self.stop_tasks()

    def check_version(self):
        """Check the NI-DAQmx version is high enough to avoid a known bug."""
        major = uInt32()
        minor = uInt32()
        patch = uInt32()
        DAQmxGetSysNIDAQMajorVersion(major)
        DAQmxGetSysNIDAQMinorVersion(minor)
        DAQmxGetSysNIDAQUpdateVersion(patch)

        if major.value == 14 and minor.value < 2:
            msg = f"""There is a known bug with buffered shots using NI DAQmx v14.0.0.
                This bug does not exist on v14.2.0. You are currently using
                v{major.value}.{minor.value}.{patch.value}. Upgrade NI DAQmx to v14.2.0
                or higher."""
            raise Exception(dedent(msg))

    def start_manual_mode_tasks(self):
        if self.num_AO > 0:
            self.AO_task = Task()
        else:
            self.AO_task = None

        if self.ports:
            self.DO_task = Task()
        else:
            self.DO_task = None

        for i in range(self.num_AO):
            con = f"{self.MAX_name}/ao{i}"
            self.AO_task.CreateAOVoltageChan(
                con, "", self.Vmin, self.Vmax, DAQmx_Val_Volts, None
            )

        for port_str in sorted(self.ports, key=split_conn_port):
            if not self.ports[port_str]['num_lines']:
                continue
            con = f'{self.MAX_name}/{port_str}'
            self.DO_task.CreateDOChan(con, "", DAQmx_Val_ChanForAllLines)

        if self.AO_task is not None:
            self.AO_task.StartTask()
        if self.DO_task is not None:
            self.DO_task.StartTask()

    def program_manual(self, front_panel_values):
        written = int32()
        if self.AO_task is not None:
            AO_data = np.zeros(self.num_AO, dtype=np.float64)
            for i in range(self.num_AO):
                AO_data[i] = front_panel_values[f'ao{i}']
            self.AO_task.WriteAnalogF64(
                1, True, 1, DAQmx_Val_GroupByChannel, AO_data, written, None
            )
        # Pack into a uint32 for WriteDigitalU32: WriteDigitalLines uses uninitialised
        # memory, and a smaller int dtype sometimes fails despite fitting the port (NI
        # forum, USB-6341). A uint32 always works; extra bits are ignored.
        if self.DO_task is not None:
            DO_data = np.zeros(len(self.ports), dtype=np.uint32)
            for conn, value in front_panel_values.items():
                if conn.startswith('port'):
                    port, line = split_conn_DO(conn)
                    DO_data[port] |= value << line
            self.DO_task.WriteDigitalU32(
                1, True, 10.0, DAQmx_Val_GroupByChannel, DO_data, written, None
            )
        return {}

    def get_output_tables(self, h5_file, device_name):
        """Return the AO and DO tables from the file, each None if it does not exist."""
        with h5py.File(h5_file, 'r') as hdf5_file:
            group = hdf5_file['devices'][device_name]
            try:
                AO_table = group['AO'][:]
            except KeyError:
                AO_table = None
            try:
                DO_table = group['DO'][:]
            except KeyError:
                DO_table = None
        return AO_table, DO_table

    def set_mirror_clock_terminal_connected(self, connected):
        """Connect or disconnect the clock terminal and its mirror, if there is one."""
        if self.clock_mirror_terminal is None:
            return
        if connected:
            DAQmxConnectTerms(
                self.clock_terminal,
                self.clock_mirror_terminal,
                DAQmx_Val_DoNotInvertPolarity,
            )
        else:
            DAQmxDisconnectTerms(self.clock_terminal, self.clock_mirror_terminal)

    def set_connected_terminals_connected(self, connected):
        """Connect or disconnect each of the connected_terminals pairs."""
        if self.connected_terminals is None:
            return
        if connected:
            for terminal_pair in self.connected_terminals:
                DAQmxConnectTerms(
                    terminal_pair[0],
                    terminal_pair[1],
                    DAQmx_Val_DoNotInvertPolarity,
                )
        else:
            for terminal_pair in self.connected_terminals:
                DAQmxDisconnectTerms(terminal_pair[0], terminal_pair[1])

    def program_buffered_DO(self, DO_table):
        """Create the DO task, program the DO table, and return the final values."""
        if DO_table is None:
            return {}
        self.DO_task = Task()
        written = int32()
        ports = DO_table.dtype.names

        final_values = {}
        for port_str in ports:
            con = f'{self.MAX_name}/{port_str}'
            self.DO_task.CreateDOChan(con, "", DAQmx_Val_ChanForAllLines)

            port_final_value = DO_table[port_str][-1]
            for line in range(self.ports[port_str]["num_lines"]):
                # Extract each digital value from the packed bits:
                line_final_value = bool((1 << line) & port_final_value)
                final_values[f'{port_str}/line{line}'] = int(line_final_value)

        # Convert DO table to a regular array and ensure it is C contiguous:
        DO_table = np.ascontiguousarray(
            structured_to_unstructured(DO_table, dtype=np.uint32)
        )

        # An all-zero DO table triggers a bug in NI-DAQmx that throws a cryptic error
        # for buffered output, so run that case as a non-buffered task.
        self.DO_all_zero = not np.any(DO_table)
        if self.DO_all_zero:
            DO_table = DO_table[0:1]

        if self.static_DO or self.DO_all_zero:
            # Static DO. Start the task and write data, no timing configuration.
            self.DO_task.StartTask()
            # Write data. See the comment in self.program_manual as to why we are using
            # uint32 instead of the native size of each port
            self.DO_task.WriteDigitalU32(
                1,  # npts
                False,  # autostart
                10.0,  # timeout
                DAQmx_Val_GroupByScanNumber,
                DO_table,
                written,
                None,
            )
        else:
            # Use all but the last sample, which is identical to the second last, to
            # ensure there is one more clock tick than there are samples: some devices
            # need that to determine that the task has completed.
            npts = len(DO_table) - 1

            self.DO_task.CfgSampClkTiming(
                self.clock_terminal,
                self.clock_limit,
                DAQmx_Val_Rising,
                DAQmx_Val_FiniteSamps,
                npts,
            )

            # Write data. See the comment in self.program_manual as to why we are using
            # uint32 instead of the native size of each port.
            self.DO_task.WriteDigitalU32(
                npts,
                False,  # autostart
                10.0,  # timeout
                DAQmx_Val_GroupByScanNumber,
                DO_table[:-1],
                written,
                None,
            )

            self.DO_task.StartTask()

        return final_values

    def program_buffered_AO(self, AO_table):
        """Create the AO task, program the AO table, and return the final values."""
        if AO_table is None:
            return {}
        self.AO_task = Task()
        written = int32()
        channels = ', '.join(self.MAX_name + '/' + c for c in AO_table.dtype.names)
        self.AO_task.CreateAOVoltageChan(
            channels, "", self.Vmin, self.Vmax, DAQmx_Val_Volts, None
        )

        final_values = dict(zip(AO_table.dtype.names, AO_table[-1]))

        # Convert AO table to a regular array and ensure it is C contiguous:
        AO_table = np.ascontiguousarray(
            structured_to_unstructured(AO_table, dtype=np.float64)
        )

        # An all-zero AO table triggers a bug in NI-DAQmx that throws a cryptic error
        # for buffered output, so run that case as a non-buffered task.
        self.AO_all_zero = not np.any(AO_table)
        if self.AO_all_zero:
            AO_table = AO_table[0:1]

        if self.static_AO or self.AO_all_zero:
            # Static AO. Start the task and write data, no timing configuration.
            self.AO_task.StartTask()
            self.AO_task.WriteAnalogF64(
                1, True, 10.0, DAQmx_Val_GroupByChannel, AO_table, written, None
            )
        else:
            # Use all but the last sample, which is identical to the second last, to
            # ensure there is one more clock tick than there are samples: some devices
            # need that to determine that the task has completed.
            npts = len(AO_table) - 1

            self.AO_task.CfgSampClkTiming(
                self.clock_terminal,
                self.clock_limit,
                DAQmx_Val_Rising,
                DAQmx_Val_FiniteSamps,
                npts,
            )

            self.AO_task.WriteAnalogF64(
                npts,
                False,  # autostart
                10.0,  # timeout
                DAQmx_Val_GroupByScanNumber,
                AO_table[:-1],
                written,
                None,
            )

            self.AO_task.StartTask()

        return final_values

    def transition_to_buffered(self, device_name, h5_file, front_panel_values, fresh):
        # Store the initial values in case we have to abort and restore them:
        self.initial_values = front_panel_values

        self.stop_tasks()

        AO_table, DO_table = self.get_output_tables(h5_file, device_name)

        self.set_mirror_clock_terminal_connected(True)
        self.set_connected_terminals_connected(True)

        DO_final_values = self.program_buffered_DO(DO_table)
        AO_final_values = self.program_buffered_AO(AO_table)

        final_values = {}
        final_values.update(DO_final_values)
        final_values.update(AO_final_values)

        # If we are the wait timeout device, then the final value of the timeout line
        # should be its rearm value:
        if self.wait_timeout_device == self.device_name:
            final_values[self.wait_timeout_connection] = self.wait_timeout_rearm_value

        return final_values

    def transition_to_manual(self):
        return self._return_to_manual(abort=False)

    def abort(self):
        return self._return_to_manual(abort=True)

    def _return_to_manual(self, abort):
        npts = uInt64()
        samples = uInt64()
        tasks = []
        if self.AO_task is not None:
            tasks.append([self.AO_task, self.static_AO or self.AO_all_zero, 'AO'])
            self.AO_task = None
        if self.DO_task is not None:
            tasks.append([self.DO_task, self.static_DO or self.DO_all_zero, 'DO'])
            self.DO_task = None

        # Only call StopTask if not aborting, as it results in an error if output was
        # incomplete. ClearTask is always called.
        for task, static, name in tasks:
            if not abort:
                if not static:
                    try:
                        # Wait for task completion with a 1 second timeout:
                        task.WaitUntilTaskDone(1)
                    finally:
                        # Log where we were up to in sample generation, regardless of
                        # whether the above succeeded:
                        task.GetWriteCurrWritePos(npts)
                        task.GetWriteTotalSampPerChanGenerated(samples)
                        # Detect -1 even though they're supposed to be unsigned ints, -1
                        # seems to indicate the task was not started:
                        current = samples.value if samples.value != 2 ** 64 - 1 else -1
                        total = npts.value if npts.value != 2 ** 64 - 1 else -1
                        msg = 'Stopping %s at sample %d of %d'
                        self.logger.info(msg, name, current, total)
                task.StopTask()
            task.ClearTask()

        self.set_mirror_clock_terminal_connected(False)
        self.set_connected_terminals_connected(False)

        self.start_manual_mode_tasks()
        if abort:
            self.program_manual(self.initial_values)

        return True

    def abort_transition_to_buffered(self):
        return self.abort()

    def abort_buffered(self):
        return self.abort()


class NI_DAQmxAcquisitionWorker(Worker):
    MAX_READ_INTERVAL = 0.2
    MAX_READ_PTS = 10000

    def init(self):
        # Prevent interference between the read callback and the shutdown code:
        self.tasklock = threading.RLock()

        # Assigned on a per-task basis and cleared afterward:
        self.read_array = None
        self.task = None

        # Assigned on a per-shot basis and cleared afterward:
        self.buffered_mode = False
        self.h5_file = None
        self.acquired_data = None
        self.buffered_rate = None
        self.buffered_chans = None

        # Manual mode acquires every analog input at a fixed 1000 samples per second:
        self.manual_mode_chans = self.AI_chans
        self.manual_mode_rate = 1000

        # An event for knowing when the wait durations are known, so that we may use
        # them to chunk up acquisition data:
        self.wait_durations_analysed = Event('wait_durations_analysed')

        self.start_task(self.manual_mode_chans, self.manual_mode_rate)

    def shutdown(self):
        if self.task is not None:
            self.stop_task()

    def read(self, task_handle, event_type, num_samples, callback_data=None):
        """DAQmx's every-N-samples callback: read the samples, keeping them if buffered."""
        samples_read = int32()
        with self.tasklock:
            if self.task is None or task_handle != self.task.taskHandle.value:
                # Task stopped already.
                return 0
            self.task.ReadAnalogF64(
                num_samples,
                -1,
                DAQmx_Val_GroupByScanNumber,
                self.read_array,
                self.read_array.size,
                samples_read,
                None,
            )
            # Select only the data read, and downconvert to 32 bit:
            data = self.read_array[: int(samples_read.value), :].astype(np.float32)
            if self.buffered_mode:
                self.acquired_data.append(data)
        return 0

    def start_task(self, chans, rate):
        """Start a task that calls read every MAX_READ_PTS samples or MAX_READ_INTERVAL
        seconds, whichever comes first, until stop_task is called."""

        if self.task is not None:
            raise RuntimeError('Task already running')

        if chans is None:
            return

        num_samples = min(self.MAX_READ_PTS, int(rate * self.MAX_READ_INTERVAL))

        self.read_array = np.zeros((num_samples, len(chans)), dtype=np.float64)
        self.task = Task()

        if self.AI_term == 'RSE':
            term = DAQmx_Val_RSE
        elif self.AI_term == 'NRSE':
            term = DAQmx_Val_NRSE
        elif self.AI_term == 'Diff':
            term = DAQmx_Val_Diff
        elif self.AI_term == 'PseudoDiff':
            term = DAQmx_Val_PseudoDiff

        for chan in chans:
            self.task.CreateAIVoltageChan(
                self.MAX_name + '/' + chan,
                "",
                term,
                self.AI_range[0],
                self.AI_range[1],
                DAQmx_Val_Volts,
                None,
            )

        if self.AI_timebase_terminal is None:
            # use internal default
            pass
        else:
            self.task.SetSampClkTimebaseSrc(self.AI_timebase_terminal)
            self.task.SetSampClkTimebaseRate(self.AI_timebase_rate)

        self.task.CfgSampClkTiming(
            "", rate, DAQmx_Val_Rising, DAQmx_Val_ContSamps, num_samples
        )
        if self.buffered_mode:
            self.task.CfgDigEdgeStartTrig(self.clock_terminal, DAQmx_Val_Rising)

        # This must not be garbage collected until the task is:
        self.task.callback_ptr = DAQmxEveryNSamplesEventCallbackPtr(self.read)

        self.task.RegisterEveryNSamplesEvent(
            DAQmx_Val_Acquired_Into_Buffer, num_samples, 0, self.task.callback_ptr, 100
        )

        self.task.StartTask()

    def stop_task(self):
        with self.tasklock:
            if self.task is None:
                raise RuntimeError('Task not running')
            self.read(self.task, None, -1)
            self.task.StopTask()
            self.task.ClearTask()
            self.task = None
            self.read_array = None

    def transition_to_buffered(self, device_name, h5_file, front_panel_values, fresh):
        self.logger.debug('transition_to_buffered')

        with h5py.File(h5_file, 'r') as f:
            group = f['/devices/' + device_name]
            if 'AI' not in group:
                return {}
            AI_table = group['AI'][:]
            device_properties = properties.get(f, device_name, 'device_properties')

        chans = [ensure_str(c) for c in AI_table['connection']]
        if chans:
            self.buffered_chans = sorted(set(chans), key=split_conn_AI)
        self.h5_file = h5_file
        self.buffered_rate = device_properties['acquisition_rate']
        if device_properties['start_delay_ticks']:
            # delay is defined in sample clock ticks, calculate in sec and save for later
            self.AI_start_delay = self.AI_start_delay_ticks/self.buffered_rate
        self.acquired_data = []
        # Stop the manual mode task and start the buffered mode task:
        self.stop_task()
        self.buffered_mode = True
        self.start_task(self.buffered_chans, self.buffered_rate)
        return {}

    def transition_to_manual(self):
        return self._return_to_manual(abort=False)

    def abort(self):
        return self._return_to_manual(abort=True)

    def _return_to_manual(self, abort):
        self.logger.debug('transition_to_manual')
        # Stop the buffered mode task and start the manual mode task, but only if in
        # buffered mode: abort() can be called when we are not, and a shot without
        # acquisitions never entered it.
        if not self.buffered_mode:
            return True
        if self.buffered_chans is not None:
            self.stop_task()
        self.buffered_mode = False
        self.logger.info('transitioning to manual mode, task stopped')
        self.start_task(self.manual_mode_chans, self.manual_mode_rate)

        if abort:
            self.acquired_data = None
            self.buffered_chans = None
            self.h5_file = None
            self.buffered_rate = None
            return True

        with h5py.File(self.h5_file, 'a') as hdf5_file:
            data_group = hdf5_file['data']
            data_group.create_group(self.device_name)
            waits_in_use = len(hdf5_file['waits']) > 0

        if self.buffered_chans is not None and not self.acquired_data:
            msg = """No data was acquired. Perhaps the acquisition task was not
                triggered to start: check that the device is connected to a
                pseudoclock."""
            raise RuntimeError(dedent(msg))
        # Concatenate our chunks of acquired data and recast them as a structured
        # array with channel names:
        if self.acquired_data:
            start_time = time.time()
            dtypes = [(chan, np.float32) for chan in self.buffered_chans]
            raw_data = np.concatenate(self.acquired_data).view(dtypes)
            raw_data = raw_data.reshape((len(raw_data),))
            self.acquired_data = None
            self.buffered_chans = None
            self.extract_measurements(raw_data, waits_in_use)
            self.h5_file = None
            self.buffered_rate = None
            msg = f'data written, time taken: {time.time() - start_time}s'
        else:
            msg = 'No acquisitions in this shot.'
        self.logger.info(msg)

        return True

    def extract_measurements(self, raw_data, waits_in_use):
        self.logger.debug('extract_measurements')
        if waits_in_use:
            # There were waits in this shot, so wait for the other process to determine
            # their durations. It posts within seconds of the shot's end; the deadline
            # only keeps a lost post from hanging BLACS.
            deadline = Deadline(self.device_name, 'hear the wait durations from the wait monitor', 30)
            with deadline.timeout_for(TimeoutError) as timeout:
                analysed = self.wait_durations_analysed.wait(self.h5_file, timeout=timeout)
            if analysed == 'failed':
                raise RuntimeError(
                    "The wait monitor failed, so the durations of the waits, which "
                    "divide up the acquisitions, are unknown. See the wait monitor "
                    "worker's error."
                )

        with h5py.File(self.h5_file, 'a') as hdf5_file:
            if waits_in_use:
                waits = hdf5_file['/data/waits']
                wait_times = waits['time']
                wait_durations = waits['duration']
            try:
                acquisitions = hdf5_file['/devices/' + self.device_name + '/AI']
            except KeyError:
                # No acquisitions!
                return
            try:
                measurements = hdf5_file['/data/traces']
            except KeyError:
                # Group doesn't exist yet, create it:
                measurements = hdf5_file.create_group('/data/traces')

            t0 = self.AI_start_delay
            for connection, label, t_start, t_end, _, _, _ in acquisitions:
                connection = ensure_str(connection)
                label = ensure_str(label)
                if waits_in_use:
                    # add durations from all waits that start prior to t_start of
                    # acquisition
                    t_start += wait_durations[(wait_times < t_start)].sum()
                    # compare wait times to t_end to allow for waits during an
                    # acquisition
                    t_end += wait_durations[(wait_times < t_end)].sum()
                i_start = int(np.ceil(self.buffered_rate * (t_start - t0)))
                i_end = int(np.floor(self.buffered_rate * (t_end - t0)))
                # np.ceil does what we want above, but float errors can miss the
                # equality:
                if t0 + (i_start - 1) / self.buffered_rate - t_start > -2e-16:
                    i_start -= 1
                # We want np.floor(x) to yield the largest integer < x (not <=):
                if t_end - t0 - i_end / self.buffered_rate < 2e-16:
                    i_end -= 1
                # IBS: t_end (with waits) sometimes lands after the end of the
                # acquisition, and then the slice below returns a shorter array than
                # expected, as i_end is past the end of the array.
                values = raw_data[connection][i_start : i_end + 1]
                i_end = i_start + len(values) - 1 # re-measure i_end

                t_i = t0 + i_start / self.buffered_rate
                t_f = t0 + i_end / self.buffered_rate
                times = np.linspace(t_i, t_f, len(values), endpoint=True)
                dtypes = [('t', np.float64), ('values', np.float32)]
                data = np.empty(len(values), dtype=dtypes)
                data['t'] = times
                data['values'] = values
                measurements.create_dataset(label, data=data)

    def abort_buffered(self):
        return self.abort()

    def abort_transition_to_buffered(self):
        return self.abort()

    def program_manual(self, front_panel_values):
        return {}


class NI_DAQmxWaitMonitorWorker(Worker):
    def init(self):
        self.all_waits_finished = Event('all_waits_finished', type='post')
        self.wait_durations_analysed = Event('wait_durations_analysed', type='post')
        self.wait_completed = Event('wait_completed', type='post')

        # Set on a per-shot basis and cleared afterward:
        self.h5_file = None
        self.CI_task = None
        self.DO_task = None
        self.wait_table = None
        self.semiperiods = None
        self.wait_monitor_thread = None

        # Saved error in case one occurs in the thread, we can raise it later in
        # transition_to_manual:
        self.wait_monitor_thread_exception = None
        # To trigger early shutdown of the wait monitor thread:
        self.shutting_down = False

        # Whether this device has "incomplete sample detection": if so, the first sample
        # on our semiperiod counter input task is automatically discarded before we see
        # it, otherwise we have to discard it ourselves
        self.incomplete_sample_detection = incomplete_sample_detection(self.MAX_name)

        if self.timeout_trigger_type == 'rising':
            trigger_value = 1
            rearm_value = 0
        elif self.timeout_trigger_type == 'falling':
            trigger_value = 0
            rearm_value = 1
        else:
            msg = (
                'timeout_trigger_type must be "rising" or "falling", '
                f'not "{self.timeout_trigger_type}". Set the timeout_trigger_type '
                'argument of the WaitMonitor to one of them.'
            )
            raise ValueError(msg)
        self.timeout_trigger = np.array([trigger_value], dtype=np.uint8)
        self.timeout_rearm = np.array([rearm_value], dtype=np.uint8)

    def shutdown(self):
        self.stop_tasks(True)

    def read_edges(self, npts, timeout=None):
        """Read npts semiperiods; return None if timeout seconds pass, keeping those read."""
        samples_read = int32()
        # Read in chunks of at most 0.2 s, until the timeout if there is one, so
        # that an abort is seen between them.
        end = None if timeout is None else time.monotonic() + timeout
        read_array = np.zeros(npts)
        read = len(self.partial_edges)
        read_array[:read] = self.partial_edges
        while True:
            if self.shutting_down:
                raise RuntimeError('Stopped before expected number of samples acquired')
            left = None if end is None else max(end - time.monotonic(), 0)
            try:
                self.CI_task.ReadCounterF64(
                    npts - read, 0.2 if left is None else min(left, 0.2),
                    read_array[read:], npts - read, samples_read, None
                )
            except SamplesNotYetAvailableError:
                # A read that times out still returns the samples it got
                read += samples_read.value
                if left is None or left > 0.2:
                    continue
                # A pulse that straddles the timeout keeps its first edge
                self.partial_edges = read_array[:read]
                return None
            self.partial_edges = read_array[:0]
            return read_array

    def wait_monitor(self):
        try:
            # Read the semiperiods of the pulses at the start of the experiment and
            # after every wait into self.semiperiods. If a wait times out, pulse the
            # timeout output to force a resume of the master pseudoclock.
            self.logger.debug('Wait monitor thread starting')
            with self.kill_lock:
                self.logger.debug('Waiting for start of experiment')
                # Wait for the pulse indicating the start of the experiment:
                if self.incomplete_sample_detection:
                    semiperiods = self.read_edges(1, timeout=None)
                else:
                    semiperiods = self.read_edges(2, timeout=None)
                self.logger.debug('Experiment started, got edges:' + str(semiperiods))
                # The last semiperiod is the initial pulse's width, which timeout pulses
                # reuse. current_time is labscript time: after each wait it is reset to
                # that wait's time plus the width of the pulse after it.
                current_time = pulse_width = semiperiods[-1]
                self.semiperiods.append(semiperiods[-1])
                for wait in self.wait_table:
                    # How long until when the next wait should timeout?
                    timeout = wait['time'] + wait['timeout'] - current_time
                    timeout = max(timeout, 0)
                    self.logger.debug('Waiting for pulse indicating end of wait')
                    semiperiods = self.read_edges(2, timeout)
                    # Did the wait finish of its own accord, or time out?
                    if semiperiods is None:
                        # It timed out. If there is a timeout device, send a trigger to
                        # resume the clock!
                        if self.DO_task is not None:
                            msg = f"""Wait timed out; retriggering clock with
                                {pulse_width:.3e} s pulse ({self.timeout_trigger_type}
                                edge)"""
                            self.logger.debug(dedent(msg))
                            self.send_resume_trigger(pulse_width)
                        else:
                            msg = """Specified wait timeout exceeded, but there is no
                                timeout device with which to resume the experiment.
                                Continuing to wait."""
                            self.logger.warning(dedent(msg))
                        # Keep waiting for the clock to resume:
                        self.logger.debug('Waiting for pulse indicating end of wait')
                        semiperiods = self.read_edges(2, timeout=None)
                    self.semiperiods.extend(semiperiods)
                    self.logger.debug('Wait completed')
                    current_time = wait['time'] + semiperiods[-1]
                    postdata = ensure_str(wait['label'])
                    self.wait_completed.post(self.h5_file, data=postdata)
                self.logger.debug('All waits finished')
                self.all_waits_finished.post(self.h5_file)
        except Exception:
            self.logger.exception('Exception in wait monitor thread:')
            # Save the exception so it can be raised in transition_to_manual
            self.wait_monitor_thread_exception = sys.exc_info()

    def send_resume_trigger(self, pulse_width):
        written = int32()
        self.DO_task.WriteDigitalLines(
            1, True, 1, DAQmx_Val_GroupByChannel, self.timeout_trigger, written, None
        )
        # Hold the trigger as long as we observed the first pulse of the experiment to
        # last. In practice this is likely to be negligible compared to the other
        # software delays here, but in case it is larger we'd better wait:
        time.sleep(pulse_width)
        self.DO_task.WriteDigitalLines(
            1, True, 1, DAQmx_Val_GroupByChannel, self.timeout_rearm, written, None
        )

    def stop_tasks(self, abort):
        self.logger.debug('stop_tasks')
        if self.wait_monitor_thread is not None:
            if abort:
                # This will cause the wait_monitor thread to raise an exception within a
                # short time, allowing us to join it before it would otherwise be done.
                self.shutting_down = True
            # The tasks stop after the shot, so an edge not seen by now will not
            # come: give the thread a second for the last ones, then stop it.
            self.wait_monitor_thread.join(1)
            self.shutting_down = True
            # It reads in chunks of 0.2 s, so sees shutting_down within one chunk
            Deadline(self.device_name, 'stop its wait monitor thread', 2).wait(
                lambda: not self.wait_monitor_thread.is_alive()
            )
            self.wait_monitor_thread = None
            self.shutting_down = False
            if not abort and self.wait_monitor_thread_exception is not None:
                # Raise any unexpected errors from the wait monitor thread:
                _reraise(self.wait_monitor_thread_exception)
            self.wait_monitor_thread_exception = None
            if not abort:
                # Don't want errors about incomplete task to be raised if we are aborting:
                self.CI_task.StopTask()
            if self.DO_task is not None:
                self.DO_task.StopTask()
        if self.CI_task is not None:
            self.CI_task.ClearTask()
            self.CI_task = None
        if self.DO_task is not None:
            self.DO_task.ClearTask()
            self.DO_task = None
        self.logger.debug('finished stop_tasks')

    def start_tasks(self):
        self.CI_task = Task()
        CI_chan = self.MAX_name + '/' + self.wait_acq_connection
        # The longest measurement is the labscript time from the start or the previous
        # wait to a wait, plus that wait's timeout:
        interwait_times = np.diff([0] + list(self.wait_table['time']))
        max_measure_time = max(interwait_times + self.wait_table['timeout'])
        # Allow for software delays in timeouts.
        max_measure_time += 1.0
        min_measure_time = self.min_semiperiod_measurement
        self.logger.debug(
            "CI measurement range is: min: %f max: %f",
            min_measure_time,
            max_measure_time,
        )
        self.CI_task.CreateCISemiPeriodChan(
            CI_chan, '', min_measure_time, max_measure_time, DAQmx_Val_Seconds, ""
        )
        num_edges = 2 * (len(self.wait_table) + 1)
        self.CI_task.CfgImplicitTiming(DAQmx_Val_ContSamps, num_edges)
        self.CI_task.StartTask()

        # The timeout task:
        if self.wait_timeout_MAX_name is not None:
            self.DO_task = Task()
            DO_chan = self.wait_timeout_MAX_name + '/' + self.wait_timeout_connection
            self.DO_task.CreateDOChan(DO_chan, "", DAQmx_Val_ChanForAllLines)
            # Ensure timeout trigger is armed:
            written = int32()
            # Writing autostarts the task:
            self.DO_task.WriteDigitalLines(
                1, True, 1, DAQmx_Val_GroupByChannel, self.timeout_rearm, written, None
            )

    def transition_to_buffered(self, device_name, h5_file, front_panel_values, fresh):
        self.logger.debug('transition_to_buffered')
        self.h5_file = h5_file
        with h5py.File(h5_file, 'r') as hdf5_file:
            dataset = hdf5_file['waits']
            if len(dataset) == 0:
                self.logger.debug('There are no waits, not transitioning to buffered')
                self.wait_table = None
                return {}
            self.wait_table = dataset[:]

        self.start_tasks()

        # semiperiods collects the counter's results. partial_edges holds what a
        # timed-out read got, for the next read:
        self.semiperiods = []
        self.partial_edges = np.zeros(0)
        self.wait_monitor_thread = threading.Thread(target=self.wait_monitor)
        # Not a daemon thread, as it implements wait timeouts - we need it to stay alive
        # if other things die.
        self.wait_monitor_thread.start()
        self.logger.debug('finished transition to buffered')

        return {}

    def transition_to_manual(self):
        return self._return_to_manual(abort=False)

    def abort(self):
        return self._return_to_manual(abort=True)

    def _return_to_manual(self, abort):
        self.logger.debug('transition_to_manual')
        try:
            self.stop_tasks(abort)
            if not abort and self.wait_table is not None:
                # Work out how long the waits were. The absolute times of each edge on
                # the wait monitor are:
                edge_times = np.cumsum(self.semiperiods)
                # There was also a rising edge at t=0 that we didn't measure:
                edge_times = np.insert(edge_times, 0, 0)
                # The even-indexed edges are rising edges:
                rising_edge_times = edge_times[::2]
                # The times between rising edges:
                periods = np.diff(rising_edge_times)
                # Compared to how long we expected between the start of the experiment
                # and the first wait, and between each pair of waits, the difference is
                # the waits' durations.
                resume_times = self.wait_table['time']
                # Again, include the start of the experiment, t=0:
                resume_times = np.insert(resume_times, 0, 0)
                run_periods = np.diff(resume_times)
                wait_durations = periods - run_periods
                waits_timed_out = wait_durations > self.wait_table['timeout']

                # Save the durations, then post an event saying so:
                dtypes = [
                    ('label', 'S256'),
                    ('time', float),
                    ('timeout', float),
                    ('duration', float),
                    ('timed_out', bool),
                ]
                data = np.empty(len(self.wait_table), dtype=dtypes)
                data['label'] = self.wait_table['label']
                data['time'] = self.wait_table['time']
                data['timeout'] = self.wait_table['timeout']
                data['duration'] = wait_durations
                data['timed_out'] = waits_timed_out
                with h5py.File(self.h5_file, 'a') as hdf5_file:
                    hdf5_file.create_dataset('/data/waits', data=data)
                self.wait_durations_analysed.post(self.h5_file)
        except Exception:
            # An acquisition worker waits for the wait durations: tell it none will come
            if not abort and self.wait_table is not None:
                self.wait_durations_analysed.post(self.h5_file, data='failed')
            raise

        self.h5_file = None
        self.semiperiods = None
        return True

    def abort_buffered(self):
        return self.abort()

    def abort_transition_to_buffered(self):
        return self.abort()

    def program_manual(self, front_panel_values):
        return {}
