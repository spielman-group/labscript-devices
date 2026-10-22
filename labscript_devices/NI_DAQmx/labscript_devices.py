#####################################################################
#                                                                   #
# /NI_DAQmx/labscript_devices.py                                    #
#                                                                   #
# Copyright 2018, Monash University, JQI, Christopher Billington    #
#                                                                   #
# This file is part of the module labscript_devices, in the         #
# labscript suite (see http://labscriptsuite.org), and is           #
# licensed under the Simplified BSD License. See the license.txt    #
# file in the root of the project for the full license.             #
#                                                                   #
#####################################################################

__version__ = '1.2.0'


from labscript import (
    IntermediateDevice,
    AnalogOut,
    DigitalOut,
    StaticAnalogOut,
    StaticDigitalOut,
    AnalogIn,
    bitfield,
    compiler,
    LabscriptError,
    set_passed_properties,
)
from labscript_utils import dedent
from .utils import split_conn_DO, split_conn_AO, split_conn_AI
import numpy as np
import warnings

_ints = {8: np.uint8, 16: np.uint16, 32: np.uint32, 64: np.uint64}


def _smallest_int_type(n):
    """Return the smallest unsigned integer type that holds n bits."""
    return _ints[min(size for size in _ints.keys() if size >= n)]


class NI_DAQmx(IntermediateDevice):
    """A National Instruments DAQ with analog and digital outputs and analog inputs."""

    # Will be overridden during __init__ depending on configuration:
    allowed_children = []

    description = 'NI-DAQmx'

    # If used as a wait monitor, this device's BLACS worker supports posting events in
    # software indicating the completion of each wait as it occurs:
    wait_monitor_supports_wait_completed_events = True

    @set_passed_properties(
        property_names={
            "connection_table_properties": [
                "clock_terminal",
                "MAX_name",
                "static_AO",
                "static_DO",
                "clock_mirror_terminal",
                "connected_terminals",
                "AI_range",
                "AI_start_delay",
                "AI_start_delay_ticks",
                "AI_term",
                "AI_chans",
                "AI_timebase_terminal",
                "AI_timebase_rate",
                "AO_range",
                "max_AI_multi_chan_rate",
                "max_AI_single_chan_rate",
                "max_AO_sample_rate",
                "max_DO_sample_rate",
                "min_semiperiod_measurement",
                "num_AI",
                "num_AO",
                "num_CI",
                "ports",
                "supports_buffered_AO",
                "supports_buffered_DO",
                "supports_semiperiod_measurement",
                "supports_simultaneous_AI_sampling",
                "clock_limit",
                "wait_monitor_minimum_pulse_width",
                "wait_monitor_supports_wait_completed_events",
            ],
            "device_properties": ["acquisition_rate","start_delay_ticks"],
        }
    )
    def __init__(
        self,
        name,
        parent_device=None,
        clock_terminal=None,
        MAX_name=None,
        static_AO=None,
        static_DO=None,
        clock_mirror_terminal=None,
        connected_terminals=None,
        acquisition_rate=None,
        AI_range=None,
        AI_range_Diff=None,
        AI_start_delay=0,
        AI_start_delay_ticks=None,
        AI_term='RSE',
        AI_term_cfg=None,
        AI_timebase_terminal=None,
        AI_timebase_rate=None,
        AO_range=None,
        max_AI_multi_chan_rate=None,
        max_AI_single_chan_rate=None,
        max_AO_sample_rate=None,
        max_DO_sample_rate=None,
        min_semiperiod_measurement=None,
        num_AI=0,
        num_AO=0,
        num_CI=0,
        ports=None,
        supports_buffered_AO=False,
        supports_buffered_DO=False,
        supports_semiperiod_measurement=False,
        supports_simultaneous_AI_sampling=False,
        **kwargs
    ):
        """
        A model subclass, such as ``NI_PCIe_6363``, takes the same keywords and
        supplies those that describe the hardware (ranges, rates, channel counts,
        ports and supported features) from its model's introspected capabilities;
        a keyword given to it replaces the capability.

        Parameters
        ----------
        name : str
            Python variable name of the device.
        parent_device : :class:`~labscript.ClockLine`, optional
            Clockline that clocks the buffered outputs and triggers the start of the
            analog input acquisitions; ``None`` by default. It can be left out only if
            `static_AO` and `static_DO` are both true, and no analog input can be
            added without it.
        clock_terminal : str, optional
            Terminal of the device that the clockline is connected to, such as
            ``'/daq/PFI0'`` for a device named ``daq`` in NI MAX. Required whenever
            `parent_device` is given.
        MAX_name : str, optional
            Name of the device in NI MAX; `name` by default.
        static_AO, static_DO : bool, optional
            Whether the analog and digital outputs are static. Static outputs take
            ``StaticAnalogOut`` or ``StaticDigitalOut`` children, each with one value
            for the whole shot; buffered outputs take ``AnalogOut`` or ``DigitalOut``
            children and are clocked. The default is ``not supports_buffered_AO`` for
            `static_AO` and ``not supports_buffered_DO`` for `static_DO`. A device that
            supports neither kind of buffered output needs both true.
        clock_mirror_terminal : str, optional
            Terminal of a digital output that mirrors the clock input: during a shot,
            BLACS connects `clock_terminal` to it. For daisy-chaining DAQs on the same
            clockline. ``None`` by default.
        connected_terminals : list of tuple of str, optional
            Pairs of terminals, a digital input and a digital output, that BLACS
            connects during a shot. For daisy-chaining DAQs on the same clockline when
            they have no direct route (see Device Routes in NI MAX). ``None`` by
            default.
        acquisition_rate : float, optional
            Sample rate of the analog inputs in a shot, in samples per second per
            channel; ``None`` by default, which allows no analog input. It cannot be
            set if `num_AI` is 0, and cannot exceed `max_AI_single_chan_rate`. When
            several channels are acquired, it is also limited by
            `max_AI_multi_chan_rate`, which the channels share unless
            `supports_simultaneous_AI_sampling`.
        AI_range : list of float, optional
            ``[Vmin, Vmax]``, in volts, for all analog inputs; ``None`` by default.
            If `AI_term` is ``'Diff'``, `AI_range_Diff` is used instead.
        AI_range_Diff : list of float, optional
            ``[Vmin, Vmax]``, in volts, for all analog inputs when `AI_term` is
            ``'Diff'``; ``None`` by default.
        AI_start_delay : float or None, optional
            Time in seconds between the start of an analog input task and its first
            sample; 0 by default. ``None`` takes the delay from
            `AI_start_delay_ticks`.
        AI_start_delay_ticks : int, optional
            Time in sample clock periods between the start of an analog input task and
            its first sample, which is necessary for DAQs that employ delta ADCs. Used,
            and then required, only if `AI_start_delay` is ``None``; ``None`` by
            default.
        AI_term : str, optional
            Termination of all analog inputs: ``'RSE'`` (the default), ``'NRSE'``,
            ``'Diff'`` or ``'PseudoDiff'``. Only the channels that `AI_term_cfg` lists
            as supporting it can be used, and none supporting it raises
            :class:`~labscript.LabscriptError`.
        AI_term_cfg : dict, optional
            The terminations each analog input supports, such as
            ``{'ai0': ['RSE', 'NRSE', 'Diff'], 'ai1': ['RSE', 'NRSE']}``; best
            introspected with ``get_capabilities.py``. ``None`` by default, which takes
            every channel to support only ``'RSE'`` and warns that the model
            specification needs updating.
        AI_timebase_terminal : str, optional
            Terminal, generally a PFI line, of the external signal used as the Sample
            Clock Timebase of the analog inputs; ``None`` by default, which uses the
            internal timebase. Give it with `AI_timebase_rate`, or neither.
        AI_timebase_rate : float, optional
            Frequency of the signal on `AI_timebase_terminal`; ``None`` by default.
        AO_range : list of float, optional
            ``[Vmin, Vmax]``, in volts, for all analog outputs; ``None`` by default.
            Needed if the device has analog outputs. A value outside it by more than
            1e-10 of the range raises :class:`~labscript.LabscriptError` when the shot
            compiles, and a smaller excess is clipped.
        max_AI_multi_chan_rate : float, optional
            Highest analog input sample rate, in samples per second, with more than
            one channel in use; the channels share it unless
            `supports_simultaneous_AI_sampling`.
        max_AI_single_chan_rate : float, optional
            Highest analog input sample rate, in samples per second, with one channel
            in use; `acquisition_rate` cannot exceed it.
        max_AO_sample_rate, max_DO_sample_rate : float, optional
            Highest sample rate, in samples per second, of buffered analog and digital
            output. The device's ``clock_limit`` is the lower of the two for the kinds
            of output that support buffering.
        min_semiperiod_measurement : float, optional
            Shortest semiperiod, in seconds, the device can measure. If the device is
            the acquisition device of the wait monitor, trigger pulses are at least
            this long.
        num_AI, num_AO, num_CI : int, optional
            Number of analog input, analog output and counter input channels; 0 by
            default. BLACS can use the device as the acquisition device of the wait
            monitor only if `num_CI` is not 0.
        ports : dict, optional
            The digital ports, as ``{'port0': {'num_lines': 32, 'supports_buffered':
            True}, 'port1': ...}``, keyed ``'port<N>'`` from 0 with none missing. Each
            gives the port's number of lines and whether it supports buffered output,
            which a ``DigitalOut`` needs. Empty by default.
        supports_buffered_AO, supports_buffered_DO : bool, optional
            Whether the analog and digital outputs can be clocked; ``False`` by
            default. They set the defaults of `static_AO` and `static_DO` and the
            device's ``clock_limit``.
        supports_semiperiod_measurement : bool, optional
            Whether the device can make semiperiod measurements; ``False`` by default.
            Saved in the connection table, where nothing reads it.
        supports_simultaneous_AI_sampling : bool, optional
            Whether the device samples its analog inputs simultaneously; ``False`` by
            default. If so, `max_AI_multi_chan_rate` applies to each channel rather
            than being shared.
        **kwargs
            Passed to :class:`~labscript.IntermediateDevice`, which passes them on to
            :class:`~labscript.Device`, for example `start_order` and `stop_order`.
        """

        if static_AO is None:
            static_AO = not supports_buffered_AO
        if static_DO is None:
            static_DO = not supports_buffered_DO
        if not static_AO and not supports_buffered_AO:
            msg = f"""{name} does not support buffered analog output. Instantiate it
                with static_AO=True."""
            raise LabscriptError(dedent(msg))
        if not static_DO and not supports_buffered_DO:
            msg = f"""{name} does not support buffered digital output. Instantiate it
                with static_DO=True."""
            raise LabscriptError(dedent(msg))

        if parent_device is None and not (static_DO and static_AO):
            msg = f"""{name} needs a parent clockline unless static_AO and static_DO are
                both True. Pass parent_device, or make both outputs static."""
            raise LabscriptError(dedent(msg))
        if parent_device is not None and clock_terminal is None:
            msg = f"""{name} has a parent_device, so it needs a clock_terminal: the
                terminal the parent clockline is connected to."""
            raise ValueError(dedent(msg))
        if acquisition_rate is not None and num_AI == 0:
            msg = f"{name} has no analog inputs, so acquisition_rate cannot be set."
            raise ValueError(msg)
        if acquisition_rate is not None and acquisition_rate > max_AI_single_chan_rate:
            msg = f"""acquisition_rate {acquisition_rate} is larger than the maximum
                single-channel rate {max_AI_single_chan_rate} of {name}. Lower
                acquisition_rate."""
            raise ValueError(dedent(msg))

        self.clock_terminal = clock_terminal
        self.MAX_name = MAX_name if MAX_name is not None else name
        self.static_AO = static_AO
        self.static_DO = static_DO

        self.acquisition_rate = acquisition_rate
        self.AO_range = AO_range
        self.max_AI_multi_chan_rate = max_AI_multi_chan_rate
        self.max_AI_single_chan_rate = max_AI_single_chan_rate
        self.max_AO_sample_rate = max_AO_sample_rate
        self.max_DO_sample_rate = max_DO_sample_rate
        self.min_semiperiod_measurement = min_semiperiod_measurement
        self.num_AI = num_AI
        self.AI_term = AI_term
        if num_AI > 0:
            if AI_term_cfg == None:
                # A model specification without AI_term_cfg is a legacy one: every
                # channel is taken to support only 'RSE'.
                AI_term_cfg = {f'ai{i:d}': ['RSE'] for i in range(num_AI)}
                msg = f"""Model specifications for {self.description} need to be updated.
                    Please run the `get_capabilities.py` and `generate_subclasses.py`
                    scripts or define the `AI_term_cfg` kwarg for your device.
                    """
                warnings.warn(dedent(msg), FutureWarning)
            self.AI_chans = [key for key,val in AI_term_cfg.items() if self.AI_term in val]
            if not len(self.AI_chans):
                msg = f"""None of the analog inputs of {name} ({self.description})
                    supports AI_term {AI_term!r}. Pass an AI_term that its AI_term_cfg
                    lists."""
                raise LabscriptError(dedent(msg))
            if AI_term == 'Diff':
                self.AI_range = AI_range_Diff
            if AI_start_delay is None:
                if AI_start_delay_ticks is not None:
                    # Tell blacs_worker to use AI_start_delay_ticks to define delay
                    self.start_delay_ticks = True
                else:
                    raise LabscriptError(
                        f"{name} has AI_start_delay=None but no AI_start_delay_ticks. "
                        "Give the delay in seconds as AI_start_delay or in sample "
                        "clock periods as AI_start_delay_ticks."
                    )
            else:
                # Tells blacs_worker to use AI_start_delay to define delay
                self.start_delay_ticks = False
        else:
            self.AI_chans = []
            self.start_delay_ticks = None
        if num_AI > 0:
            if (AI_timebase_rate is None) ^ (AI_timebase_terminal is None):
                raise LabscriptError(
                    f"{name} needs both AI_timebase_terminal and AI_timebase_rate to "
                    "use an external AI timebase. Give both, or neither for the "
                    "internal timebase."
                )
            self.AI_timebase_terminal = AI_timebase_terminal

        self.num_AO = num_AO
        self.num_CI = num_CI
        self.ports = ports if ports is not None else {}
        self.supports_buffered_AO = supports_buffered_AO
        self.supports_buffered_DO = supports_buffered_DO
        self.supports_semiperiod_measurement = supports_semiperiod_measurement
        self.supports_simultaneous_AI_sampling = supports_simultaneous_AI_sampling

        if self.supports_buffered_DO and self.supports_buffered_AO:
            self.clock_limit = min(self.max_DO_sample_rate, self.max_AO_sample_rate)
        elif self.supports_buffered_DO:
            self.clock_limit = self.max_DO_sample_rate
        elif self.supports_buffered_AO:
            self.clock_limit = self.max_AO_sample_rate
        else:
            self.clock_limit = None

        self.wait_monitor_minimum_pulse_width = self.min_semiperiod_measurement

        self.allowed_children = []
        if self.num_AI > 0:
            self.allowed_children += [AnalogIn]
        if self.num_AO > 0 and static_AO:
            self.allowed_children += [StaticAnalogOut]
        if self.num_AO > 0 and not static_AO:
            self.allowed_children += [AnalogOut]
        if self.ports and static_DO:
            self.allowed_children += [StaticDigitalOut]
        if self.ports and not static_DO:
            self.allowed_children += [DigitalOut]

        self.BLACS_connection = self.MAX_name

        # Called late: the parent clockline reads clock_limit when this device joins it.
        IntermediateDevice.__init__(self, name, parent_device, **kwargs)

        # Cannot be set with set_passed_properties because of name mangling with the
        # initial double underscore:
        self.set_property('__version__', __version__, 'connection_table_properties')

    def add_device(self, device):
        """Check a child's kind and connection against this device's configuration."""
        if isinstance(device, StaticAnalogOut) and not self.static_AO:
            msg = f"""Cannot add the StaticAnalogOut {device.name} to {self.name}, which
                is configured for dynamic analog output. Pass static_AO=True to
                {self.name} for static analog output."""
            raise LabscriptError(dedent(msg))
        if isinstance(device, StaticDigitalOut) and not self.static_DO:
            msg = f"""Cannot add the StaticDigitalOut {device.name} to {self.name}, which
                is configured for dynamic digital output. Pass static_DO=True to
                {self.name} for static digital output."""
            raise LabscriptError(dedent(msg))
        if isinstance(device, AnalogOut) and self.static_AO:
            msg = f"""Cannot add the AnalogOut {device.name} to {self.name}, which is
                configured for static analog output. Use a StaticAnalogOut, or, if the
                device supports buffered analog output, pass static_AO=False to it."""
            raise LabscriptError(dedent(msg))
        if isinstance(device, DigitalOut) and self.static_DO:
            msg = f"""Cannot add the DigitalOut {device.name} to {self.name}, which is
                configured for static digital output. Use a StaticDigitalOut, or, if
                the port supports buffered output, pass static_DO=False to the device."""
            raise LabscriptError(dedent(msg))
        if isinstance(device, (AnalogOut, StaticAnalogOut)):
            ao_num = split_conn_AO(device.connection)
            if ao_num >= self.num_AO:
                msg = f"""Cannot add output with connection string '{device.connection}'
                    to {self.name}, which has num_AO={self.num_AO}."""
                raise ValueError(dedent(msg))
        elif isinstance(device, (DigitalOut, StaticDigitalOut)):
            port, line = split_conn_DO(device.connection)
            port_str = f'port{port}'
            if port_str not in self.ports:
                msg = f"{self.name} has no digital output port '{port_str}'."
                raise ValueError(msg)
            nlines = self.ports[port_str]['num_lines']
            if line >= nlines:
                msg = f"""Cannot add output with connection string
                    '{device.connection}' to port '{port_str}' of {self.name}, which
                    has only {nlines} lines."""
                raise ValueError(dedent(msg))
            supports_buffered = self.ports[port_str]['supports_buffered']
            if isinstance(device, DigitalOut) and not supports_buffered:
                msg = f"""Cannot add the DigitalOut {device.name} to port '{port_str}'
                    of {self.name}, which does not support buffered output. Use a
                    buffered port, or a StaticDigitalOut with static_DO=True."""
                raise ValueError(dedent(msg))
        elif isinstance(device, AnalogIn):
            if device.connection not in self.AI_chans:
                msg = f"""Cannot add analog input with connection string
                    '{device.connection}' to {self.name}: it is not one of the analog
                    inputs (num_AI={self.num_AI}) that support AI_term {self.AI_term!r}."""
                raise ValueError(dedent(msg))
            if self.acquisition_rate is None:
                msg = f"""Cannot add the analog input {device.name} to {self.name},
                    which has acquisition_rate=None. Pass acquisition_rate to
                    {self.name}."""
                raise ValueError(dedent(msg))
            if self.parent_device is None:
                msg = f"""Cannot add the analog input {device.name} to {self.name},
                    which has no parent clockline. Even if there is no buffered output,
                    a pseudoclock is still required to trigger the start of
                    acquisition. Pass parent_device and clock_terminal to
                    {self.name}."""
                raise ValueError(dedent(msg))

        IntermediateDevice.add_device(self, device)

    def _check_even_children(self, analogs, digitals):
        """Check that there are an even number of children of each type."""
        errmsg = """{0} {1} must have an even number of {2}s in order to guarantee an
            even total number of samples, which is a limitation of the DAQmx library.
            Add a dummy {2} device or remove one you are not using, so that there is an
            even number."""
        if len(analogs) % 2:
            msg = errmsg.format(self.description, self.name, 'analog output')
            raise LabscriptError(dedent(msg))
        if len(digitals) % 2:
            msg = errmsg.format(self.description, self.name, 'digital output')
            raise LabscriptError(dedent(msg))

    def _check_bounds(self, analogs):
        """Check that all analog outputs are in bounds."""
        if not analogs:
            return
        vmin, vmax = self.AO_range
        # Rounding can leave a value that is mathematically in bounds just outside them.
        # One out by at most 1e-10 of the range (over 32 bits of precision, beyond any
        # of the DACs) is clipped into bounds rather than refused.
        eps = abs(vmax - vmin) * 1e-10
        for output in analogs.values():
            if any((output.raw_output < vmin - eps) | (output.raw_output > vmax + eps)):
                msg = f"""{output.description} {output.name} can only have values
                    between {vmin:g} and {vmax:g} Volts, the AO_range of {self.name}."""
                raise LabscriptError(dedent(msg))
            np.clip(output.raw_output, vmin, vmax, out=output.raw_output)

    def _check_AI_not_too_fast(self, AI_table):
        """Check that analog input acquisition rates do not exceed maximums."""
        if AI_table is None:
            return
        n = len(set(AI_table['connection']))
        if n < 2:
            # Either no AI in use, or already checked against single channel rate in
            # __init__.
            return
        if self.supports_simultaneous_AI_sampling and self.acquisition_rate <= self.max_AI_multi_chan_rate:
            return
        elif self.acquisition_rate <= self.max_AI_multi_chan_rate / n:
            return
        msg = f"""acquisition_rate {self.acquisition_rate} of {self.name} is too fast for
            the {n} analog input channels in use. The device's multi-channel rate is
            {self.max_AI_multi_chan_rate}, which the channels share unless it samples
            them simultaneously. Lower acquisition_rate or acquire from fewer
            channels."""
        raise ValueError(dedent(msg))

    def _make_analog_out_table(self, analogs, times):
        """Collect analog output data and create the output array."""
        if not analogs:
            return None
        n_timepoints = 1 if self.static_AO else len(times)
        connections = sorted(analogs, key=split_conn_AO)
        dtypes = [(c, np.float32) for c in connections]
        analog_out_table = np.empty(n_timepoints, dtype=dtypes)
        for connection, output in analogs.items():
            analog_out_table[connection] = output.raw_output
        return analog_out_table

    def _make_digital_out_table(self, digitals, times):
        """Collect digital output data and create the output array."""
        if not digitals:
            return None
        n_timepoints = 1 if self.static_DO else len(times)
        # List of output bits by port number:
        bits_by_port = {}
        # table names and dtypes by port number:
        columns = {}
        for connection, output in digitals.items():
            port, line = split_conn_DO(connection)
            port_str = f'port{port}'
            if port not in bits_by_port:
                # One bit per line, padded to the width of the smallest unsigned
                # integer type that holds the port.
                nlines = self.ports[port_str]["num_lines"]
                int_type = _smallest_int_type(nlines)
                int_type_nbits = 8 * int_type().nbytes
                columns[port] = (port_str, int_type)
                bits_by_port[port] = [0] * int_type_nbits
            bits_by_port[port][line] = output.raw_output
        dtypes = [columns[port] for port in sorted(columns)]
        digital_out_table = np.empty(n_timepoints, dtype=dtypes)
        for port, bits in bits_by_port.items():
            # Pack the bits from each port into an integer:
            port_str, dtype = columns[port]
            values = bitfield(bits, dtype=dtype)
            digital_out_table[port_str] = np.array(values)
        return digital_out_table

    def _make_analog_input_table(self, inputs):
        """Collect analog input instructions and create the acquisition table."""
        if not inputs:
            return None
        acquisitions = []
        for connection, input in inputs.items():
            for acq in input.acquisitions:
                acquisitions.append(
                    (
                        connection,
                        acq['label'],
                        acq['start_time'],
                        acq['end_time'],
                        acq['wait_label'],
                        acq['scale_factor'],
                        acq['units'],
                    )
                )
        if acquisitions and compiler.wait_table and compiler.wait_monitor is None:
            msg = f"""Cannot do analog input on {self.name} in an experiment that uses
                waits without a wait monitor. Input data cannot be 'chunked' into the
                requested segments without knowing the durations of the waits. Add a
                labscript.WaitMonitor to the experiment."""
            raise LabscriptError(dedent(msg))

        # 'S256' limits the string fields to 256 characters; dtype=str, with no length,
        # makes the strings all come out empty. 'S' strings are bytes, the same on disk
        # as the 'a' alias numpy 2.0 removed, so earlier shot files still read.
        acquisitions_table_dtypes = [
            ('connection', 'S256'),
            ('label', 'S256'),
            ('start', float),
            ('stop', float),
            ('wait label', 'S256'),
            ('scale factor', float),
            ('units', 'S256'),
        ]
        acquisition_table = np.empty(len(acquisitions), dtype=acquisitions_table_dtypes)
        for i, acq in enumerate(acquisitions):
            acquisition_table[i] = acq

        return acquisition_table

    def _check_wait_monitor_timeout_device_config(self):
        """Check the type and order of a wait monitor timeout device other than this."""
        if compiler.wait_monitor is None:
            return
        acquisition_device = compiler.wait_monitor.acquisition_device
        timeout_device = compiler.wait_monitor.timeout_device
        if acquisition_device is not self or timeout_device is None:
            return
        if timeout_device is self:
            return
        if not isinstance(timeout_device, NI_DAQmx):
            msg = f"""If using an NI DAQmx device as a wait monitor acquisition device,
                then the wait monitor timeout device must also be an NI DAQmx device,
                not {type(timeout_device).__name__}."""
            raise TypeError(dedent(msg))
        timeout_start = timeout_device.start_order
        if timeout_start is None:
            timeout_start = 0
        timeout_stop = timeout_device.stop_order
        if timeout_stop is None:
            timeout_stop = 0
        self_start = self.start_order
        if self_start is None:
            self_start = 0
        self_stop = self.stop_order
        if self_stop is None:
            self_stop = 0
        if timeout_start >= self_start or timeout_stop <= self_stop:
            msg = """If using different DAQmx devices as the wait monitor acquisition
                and timeout devices, the timeout device must transition_to_buffered
                before the acquisition device, and transition_to_manual after it, in
                order to ensure the output port for timeout pulses is not in use (by the
                manual mode DO task) when the wait monitor subprocess attempts to use
                it. To achieve this, pass the start_order and stop_order keyword
                arguments to the devices in your connection table, ensuring that the
                timeout device has a lower start_order and a higher stop_order than the
                acquisition device. The default start_order and stop_order is zero, so
                if you are not otherwise controlling the order that devices are
                programmed, you can set start_order=-1, stop_order=1 on the timeout
                device only."""
            raise RuntimeError(dedent(msg))

    def generate_code(self, hdf5_file):
        """Write the AO, DO and AI tables to the shot file."""
        IntermediateDevice.generate_code(self, hdf5_file)
        analogs = {}
        digitals = {}
        inputs = {}
        for device in self.child_devices:
            if isinstance(device, (AnalogOut, StaticAnalogOut)):
                analogs[device.connection] = device
            elif isinstance(device, (DigitalOut, StaticDigitalOut)):
                digitals[device.connection] = device
            elif isinstance(device, AnalogIn):
                inputs[device.connection] = device
            else:
                raise TypeError(
                    f"{device.name} is not an analog output, digital output or analog "
                    f"input, so {self.name} cannot generate code for it."
                )

        clockline = self.parent_device
        if clockline is None:
            # No pseudoclock to call expand_timeseries() on our children.
            # Call it ourselves:
            for device in self.child_devices:
                if isinstance(device, (StaticDigitalOut, StaticAnalogOut)):
                    device.expand_timeseries()
            times = None
        else:
            times = clockline.parent_device.times[clockline]

        self._check_even_children(analogs, digitals)
        self._check_bounds(analogs)

        AO_table = self._make_analog_out_table(analogs, times)
        DO_table = self._make_digital_out_table(digitals, times)
        AI_table = self._make_analog_input_table(inputs)

        self._check_AI_not_too_fast(AI_table)
        self._check_wait_monitor_timeout_device_config()

        grp = self.init_device_group(hdf5_file)
        if AO_table is not None:
            grp.create_dataset('AO', data=AO_table, compression=compiler.compression)
        if DO_table is not None:
            grp.create_dataset('DO', data=DO_table, compression=compiler.compression)
        if AI_table is not None:
            grp.create_dataset('AI', data=AI_table, compression=compiler.compression)


# The models import NI_DAQmx from this module, so they load after it is defined; this
# also makes each model importable from here.
from .models import *
