#####################################################################
#                                                                   #
# /labscript_devices/CiceroOpalKellyXEM3001/labscript_devices.py    #
#                                                                   #
# Copyright 2013, Monash University                                 #
#                                                                   #
# This file is part of the module labscript_devices, in the         #
# labscript suite (see http://labscriptsuite.org), and is           #
# licensed under the Simplified BSD License. See the license.txt    #
# file in the root of the project for the full license.             #
#                                                                   #
#####################################################################

from labscript import (
    Device,
    PseudoclockDevice,
    Pseudoclock,
    ClockLine,
    LabscriptError,
    set_passed_properties,
    compiler,
    WaitMonitor,
    DigitalOut,
    internal_wait_monitor_outputs,
)

import numpy as np


# The most reps one instruction holds: the worker packs them into 4 bytes.
MAX_REPS = 2**32 - 1

class CiceroOpalKellyXEM3001(PseudoclockDevice):
    """A pseudoclock on an Opal Kelly XEM3001 FPGA board, with one clock line, `clockline`."""

    # Most timings are set in __init__, as they depend on the reference clock frequency.
    description = 'CiceroOpalKellyXEM3001'
    trigger_edge_type = 'rising'
    allowed_children = [Pseudoclock]
    # Its own pseudoclock, and the internal one its wait monitor hangs from.
    max_pseudoclocks = 2

    # Determined by confirming that an instruction table that is 2049 long
    # does not output the last instruction
    max_instructions = 2048

    @set_passed_properties(
        property_names={
            "connection_table_properties": [
                "reference_clock",
                "clock_frequency",
                "trigger_debounce_clock_ticks",
            ],
            "device_properties": ["trigger_delay", "wait_delay"],
        }
    )
    def __init__(
        self,
        name,
        trigger_device=None,
        trigger_connection=None,
        serial_number='',
        reference_clock='internal',
        clock_frequency=100e6,
        use_wait_monitor=None,
        trigger_debounce_clock_ticks=10,
        **kwargs,
    ):
        """
        Parameters
        ----------
        name : str
            Python variable name of the device.
        trigger_device : :class:`~labscript.IntermediateDevice`, optional
            Device that sends the hardware start trigger when this is a secondary
            pseudoclock. If `None`, the default, this is the master pseudoclock.
        trigger_connection : str, optional
            Output of `trigger_device` wired to the board's hardware trigger input;
            required if `trigger_device` is given.
        serial_number : str, optional
            Serial number of the Opal Kelly board, as BLACS opens it; ``''`` by
            default.
        reference_clock : str, optional
            ``'internal'``, the default, or ``'external'``: the reference clock the
            FPGA firmware runs from. BLACS flashes the matching bit file,
            ``CiceroOpalKellyXEM3001_fpga_internal.bit`` or
            ``CiceroOpalKellyXEM3001_fpga_external.bit``, from the
            `CiceroOpalKellyXEM3001` package folder.
        clock_frequency : float, optional
            Frequency of the reference clock in Hz; ``100e6`` by default.
            Instructions count its cycles, so its period is the clock resolution
            and half its frequency is the clock limit.
        use_wait_monitor : bool, optional
            Let the board time waits itself. If `None`, the default, a master
            pseudoclock does and a secondary does not; `True` on a secondary raises
            a LabscriptError, since only the master times the waits.
        trigger_debounce_clock_ticks : int, optional
            Debounce count of the FPGA's trigger input in reference clock cycles,
            from 0 to 65535; 10 by default. labscript takes the shortest trigger
            pulse as twice this, and the delay from trigger to output as this plus 5.
        **kwargs
            Passed to :class:`~labscript.PseudoclockDevice`.
        """
        if 'serial' in kwargs:
            raise LabscriptError(
                f"CiceroOpalKellyXEM3001 {name}: the keyword serial is serial_number."
            )
        self.clock_limit = clock_frequency/2
        self.clock_resolution = 1/clock_frequency
        # Twice the debounce time.
        self.trigger_minimum_duration = 2*trigger_debounce_clock_ticks/clock_frequency
        # An estimate, not measured: 3 clock cycles to reach the FPGA's state machine (three
        # non-blocking <= in its debounce code), then 2 before the output goes high (one to
        # leave the wait-for-retrigger code, one for the non-blocking output update).
        self.trigger_delay = (5+trigger_debounce_clock_ticks)/clock_frequency
        # An estimate, not measured: one clock cycle.
        self.wait_delay = self.clock_resolution

        PseudoclockDevice.__init__(self, name, trigger_device, trigger_connection, **kwargs)
        self.BLACS_connection = serial_number

        if not 0 <= trigger_debounce_clock_ticks < 2**16:
            raise LabscriptError(
                f"The {self.description} {self.name} trigger_debounce_clock_ticks must be "
                f"between 0 and 65535, not {trigger_debounce_clock_ticks}."
            )

        self._pseudoclock = Pseudoclock(
            f'{name}_pseudoclock', self, 'clock', max_clock_lines=1
        )
        # The board's one output, 'Clock Out', is this clock line; its worker and runviewer
        # parser use that name.
        self._clock_line = ClockLine(f'{name}_clock_line', self.pseudoclock, 'Clock Out')

        self.__wait_monitor_intermediate_device = internal_wait_monitor_outputs(self)

        # Only a master pseudoclock times the waits, so by default only a master has the
        # wait monitor.
        if use_wait_monitor is None:
            use_wait_monitor = self.is_master_pseudoclock
        elif use_wait_monitor and not self.is_master_pseudoclock:
            raise LabscriptError(
                f"The {self.description} {self.name} is a secondary pseudoclock, so it "
                "cannot have the wait monitor: only the master times the waits. "
                "Leave use_wait_monitor as None or set it to False."
            )
        if use_wait_monitor:
            WaitMonitor(
                f'{name}__wait_monitor',
                self.internal_wait_monitor_outputs,
                'internal',
                self.internal_wait_monitor_outputs,
                'internal',
                self.internal_wait_monitor_outputs,
                'internal',
            )

    @property
    def internal_wait_monitor_outputs(self):
        """The intermediate device the internal wait monitor is attached to."""
        return self.__wait_monitor_intermediate_device

    @property
    def pseudoclock(self):
        """The pseudoclock the device creates."""
        return self._pseudoclock

    @property
    def clockline(self):
        """The clock line the device creates, for the devices it clocks to connect to.

        Not to be confused with `parent_clock_line`, the clock line that clocks a device.
        """
        return self._clock_line

    def generate_code(self, hdf5_file):
        """Write the pulse program to the shot file, as PULSE_PROGRAM."""
        PseudoclockDevice.generate_code(self, hdf5_file)
        group = self.init_device_group(hdf5_file)

        reduced_instructions = []
        current_wait_index = 0
        wait_table = sorted(compiler.wait_table)

        if not self.is_master_pseudoclock:
            # A secondary begins with a wait for its first trigger.
            reduced_instructions.append(
                {'on': 0, 'off': ((self.trigger_edge_type == 'rising') << 1) + 1, 'reps': 0}
            )

        for instruction in self.pseudoclock.clock:
            if instruction == 'WAIT':
                wait_timeout = compiler.wait_table[wait_table[current_wait_index]][1]
                current_wait_index += 1

                # A wait has 0 reps; 'on' is the reference clock cycles to wait for the
                # trigger before resuming. The FPGA cannot resume until after the second
                # cycle, so it overcounts by 1, which is subtracted here.
                reduced_instructions.append(
                    {
                        'on': self.quantise_to_pseudoclock(wait_timeout, ticks=True) - 1,
                        'off': ((self.trigger_edge_type == 'rising') << 1) + 1,
                        'reps': 0,
                    }
                )
                continue
            reps = instruction['reps']
            # The period is in whole ticks of clock_resolution.
            periods = self.quantise_to_pseudoclock(instruction['step'], ticks=True)
            # The "high" half of the clock period.
            on_period = int(periods/2)
            # The remainder is the "off" period: this allows slightly asymmetric clock
            # signals, to minimise timing errors.
            off_period = periods-on_period

            # Merge consecutive clock instructions of the same periods, to save room in
            # the instruction table, but never into a wait (0 reps), and to no more reps
            # than the worker's 4 bytes hold, splitting a longer run.
            while reps:
                last = reduced_instructions[-1] if reduced_instructions else None
                if (
                    last
                    and 0 < last['reps'] < MAX_REPS
                    and last['on'] == on_period
                    and last['off'] == off_period
                ):
                    added = min(reps, MAX_REPS - last['reps'])
                    last['reps'] += added
                else:
                    added = min(reps, MAX_REPS)
                    reduced_instructions.append({'on': on_period, 'off': off_period, 'reps': added})
                reps -= added

        if len(reduced_instructions) > self.max_instructions:
            raise LabscriptError(
                f"{self.description} {self.name} has too many instructions: it has "
                f"{len(reduced_instructions)} and can support only "
                f"{self.max_instructions}. Reduce the number of waits and "
                "clock-period changes."
            )

        dtypes = [('on_period', np.int64), ('off_period', np.int64), ('reps', np.int64)]
        pulse_program = np.zeros(len(reduced_instructions), dtype=dtypes)
        for i, instruction in enumerate(reduced_instructions):
            pulse_program[i]['on_period'] = instruction['on']
            pulse_program[i]['off_period'] = instruction['off']
            pulse_program[i]['reps'] = instruction['reps']
        group.create_dataset(
            'PULSE_PROGRAM', compression=compiler.compression, data=pulse_program
        )
