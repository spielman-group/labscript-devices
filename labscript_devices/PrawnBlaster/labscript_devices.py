#####################################################################
#                                                                   #
# /labscript_devices/PrawnBlaster/labscript_devices.py              #
#                                                                   #
# Copyright 2021, Philip Starkey                                    #
#                                                                   #
# This file is part of labscript_devices, in the labscript suite    #
# (see http://labscriptsuite.org), and is licensed under the        #
# Simplified BSD License. See the license.txt file in the root of   #
# the project for the full license.                                 #
#                                                                   #
#####################################################################

import copy

from labscript import (
    ClockLine,
    LabscriptError,
    PseudoclockDevice,
    Pseudoclock,
    WaitMonitor,
    compiler,
    internal_wait_monitor_outputs,
    set_passed_properties,
)
import numpy as np


class _PrawnBlasterPseudoclock(Pseudoclock):
    """A pseudoclock with one clockline that knows its hardware index `i`."""

    def __init__(self, i, *args, **kwargs):
        """`i` is the pseudoclock's index on the board; the rest go to `Pseudoclock`."""
        super().__init__(*args, **kwargs)
        self.i = i

    max_clock_lines = 1


class PrawnBlaster(PseudoclockDevice):
    """A Raspberry Pi Pico with the PrawnBlaster firmware, providing one to four pseudoclocks."""

    description = "PrawnBlaster"
    clock_limit = 1 / 100e-9
    """Maximum allowable clock rate."""
    clock_resolution = 20e-9
    """Minimum resolvable time for a clock tick."""
    input_response_time = 50e-9
    """Time necessary for hardware to respond to a hardware trigger. 
    Empirically determined to be a ~50 ns buffer on the input.
    """
    trigger_delay = input_response_time + 80e-9
    """Processing time delay after trigger is detected. Due to firmware, there is an
    80 ns delay between trigger detection and first output pulse."""
    trigger_minimum_duration = 160e-9
    """Minimum required width of hardware trigger. An overestimate that covers
    currently unsupported indefinite waits."""
    wait_delay = 40e-9
    """Minimum required length of a wait before retrigger can be detected.
    Corresponds to 4 instructions."""
    max_half_period = 2**32 - 1
    """Largest half_period of an instruction, in clock cycles. The firmware stores
    half_period and reps as 32-bit unsigned integers."""
    max_reps = 2**32 - 1
    """Largest number of repetitions of an instruction."""
    allowed_children = [Pseudoclock]
    allowed_boards = ['pico1', 'pico2']
    max_instructions_map = {'pico1' : 30000, 'pico2' : 60000}
    """Each pico board's instruction table, shared equally between its pseudoclocks."""
    max_frequency_map = {'pico1' : 133e6, 'pico2' : 150e6}

    @set_passed_properties(
        property_names={
            "connection_table_properties": [
                "com_port",
                'pico_board',
                "in_pins",
                "out_pins",
                "num_pseudoclocks",
            ],
            "device_properties": [
                "clock_frequency",
                "external_clock_pin",
                "clock_limit",
                "clock_resolution",
                "input_response_time",
                "trigger_delay",
                "trigger_minimum_duration",
                "wait_delay",
                "max_instructions",
            ],
        }
    )
    def __init__(
        self,
        name,
        trigger_device=None,
        trigger_connection=None,
        com_port="COM1",
        pico_board = 'pico1',
        num_pseudoclocks=1,
        out_pins=None,
        in_pins=None,
        clock_frequency=100e6,
        external_clock_pin=None,
        use_wait_monitor=True,
        **kwargs,
    ):
        """
        Parameters
        ----------
        name : str
            Python variable name of the device.
        trigger_device : :class:`~labscript.IntermediateDevice`, optional
            Device that sends the hardware start trigger when this is a secondary
            pseudoclock.
        trigger_connection : str, optional
            Output of `trigger_device` wired to the hardware trigger input.
        com_port : str, optional
            Serial port the OS assigned, such as ``'COM1'``, the default.
        pico_board : str, optional
            ``'pico1'``, the default, or ``'pico2'``.
        num_pseudoclocks : int, optional
            Number of pseudoclocks, from 1, the default, to 4.
        out_pins : list of int, optional
            Pins for the pseudoclock outputs, at least `num_pseudoclocks` of them;
            ``[9, 11, 13, 15]`` by default. The firmware takes pins 0 to 19 or 25.
        in_pins : list of int, optional
            Pins for the pseudoclocks' hardware trigger inputs, at least
            `num_pseudoclocks` of them; ``[0, 0, 0, 0]`` by default. The firmware
            takes pins 0 to 19, none of them an out pin.
        clock_frequency : float, optional
            Clock frequency in Hz; 100 MHz by default, at most 133 MHz for pico1 and
            150 MHz for pico2. The class's timings are for 100 MHz and scale with it.
        external_clock_pin : int, optional
            If not `None` (the default), the pin, 20 or 22, of an external clock whose
            frequency is `clock_frequency`.
        use_wait_monitor : bool, optional
            Let the PrawnBlaster monitor waits itself, as it does by default. Only a
            master pseudoclock can.
        **kwargs
            Passed to :class:`~labscript.PseudoclockDevice`.
        """
        if pico_board in self.allowed_boards:
            self.pico_board = pico_board
        else:
            raise LabscriptError(
                f"Pico board {pico_board!r} is not supported. "
                f"Use one of {self.allowed_boards}."
            )

        if num_pseudoclocks < 1 or num_pseudoclocks > 4:
            raise LabscriptError(
                f"The PrawnBlaster {name} supports between 1 and 4 pseudoclocks, "
                f"not {num_pseudoclocks}."
            )

        self.max_instructions = self.max_instructions_map[self.pico_board]
        # The instruction table is shared equally between the pseudoclocks.
        self.max_instructions = self.max_instructions // num_pseudoclocks

        self.max_frequency = self.max_frequency_map[self.pico_board]

        if clock_frequency > self.max_frequency:
            raise ValueError(
                f"Clock frequency must be at most {int(self.max_frequency * 10**-6)} MHz "
                f"for {self.pico_board}."
            )
        # The class-level timings are for a 100 MHz clock; scale them to this one.
        # The clock limit is a rate, so it scales the other way.
        if self.clock_resolution != 2 / clock_frequency:
            factor = (2 / clock_frequency) / self.clock_resolution
            self.clock_limit /= factor
            self.clock_resolution *= factor
            self.input_response_time *= factor
            self.trigger_delay *= factor
            self.trigger_minimum_duration *= factor
            self.wait_delay *= factor

        PseudoclockDevice.__init__(self, name, trigger_device, trigger_connection, **kwargs)
        self.num_pseudoclocks = num_pseudoclocks
        # Wait monitor can only be used if this is the master pseudoclock
        self.use_wait_monitor = use_wait_monitor and self.is_master_pseudoclock
        # One pseudoclock per output, and the internal one a wait monitor hangs from.
        self.max_pseudoclocks = num_pseudoclocks + self.use_wait_monitor

        self.BLACS_connection = com_port

        if out_pins is None:
            out_pins = [9, 11, 13, 15]
        if in_pins is None:
            in_pins = [0, 0, 0, 0]
        if len(out_pins) < num_pseudoclocks:
            raise LabscriptError(
                f"The PrawnBlaster {self.name} has {num_pseudoclocks} pseudoclocks "
                f"but out_pins gives {len(out_pins)}. "
                "Give one out pin for each pseudoclock."
            )
        else:
            self.out_pins = out_pins[:num_pseudoclocks]
        if len(in_pins) < num_pseudoclocks:
            raise LabscriptError(
                f"The PrawnBlaster {self.name} has {num_pseudoclocks} pseudoclocks "
                f"but in_pins gives {len(in_pins)}. "
                "Give one in pin for each pseudoclock."
            )
        else:
            self.in_pins = in_pins[:num_pseudoclocks]

        self._pseudoclocks = []
        self._clocklines = []
        for i in range(num_pseudoclocks):
            self._pseudoclocks.append(
                _PrawnBlasterPseudoclock(
                    i,
                    name=f"{name}_pseudoclock_{i}",
                    pseudoclock_device=self,
                    connection=f"pseudoclock {i}",
                )
            )
            self._clocklines.append(
                ClockLine(
                    name=f"{name}_clock_line_{i}",
                    pseudoclock=self._pseudoclocks[i],
                    connection=f"GPIO {self.out_pins[i]}",
                )
            )

        if self.use_wait_monitor:
            # Create internal devices for connecting to a wait monitor
            self.__wait_monitor_intermediate_device = internal_wait_monitor_outputs(self)

            WaitMonitor(
                f"{name}__wait_monitor",
                self.internal_wait_monitor_outputs,
                "internal",
                self.internal_wait_monitor_outputs,
                "internal",
                self.internal_wait_monitor_outputs,
                "internal",
            )

    @property
    def internal_wait_monitor_outputs(self):
        """The intermediate device the internal wait monitor is attached to."""
        return self.__wait_monitor_intermediate_device

    @property
    def pseudoclocks(self):
        """The device's pseudoclocks, as a new list of :class:`_PrawnBlasterPseudoclock`."""
        return copy.copy(self._pseudoclocks)

    @property
    def clocklines(self):
        """The device's clocklines, as a new list of :class:`~labscript.ClockLine`."""
        return copy.copy(self._clocklines)

    def generate_code(self, hdf5_file):
        """Write each pseudoclock's pulse program to the shot file."""
        PseudoclockDevice.generate_code(self, hdf5_file)
        group = self.init_device_group(hdf5_file)

        current_wait_index = 0
        wait_table = sorted(compiler.wait_table)

        for i, pseudoclock in enumerate(self.pseudoclocks):
            current_wait_index = 0

            # Compress clock instructions with the same half_period
            reduced_instructions = []
            for instruction in pseudoclock.clock:
                if instruction == "WAIT":
                    # If we're using the internal wait monitor, set the timeout
                    if self.use_wait_monitor:
                        wait_time = wait_table[current_wait_index]
                        wait_timeout = compiler.wait_table[wait_time][1]
                        current_wait_index += 1
                        half_period = round(wait_timeout / (self.clock_resolution / 2))
                        if half_period > self.max_half_period:
                            max_timeout = self.max_half_period * self.clock_resolution / 2
                            raise LabscriptError(
                                f"{self.description} {self.name}: the wait at t={wait_time} s "
                                f"has a timeout of {wait_timeout} s, longer than the "
                                f"maximum of {max_timeout:.1f} s."
                            )
                        # The following half_period and reps indicates a wait instruction
                        reduced_instructions.append({"half_period": half_period, "reps": 0})
                        continue
                    # Else, set an indefinite wait and wait for a trigger from something else.
                    else:
                        # Two waits in a row are an indefinite wait
                        reduced_instructions.append(
                            {"half_period": self.max_half_period, "reps": 0}
                        )
                        reduced_instructions.append(
                            {"half_period": self.max_half_period, "reps": 0}
                        )
                        continue

                reps = instruction["reps"]
                # half_period is in quantised units:
                half_period = self.quantise_to_pseudoclock(instruction["step"], ticks=True)
                if half_period > self.max_half_period:
                    max_step = self.max_half_period * self.clock_resolution
                    start = instruction["start"]
                    raise LabscriptError(
                        f"{self.description} {self.name}.clocklines[{i}] has no clock "
                        f"ticks between t={start} s and t={start + instruction['step']} s. "
                        f"This interval of {instruction['step']} s is longer than the "
                        f"maximum of {max_step:.1f} s between clock ticks. Command an "
                        f"output on this clockline at least once every {max_step:.1f} s."
                    )
                if reps > self.max_reps:
                    raise LabscriptError(
                        f"{self.description} {self.name}.clocklines[{i}] requires {reps} "
                        f"clock ticks of period {instruction['step']} s from "
                        f"t={instruction['start']} s, more than the maximum of "
                        f"{self.max_reps} repetitions of one instruction."
                    )
                if (
                    # If there is a previous instruction
                    reduced_instructions
                    # And it's not a wait
                    and reduced_instructions[-1]["reps"] != 0
                    # And the half_periods match
                    and reduced_instructions[-1]["half_period"] == half_period
                    # And the sum of the previous reps and current reps won't push it over the limit
                    and (reduced_instructions[-1]["reps"] + reps) < self.max_reps
                ):
                    reduced_instructions[-1]["reps"] += reps
                else:
                    reduced_instructions.append(
                        {"half_period": half_period, "reps": reps}
                    )

            # Only add this if there is room in the instruction table. The firmware
            # keeps a zero instruction after each pseudoclock's share, which stops a
            # program that fills it.
            if len(reduced_instructions) != self.max_instructions:
                # The following half_period and reps indicates a stop instruction:
                reduced_instructions.append({"half_period": 0, "reps": 0})

            # max_instructions is already the share of each pseudoclock.
            if len(reduced_instructions) > self.max_instructions:
                raise LabscriptError(
                    f"{self.description} {self.name}.clocklines[{i}] has too many "
                    f"instructions: it has {len(reduced_instructions)} and can support "
                    f"only {self.max_instructions}. Reduce the number of waits and "
                    "clock-period changes, or use fewer pseudoclocks on this device."
                )

            dtypes = [("half_period", int), ("reps", int)]
            pulse_program = np.zeros(len(reduced_instructions), dtype=dtypes)
            for j, instruction in enumerate(reduced_instructions):
                pulse_program[j]["half_period"] = instruction["half_period"]
                pulse_program[j]["reps"] = instruction["reps"]
            group.create_dataset(
                f"PULSE_PROGRAM_{i}", compression=compiler.compression, data=pulse_program
            )
