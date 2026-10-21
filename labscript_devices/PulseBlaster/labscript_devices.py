#####################################################################
#                                                                   #
# /labscript_devices/PulseBlaster/labscript_devices.py              #
#                                                                   #
# Copyright 2013, Monash University                                 #
#                                                                   #
# This file is part of the module labscript_devices, in the         #
# labscript suite (see http://labscriptsuite.org), and is           #
# licensed under the Simplified BSD License. See the license.txt    #
# file in the root of the project for the full license.             #
#                                                                   #
#####################################################################

import inspect
import os
import sys
import warnings

from labscript_utils import dedent

from labscript import (
    Device,
    PseudoclockDevice,
    Pseudoclock,
    ClockLine,
    IntermediateDevice,
    DigitalQuantity,
    DigitalOut,
    DDS,
    DDSQuantity,
    LabscriptError,
    set_passed_properties,
    compiler,
)

import numpy as np

import labscript
import labscript_devices


class PulseBlasterDDS(DDSQuantity):
    """A DDS output of a PulseBlaster, with its own gate and phase reset."""

    description = 'PulseBlasterDDS'

    def __init__(self, *args, **kwargs):
        """Takes the arguments of :class:`~labscript.DDSQuantity`, with a `connection`
        of ``'dds 0'`` or ``'dds 1'``, but no `digital_gate`: the gate is always the
        PulseBlaster's own."""
        if 'call_parents_add_device' in kwargs:
            call_parents_add_device = kwargs['call_parents_add_device']
        else:
            call_parents_add_device = True

        kwargs['call_parents_add_device'] = False
        DDSQuantity.__init__(self, *args, **kwargs)

        self.gate = DigitalQuantity(self.name + '_gate', self, 'gate')
        self.phase_reset = DigitalQuantity(self.name + '_phase_reset', self, 'phase_reset')

        if call_parents_add_device:
            self.parent_device.add_device(self)

    def hold_phase(self, t):
        """Set the DDS's phase reset high at time `t`, in seconds."""
        self.phase_reset.go_high(t)

    def release_phase(self, t):
        """Set the DDS's phase reset low at time `t`, in seconds."""
        self.phase_reset.go_low(t)


class PulseBlasterBase(PseudoclockDevice):
    """The pseudoclock and flags of a SpinCore PulseBlaster board. A board's class
    sets its ``description``, ``clock_limit``, ``clock_resolution``, ``n_flags``
    and ``clock_frequency``, in Hz."""

    pb_instructions = {'CONTINUE':   0,
                       'STOP':       1,
                       'LOOP':       2,
                       'END_LOOP':   3,
                       'BRANCH':     6,
                       'LONG_DELAY': 7,
                       'WAIT':       8}

    # Coupled to the lengths, 100 ns each, of the first two instructions the BLACS
    # worker programs: change this and those together. Found experimentally; those
    # lengths and a finite delay in the PulseBlaster set it.
    trigger_delay = 250e-9
    wait_delay = 100e-9
    trigger_edge_type = 'falling'

    # Only the board's Pseudoclock can be its child; digital and DDS outputs connect
    # to `direct_outputs`, below it.
    allowed_children = [Pseudoclock]
    max_pseudoclocks = 1

    @set_passed_properties(
        property_names={
            "connection_table_properties": ["firmware", "programming_scheme"],
            "device_properties": [
                "pulse_width",
                "max_instructions",
                "time_based_stop_workaround",
                "time_based_stop_workaround_extra_time",
            ],
        }
    )
    def __init__(
        self,
        name,
        trigger_device=None,
        trigger_connection=None,
        board_number=0,
        firmware='',
        programming_scheme='pb_start/BRANCH',
        pulse_width='symmetric',
        max_instructions=4000,
        time_based_stop_workaround=False,
        time_based_stop_workaround_extra_time=0.5,
        **kwargs,
    ):
        """
        Parameters
        ----------
        name : str
            Python variable name of the device.
        trigger_device : :class:`~labscript.IntermediateDevice`, optional
            Device that sends the hardware start trigger when this is a secondary
            pseudoclock. A board with a `trigger_device` must use
            ``'pb_start/BRANCH'``.
        trigger_connection : str, optional
            Output of `trigger_device` wired to the board's hardware trigger input.
        board_number : int, optional
            Number of the board, which BLACS passes to SpinAPI's ``pb_select_board``;
            0 by default.
        firmware : str, optional
            The board's firmware version, saved in the connection table, where
            nothing reads it; ``''`` by default.
        programming_scheme : str, optional
            How BLACS starts and stops the board: ``'pb_start/BRANCH'``, the default,
            or ``'pb_stop_programming/STOP'``. With the first, a master starts when
            BLACS calls ``pb_start()``, in software time, and a secondary on its
            hardware trigger; the program ends with a BRANCH to a WAIT instruction at
            its beginning, ready to start again. With the second, BLACS leaves the board in programming mode until
            the shot starts, then calls ``pb_stop_programming()`` and ``pb_start()``;
            until then the board ignores hardware triggers, such as repeated ones from
            a 50/60 Hz line trigger. The program ends with a STOP, so further triggers
            do not run it again, and BLACS reprograms the board with the front panel's
            values after the shot. BLACS reads the scheme from the connection table.
        pulse_width : str or float, optional
            The high time of a clock tick: ``'symmetric'``, the default, makes it half
            the tick; ``'minimum'`` makes it the shortest possible, 0.5/`clock_limit`;
            a number is a fixed width in seconds, at least 0.5/`clock_limit`, which is
            rounded up to a multiple of half the `clock_resolution`. A fixed width
            above the minimum lowers `clock_limit` to 1/(width + 0.5/`clock_limit`).
        max_instructions : int, optional
            The most instructions the board's memory holds, counting the two that
            BLACS programs ahead of the pulse program and the one that ends it; 4000
            by default. Compiling a program with more raises ``LabscriptError``.
        time_based_stop_workaround : bool, optional
            For old PulseBlaster models that do not respond correctly to status
            checks, and so give no way to know when the shot has completed. If
            ``True``, BLACS instead waits until `stop_time`, plus the timeouts of
            all waits and `time_based_stop_workaround_extra_time`, after the shot
            starts, and takes the shot to end then. Since the timeouts of all waits
            are included, a timeout larger than necessary lengthens every shot, even
            when the waits are short. ``False`` by default.
        time_based_stop_workaround_extra_time : float, optional
            Seconds to wait beyond that, to allow for software timing variation;
            0.5 by default.
        **kwargs
            Passed to :class:`~labscript.PseudoclockDevice`.
        """
        PseudoclockDevice.__init__(self, name, trigger_device, trigger_connection, **kwargs)
        self.BLACS_connection = board_number
        self.firmware_version = firmware

        possible_programming_schemes = ['pb_start/BRANCH', 'pb_stop_programming/STOP']
        if programming_scheme not in possible_programming_schemes:
            raise LabscriptError(
                f"programming_scheme must be one of {possible_programming_schemes}, "
                f"not {programming_scheme!r}."
            )
        if trigger_device is not None and programming_scheme != 'pb_start/BRANCH':
            raise LabscriptError(
                f"{name} has a trigger_device, so it is not the master pseudoclock "
                f"and cannot use programming_scheme {programming_scheme!r}. "
                "Use 'pb_start/BRANCH'."
            )
        self.programming_scheme = programming_scheme

        # The board's minimum instruction duration, saved before a fixed pulse_width,
        # below, can lower clock_limit.
        self.min_delay = 0.5 / self.clock_limit

        # LEGACY CORE_CLOCK_FREQ COMPATIBILITY. DEPRECATED CODE, WILL BE REMOVED.
        if hasattr(self, 'core_clock_freq'):
            warnings.warn(
                f"{type(self).__name__}.core_clock_freq, in MHz, will be removed; "
                "set clock_frequency, in Hz.", FutureWarning, stacklevel=3
            )
            self.clock_frequency = self.core_clock_freq * 1e6
        # An instruction lasts at most 2**32 core clock cycles. A delay longer than
        # long_delay is some LONG_DELAYs and a remainder; long_delay is that maximum
        # less min_delay, so a remainder under min_delay can take one back and fit.
        self.long_delay = 2**32 / self.clock_frequency - self.min_delay

        if pulse_width == 'minimum':
            pulse_width = 0.5/self.clock_limit # the shortest possible
        elif pulse_width != 'symmetric':
            if not isinstance(pulse_width, (float, int, np.integer)):
                msg = ("pulse_width must be 'symmetric', 'minimum' or a number of "
                       f"seconds, not {pulse_width!r}.")
                raise ValueError(msg)

            if pulse_width < 0.5/self.clock_limit:
                message = (f"pulse_width {pulse_width} s is shorter than the minimum, "
                           f"0.5/{self.__class__.__name__}.clock_limit = "
                           f"{0.5/self.clock_limit} s. Use a longer pulse_width, "
                           "or 'minimum'.")
                raise LabscriptError(message)
            # Round the width up to a multiple of half the clock resolution, as the
            # width of a symmetric pulse is:
            quantised_pulse_width = 2*pulse_width/self.clock_resolution
            # Rounding first drops float error, so a width already a multiple stays one:
            quantised_pulse_width = int(np.ceil(round(quantised_pulse_width, 9)))
            # This will be used as the high time of clock ticks:
            pulse_width = quantised_pulse_width*self.clock_resolution/2
            # A tick lasts the pulse width plus the minimum low time, so a width above
            # the minimum lowers clock_limit.
            minimum_low_time = 0.5/self.clock_limit
            if pulse_width > minimum_low_time:
                self.clock_limit = 1/(pulse_width + minimum_low_time)
        self.pulse_width = pulse_width
        self.max_instructions = max_instructions

        self._pseudoclock = Pseudoclock('%s_pseudoclock'%name, self, 'clock')
        self._direct_output_clock_line = ClockLine('%s_direct_output_clock_line'%name, self.pseudoclock, 'internal', ramping_allowed = False)
        # The board's direct DigitalOuts and DDSs connect to this device, on an internal
        # clock line.
        self._direct_output_device = PulseBlasterDirectOutputs('%s_direct_output_device'%name, self._direct_output_clock_line)

    @property
    def pseudoclock(self):
        """The board's pseudoclock, which its clock lines connect to."""
        return self._pseudoclock

    @property
    def direct_outputs(self):
        """The device that the board's digital outputs, 'flag n', and DDS outputs, 'dds n', connect to."""
        return self._direct_output_device

    def flag_valid(self, flag):
        if -1 < flag < self.n_flags:
            return True
        return False

    def flag_is_clock(self, flag):
        for clock_line in self.pseudoclock.child_devices:
            if clock_line.connection == 'internal': # the internal clock line has no flag
                continue
            if flag == self.get_flag_number(clock_line.connection):
                return True
        return False

    def get_flag_number(self, connection):
        prefix, connection = connection.split()
        return int(connection)

    def get_direct_outputs(self):
        """Return the direct digital outputs and DDSs, after checking their connections."""
        dig_outputs = []
        dds_outputs = []
        for output in self.direct_outputs.get_all_outputs():
            # This also returns a DDS's channels; process each DDS once, in place of
            # the first of them.
            if isinstance(output.parent_device, DDS) or isinstance(output.parent_device, PulseBlasterDDS):
                if output.parent_device not in dds_outputs:
                    output = output.parent_device
                else:
                    continue

            if isinstance(output,DDS) or isinstance(output,PulseBlasterDDS) or isinstance(output, DigitalOut):
                try:
                    prefix, connection = output.connection.split()
                    assert prefix == 'flag' or prefix == 'dds'
                    connection = int(connection)
                except:
                    raise LabscriptError(
                        f"{output.description} {output.name} has invalid connection string: "
                        f"{output.connection!r}. Format must be 'flag n' with n an integer "
                        f"less than {self.n_flags}, or 'dds n' with n less than 2."
                    )
                if prefix == 'flag' and not self.flag_valid(connection):
                    raise LabscriptError(
                        f"{output.name} is connected to flag {connection} of {self.name}, "
                        f"which has flags 0 to {self.n_flags-1}. Connect it to a flag "
                        "in that range."
                    )
                if prefix == 'flag' and self.flag_is_clock(connection):
                    raise LabscriptError(
                        f"{output.name} is connected to flag {connection} of {self.name}, "
                        "which a clock line already uses. Connect it to another flag."
                    )
                if prefix == 'dds' and not connection < 2:
                    raise LabscriptError(
                        f"{output.name} is connected to DDS output {connection} of "
                        f"{self.name}, which has only 'dds 0' and 'dds 1'. Connect it "
                        "to one of those."
                    )

                for other_output in dig_outputs + dds_outputs:
                    if output.connection == other_output.connection:
                        raise LabscriptError(
                            f"{output.name} and {other_output.name} are both connected "
                            f"to {output.connection} of {self.name}. Connect each "
                            "output to its own flag or DDS output."
                        )

                if isinstance(output, DigitalOut):
                    dig_outputs.append(output)
                elif isinstance(output, DDS) or isinstance(output, PulseBlasterDDS):
                    dds_outputs.append(output)

        return dig_outputs, dds_outputs

    def convert_to_pb_inst(self, dig_outputs):
        pb_inst = []

        # Index into output.raw_output of the values the flags take. It starts at -1
        # because the internal clock line ticks on the first instruction, which
        # increments it to 0 before any array is indexed with it.
        i = -1
        # Number of the hardware instruction being written, which an END_LOOP's data
        # gives as the LOOP to return to.
        j = 0
        # We've delegated the initial two instructions off to BLACS, which
        # can ensure continuity with the state of the front panel. Thus
        # these two instructions don't actually do anything:
        flags = [0]*self.n_flags
        # An instruction's 'output_index' is the i its outputs' values come
        # from; these two have none:
        pb_inst.append({'output_index': None,
                        'flags': ''.join([str(flag) for flag in flags]), 'instruction': 'STOP',
                        'data': 0, 'delay': 10.0/self.clock_limit*1e9})
        pb_inst.append({'output_index': None,
                        'flags': ''.join([str(flag) for flag in flags]), 'instruction': 'STOP',
                        'data': 0, 'delay': 10.0/self.clock_limit*1e9})
        j += 2

        flagstring = '0'*self.n_flags # So that this variable is still defined if the for loop has no iterations
        for k, instruction in enumerate(self.pseudoclock.clock):
            if instruction == 'WAIT':
                # This is a wait instruction. Repeat the last instruction but with a 100ns delay and a WAIT op code:
                wait_instruction = pb_inst[-1].copy()
                wait_instruction['delay'] = 100
                wait_instruction['instruction'] = 'WAIT'
                wait_instruction['data'] = 0
                pb_inst.append(wait_instruction)
                j += 1
                continue

            flags = [0]*self.n_flags

            # This flag indicates whether we need a full clock tick, or are just updating an internal output
            only_internal = True
            for clock_line in instruction['enabled_clocks']:
                if clock_line == self._direct_output_clock_line:
                    # advance i, the index of the internal clock line's outputs
                    i += 1
                else:
                    flag_index = int(clock_line.connection.split()[1])
                    flags[flag_index] = 1
                    only_internal = False

            for output in dig_outputs:
                flagindex = int(output.connection.split()[1])
                flags[flagindex] = int(output.raw_output[i])

            flagstring = ''.join([str(flag) for flag in flags])

            if instruction['reps'] > 1048576:
                raise LabscriptError(
                    "A PulseBlaster can loop at most 1048576 times, but "
                    f"{instruction['reps']} repetitions were requested at t = "
                    f"{instruction['start']} s. The device class does not nest loops to go "
                    "further. Shorten that stretch of the shot, or lengthen its clock "
                    "period."
                )

            if not only_internal:
                if self.pulse_width == 'symmetric':
                    high_time = instruction['step']/2
                else:
                    high_time = self.pulse_width
                # A high time over long_delay (~57 s for a 75 MHz core clock) is clipped
                # to it, so the requested symmetric or fixed pulse width is not honoured:
                # honouring it would use more instructions.
                high_time = min(high_time, self.long_delay)

                low_time = instruction['step'] - high_time

                n_long_delays, remaining_low_time =  divmod(low_time, self.long_delay)

                # A remainder under min_delay is too short to output: take one long_delay
                # back from n_long_delays. The sum is under 2**32 core clock cycles, as
                # long_delay is that less min_delay.
                if n_long_delays and remaining_low_time < self.min_delay:
                    n_long_delays -= 1
                    remaining_low_time += self.long_delay

                # The start of the loop. Clock edges are high:
                pb_inst.append({'output_index': i,
                                'flags': flagstring, 'instruction': 'LOOP',
                                'data': instruction['reps'], 'delay': high_time*1e9})

                for clock_line in instruction['enabled_clocks']:
                    if clock_line != self._direct_output_clock_line:
                        flag_index = int(clock_line.connection.split()[1])
                        flags[flag_index] = 0

                flagstring = ''.join([str(flag) for flag in flags])

                # The long delay instruction, if any. Clock edges are low:
                if n_long_delays:
                    pb_inst.append({'output_index': i,
                                'flags': flagstring, 'instruction': 'LONG_DELAY',
                                'data': int(n_long_delays), 'delay': self.long_delay*1e9})

                # Remaining low time. Clock edges are low:
                pb_inst.append({'output_index': i,
                                'flags': flagstring, 'instruction': 'END_LOOP',
                                'data': j, 'delay': remaining_low_time*1e9})

                # Two instructions were used in the case of there being no LONG_DELAY,
                # otherwise three. This increment is done here so that the j referred
                # to in the previous line still refers to the LOOP instruction.
                j += 3 if n_long_delays else 2
            else:
                # We only need to update a direct output, so no need to tick the clocks.
                n_long_delays, remaining_delay =  divmod(instruction['step'], self.long_delay)
                # As for the low time, a remainder under min_delay takes one long_delay back.
                if n_long_delays and remaining_delay < self.min_delay:
                    n_long_delays -= 1
                    remaining_delay += self.long_delay

                if n_long_delays:
                    pb_inst.append({'output_index': i,
                                'flags': flagstring, 'instruction': 'LONG_DELAY',
                                'data': int(n_long_delays), 'delay': self.long_delay*1e9})

                pb_inst.append({'output_index': i,
                                'flags': flagstring, 'instruction': 'CONTINUE',
                                'data': 0, 'delay': remaining_delay*1e9})

                j += 2 if n_long_delays else 1

        if self.programming_scheme == 'pb_start/BRANCH':
            # Branch from the last instruction to instruction zero, which BLACS programs
            # with the same values and a WAIT. The PulseBlaster then waits there, ready
            # for a static update or the next shot.
            pb_inst.append({'output_index': pb_inst[-1]['output_index'],
                            'flags': flagstring, 'instruction': 'BRANCH',
                            'data': 0, 'delay': 10.0/self.clock_limit*1e9})
        elif self.programming_scheme == 'pb_stop_programming/STOP':
            # An ordinary STOP, as a WAIT would run the program again on each repeated
            # trigger, such as a 50/60 Hz line trigger. On some models the outputs may
            # reset to zero briefly, until BLACS calls program_manual after the shot.
            pb_inst.append({'output_index': pb_inst[-1]['output_index'],
                            'flags': flagstring, 'instruction': 'STOP',
                            'data': 0, 'delay': 10.0/self.clock_limit*1e9})
        else:
            raise AssertionError('Invalid programming scheme %s'%str(self.programming_scheme))

        if len(pb_inst) > self.max_instructions:
            raise LabscriptError(
                f"{self.name} can store at most {self.max_instructions} instructions, but "
                f"its pulse program has {len(pb_inst)}. Reduce the shot's output changes, "
                "clock-rate changes and waits, or raise max_instructions if the board "
                "has room for more."
            )

        return pb_inst

    def write_pb_inst_to_h5(self, pb_inst, hdf5_file):
        pb_dtype= [('flags',np.int32), ('inst',np.int32), ('inst_data',np.int32), ('length',np.float64)]
        pb_inst_table = np.empty(len(pb_inst),dtype = pb_dtype)
        for i,inst in enumerate(pb_inst):
            flagint = int(inst['flags'][::-1],2)
            instructionint = self.pb_instructions[inst['instruction']]
            dataint = inst['data']
            delaydouble = inst['delay']
            pb_inst_table[i] = (flagint, instructionint, dataint, delaydouble)

        group = hdf5_file['/devices/'+self.name]
        group.create_dataset('PULSE_PROGRAM', compression=compiler.compression,data = pb_inst_table)

    def _check_wait_monitor_ok(self):
        if (
            compiler.master_pseudoclock is self
            and compiler.wait_table
            and compiler.wait_monitor is None
            and self.programming_scheme != 'pb_stop_programming/STOP'
        ):
            msg = f"""{self.name} is the master pseudoclock and the shot has waits but no
                wait monitor, so it must have
                programming_scheme='pb_stop_programming/STOP'. Otherwise there is no way
                for BLACS to distinguish between a wait and the end of a shot. Either
                use a wait monitor (see labscript.WaitMonitor for details) or set
                programming_scheme='pb_stop_programming/STOP' for {self.name}."""
            raise LabscriptError(dedent(msg))

    def generate_code(self, hdf5_file):
        self.init_device_group(hdf5_file)
        PseudoclockDevice.generate_code(self, hdf5_file)
        dig_outputs, dds_outputs = self.get_direct_outputs()
        if dds_outputs:
            names = ', '.join(dds.name for dds in dds_outputs)
            raise LabscriptError(
                f"{self.name} ({self.description}) has no DDS outputs, so {names} "
                "cannot be connected to it."
            )
        pb_inst = self.convert_to_pb_inst(dig_outputs)
        self._check_wait_monitor_ok()
        self.write_pb_inst_to_h5(pb_inst, hdf5_file)


class DDSPulseBlasterMixin:
    """The two DDS outputs, ``'dds 0'`` and ``'dds 1'``, of a PulseBlaster board
    that has them. It comes before :class:`PulseBlasterBase` in a board's bases."""

    def generate_registers(self, hdf5_file, dds_outputs):
        ampdicts = {}
        phasedicts = {}
        freqdicts = {}
        group = hdf5_file['/devices/'+self.name]
        dds_dict = {}
        for output in dds_outputs:
            num = int(output.connection.split()[1])
            dds_dict[num] = output
        for num in [0,1]:

            if num in dds_dict:
                output = dds_dict[num]

                if any(output.amplitude.raw_output > 1)  or any(output.amplitude.raw_output < 0):
                    raise LabscriptError(
                        f"{output.amplitude.description} {output.amplitude.name} can only "
                        f"have values between 0 and 1, the limit imposed by {output.name}."
                    )

                if any(output.frequency.raw_output > 150e6 )  or any(output.frequency.raw_output < 0):
                    raise LabscriptError(
                        f"{output.frequency.description} {output.frequency.name} can only "
                        "have values between 0 Hz and 150 MHz, the limit imposed by "
                        f"{output.name}."
                    )

                output.phase.raw_output %= 360

                amps = set(output.amplitude.raw_output)
                phases = set(output.phase.raw_output)
                freqs = set(output.frequency.raw_output)
            else:
                # If the DDS is unused, it will use the following values
                # for the whole experimental run:
                amps = set([0])
                phases = set([0])
                freqs = set([0])

            if len(amps) > 1024:
                raise LabscriptError(
                    f"{self.name} dds {num} can only support 1024 amplitude registers, but "
                    f"{len(amps)} were requested. Use fewer distinct amplitudes on it."
                )
            if len(phases) > 128:
                raise LabscriptError(
                    f"{self.name} dds {num} can only support 128 phase registers, but "
                    f"{len(phases)} were requested. Use fewer distinct phases on it."
                )
            if len(freqs) > 1024:
                raise LabscriptError(
                    f"{self.name} dds {num} can only support 1024 frequency registers, but "
                    f"{len(freqs)} were requested. Use fewer distinct frequencies on it."
                )

            # Register zero is left for BLACS, which fills it with the front panel's
            # value, so counting starts at 1:
            ampregs = range(1,len(amps)+1)
            freqregs = range(1,len(freqs)+1)
            phaseregs = range(1,len(phases)+1)

            ampdicts[num] = dict(zip(amps,ampregs))
            freqdicts[num] = dict(zip(freqs,freqregs))
            phasedicts[num] = dict(zip(phases,phaseregs))

            # The zeros are the dummy instructions:
            freq_table = np.array([0] + list(freqs), dtype = np.float64) / 1e6 # convert to MHz
            amp_table = np.array([0] + list(amps), dtype = np.float32)
            phase_table = np.array([0] + list(phases), dtype = np.float64)

            subgroup = group.create_group('DDS%d'%num)
            subgroup.create_dataset('FREQ_REGS', compression=compiler.compression, data = freq_table)
            subgroup.create_dataset('AMP_REGS', compression=compiler.compression, data = amp_table)
            subgroup.create_dataset('PHASE_REGS', compression=compiler.compression, data = phase_table)

        return freqdicts, ampdicts, phasedicts

    def write_pb_inst_to_h5(self, pb_inst, hdf5_file):
        pb_dtype = [('freq0', np.int32), ('phase0', np.int32), ('amp0', np.int32),
                    ('dds_en0', np.int32), ('phase_reset0', np.int32),
                    ('freq1', np.int32), ('phase1', np.int32), ('amp1', np.int32),
                    ('dds_en1', np.int32), ('phase_reset1', np.int32),
                    ('flags', np.int32), ('inst', np.int32),
                    ('inst_data', np.int32), ('length', np.float64)]
        pb_inst_table = np.empty(len(pb_inst),dtype = pb_dtype)
        for i,inst in enumerate(pb_inst):
            flagint = int(inst['flags'][::-1],2)
            instructionint = self.pb_instructions[inst['instruction']]
            dataint = inst['data']
            delaydouble = inst['delay']
            freq0 = inst['freqs'][0]
            freq1 = inst['freqs'][1]
            phase0 = inst['phases'][0]
            phase1 = inst['phases'][1]
            amp0 = inst['amps'][0]
            amp1 = inst['amps'][1]
            en0 = inst['enables'][0]
            en1 = inst['enables'][1]
            phase_reset0 = inst['phase_resets'][0]
            phase_reset1 = inst['phase_resets'][1]

            pb_inst_table[i] = (freq0,phase0,amp0,en0,phase_reset0,freq1,phase1,amp1,en1,phase_reset1, flagint,
                                instructionint, dataint, delaydouble)

        group = hdf5_file['/devices/'+self.name]
        group.create_dataset('PULSE_PROGRAM', compression=compiler.compression,data = pb_inst_table)

    def generate_code(self, hdf5_file):
        self.init_device_group(hdf5_file)
        PseudoclockDevice.generate_code(self, hdf5_file)
        dig_outputs, dds_outputs = self.get_direct_outputs()
        freqs, amps, phases = self.generate_registers(hdf5_file, dds_outputs)
        pb_inst = self.convert_to_pb_inst(dig_outputs)
        for inst in pb_inst:
            i = inst['output_index']
            if i is None:
                # BLACS fills in these dummy instructions' registers zero with
                # the front panel's values:
                inst.update(freqs=[0]*2, amps=[0]*2, phases=[0]*2, enables=[0]*2, phase_resets=[0]*2)
                continue
            # Registers one, not zero, so as not to use the dummy instructions'
            # values: an unused DDS has its zeros in register one.
            inst.update(freqs=[1]*2, amps=[1]*2, phases=[1]*2, enables=[0]*2, phase_resets=[0]*2)
            for output in dds_outputs:
                n = int(output.connection.split()[1])
                inst['freqs'][n] = freqs[n][output.frequency.raw_output[i]]
                inst['amps'][n] = amps[n][output.amplitude.raw_output[i]]
                inst['phases'][n] = phases[n][output.phase.raw_output[i]]
                inst['enables'][n] = output.gate.raw_output[i]
                if isinstance(output, PulseBlasterDDS):
                    inst['phase_resets'][n] = output.phase_reset.raw_output[i]
        self._check_wait_monitor_ok()
        self.write_pb_inst_to_h5(pb_inst, hdf5_file)


class PulseBlaster(DDSPulseBlasterMixin, PulseBlasterBase):
    """A SpinCore PulseBlaster DDS-II-300 board, with 12 flags and two DDS outputs."""

    description = 'PB-DDSII-300'
    clock_limit = 8.3e6 # Slight underestimate I think.
    clock_resolution = 26.6666666666666666e-9
    n_flags = 12
    clock_frequency = 75e6


# LEGACY VPP AMPLITUDE COMPATIBILITY. DEPRECATED CODE, WILL BE REMOVED.
_SUITE = (
    os.path.dirname(labscript.__file__) + os.sep,
    os.path.dirname(labscript_devices.__file__) + os.sep,
)


def _takes_first(frame, device):
    """Whether `frame`'s function was given `device` as its first argument."""
    code = frame.f_code
    if code.co_argcount:
        return frame.f_locals.get(code.co_varnames[0]) is device
    if code.co_flags & inspect.CO_VARARGS:
        args = frame.f_locals.get(code.co_varnames[code.co_kwonlyargcount])
        return bool(args) and args[0] is device
    return False


class PulseBlasterDirectOutputs(IntermediateDevice):
    """The internal device that a PulseBlaster's digital outputs and DDSs connect to."""

    allowed_children = [DDS, PulseBlasterDDS, DigitalOut]
    clock_limit = PulseBlaster.clock_limit
    description = 'PB-DDSII-300 Direct Outputs'

    def add_device(self, device):
        IntermediateDevice.add_device(self, device)
        # LEGACY VPP AMPLITUDE COMPATIBILITY. DEPRECATED CODE, WILL BE REMOVED.
        conversion = getattr(getattr(device, 'amplitude', None), 'unit_conversion_class', None)
        if getattr(conversion, 'base_unit', None) == 'Vpp':
            # Warn at the line that made or added the DDS: past the suite's code, the
            # DDS's own __init__s and the wrappers that called them, which take the DDS
            # first. A function that only adds it is the line. Never raise.
            try:
                stacklevel, frame, constructing = 2, sys._getframe(1), False
                while True:
                    takes_dds = _takes_first(frame, device)
                    constructor = takes_dds and frame.f_code.co_name == '__init__'
                    wrapper = takes_dds and constructing
                    in_suite = frame.f_code.co_filename.startswith(_SUITE)
                    if not (in_suite or constructor or wrapper):
                        break
                    constructing = constructor or wrapper or (in_suite and constructing)
                    stacklevel, frame = stacklevel + 1, frame.f_back
            except Exception:
                stacklevel = 2
            warnings.warn(
                f"{conversion.__name__}'s base_unit 'Vpp' will be removed for a "
                "PulseBlaster DDS amplitude; use 'Arb'.", FutureWarning,
                stacklevel=stacklevel,
            )
        if isinstance(device, DDS):
            # The gate is always internal to the PulseBlaster, so a DDS given a digital
            # gate of its own is refused; this DigitalQuantity keeps track of the gating.
            if device.gate is None:
                device.gate = DigitalQuantity(device.name + '_gate', device, 'gate')
            else:
                raise LabscriptError(
                    f"{device.name} was given a digital_gate, but the gate of a DDS "
                    f"connected to {self.name} is always internal to the PulseBlaster. "
                    "Remove the digital_gate."
                )
