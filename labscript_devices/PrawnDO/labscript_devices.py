#####################################################################
#                                                                   #
# /labscript_devices/PrawnDO/labscript_devices.py                   #
#                                                                   #
# Copyright 2023, Philip Starkey, Carter Turnbaugh, Patrick Miller  #
#                                                                   #
# This file is part of labscript_devices, in the labscript suite    #
# (see http://labscriptsuite.org), and is licensed under the        #
# Simplified BSD License. See the license.txt file in the root of   #
# the project for the full license.                                 #
#                                                                   #
#####################################################################
from labscript import (
    IntermediateDevice,
    PseudoclockDevice,
    Pseudoclock,
    ClockLine,
    DigitalOut,
    Trigger,
    bitfield,
    set_passed_properties,
    LabscriptError
)
import numpy as np


class _PrawnDigitalOutputs(IntermediateDevice):
    """The 16 digital outputs of a PrawnDO, connected as 'do0' to 'do15'."""

    allowed_children = [DigitalOut]

    allowed_channels = tuple(range(16))

    def __init__(self, name, parent_device,
                 **kwargs):
        IntermediateDevice.__init__(self, name, parent_device, **kwargs)
        self.connected_channels = []

    def add_device(self, device):
        conn = device.connection
        chan = int(conn.split('do')[-1])

        if chan not in self.allowed_channels:
            raise LabscriptError(
                f"{conn!r} is not a PrawnDO output. Connect digital outputs as "
                "'do0' to 'do15'."
            )
        if chan in self.connected_channels:
            raise LabscriptError(
                f"Channel {conn} is already connected to {self.name}. "
                "Connect each digital output to its own channel."
            )

        self.connected_channels.append(chan)
        super().add_device(device)


class PrawnDO(PseudoclockDevice):
    """A PrawnDO board with 16 digital outputs, connected to its `outputs` as 'do0' to 'do15'."""

    description = "PrawnDO device"

    # Specs for a 100 MHz system clock; __init__ scales them to clock_frequency.
    clock_limit = 1 / 100e-9
    "Maximum allowable clock rate"
    clock_resolution = 10e-9
    "Minimum resolvable unit of time, corresponds to system clock period."
    minimum_duration = 50e-9
    "Minimum time between updates on the outputs."
    wait_delay = 50e-9
    "Minimum required length of wait before a retrigger can be detected."
    input_response_time = 50e-9
    "Time between hardware trigger and output starting."
    trigger_delay = 50e-9
    trigger_minimum_duration = 160e-9
    "Minimum required duration of hardware trigger. A fairly large over-estimate."

    allowed_children = [Pseudoclock]
    allowed_boards = ['pico1', 'pico2']

    max_instructions_map = {'pico1' : 30000, 'pico2' : 60000}
    """Maximum number of instructions in the pulse program for each pico board."""

    max_frequency_map = {'pico1' : 133e6, 'pico2' : 150e6}

    max_reps = 2**32 - 1
    """Largest number of clock cycles for which one instruction holds its output.
    The firmware stores reps as a 32-bit unsigned integer."""

    @set_passed_properties(
        property_names={
            'connection_table_properties': [
                'com_port',
                'pico_board',
            ],
            'device_properties': [
                'clock_frequency',
                'external_clock',
                'clock_limit',
                'clock_resolution',
                'minimum_duration',
                'input_response_time',
                'trigger_delay',
                'trigger_minimum_duration',
                'wait_delay',
            ]
        }
    )
    def __init__(self, name,
                 trigger_device=None,
                 trigger_connection=None,
                 clock_line=None,
                 com_port='COM1',
                 pico_board='pico1',
                 clock_frequency=100e6,
                 external_clock=False,
                 **kwargs
                ):
        """
        Parameters
        ----------
        name : str
            Python variable name of the device.
        trigger_device : :class:`~labscript.IntermediateDevice`, optional
            Device that sends the hardware start trigger when this is a secondary
            pseudoclock. Not with `clock_line`.
        trigger_connection : str, optional
            Output of `trigger_device` wired to the hardware trigger input.
        clock_line : :class:`~labscript.ClockLine`, optional
            Clock line, such as a PrawnBlaster's, that triggers this device
            directly, through an internal intermediate device. Not with
            `trigger_device`.
        com_port : str, optional
            Serial port the OS assigned, such as ``'COM1'``, the default.
        pico_board : str, optional
            ``'pico1'``, the default, or ``'pico2'``. labscript allows a pulse
            program of 30000 instructions on pico1 and 60000 on pico2.
        clock_frequency : float, optional
            System clock frequency in Hz; ``100e6`` by default, at most 133 MHz for
            pico1 and 150 MHz for pico2. The class's timings are for 100 MHz and
            scale with it.
        external_clock : bool, optional
            Take the clock from an external signal on pin 20, whose frequency is
            `clock_frequency`; ``False`` by default.
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

        self.max_instructions = self.max_instructions_map[self.pico_board]
        self.max_frequency = self.max_frequency_map[self.pico_board]

        if clock_frequency > self.max_frequency:
            raise ValueError(
                f"Clock frequency must be at most {int(self.max_frequency * 10**-6)} MHz "
                f"for {self.pico_board}."
            )

        self.external_clock = external_clock
        self.clock_frequency = clock_frequency
        # The class specs are for a 100 MHz clock; scale them by the ratio of the clock
        # periods, and the clock limit, a rate, the other way.
        if self.clock_frequency != 100e6:
            factor = 100e6/self.clock_frequency
            self.clock_limit /= factor
            self.clock_resolution *= factor
            self.minimum_duration *= factor
            self.wait_delay *= factor
            self.input_response_time *= factor
            self.trigger_delay *= factor
            self.trigger_minimum_duration *= factor

        if clock_line is not None and trigger_device is not None:
            raise LabscriptError("Provide only a trigger_device or a clock_line, not both")
        self.__intermediate = None
        if clock_line is not None:
            # An internal intermediate device on the clock line, with a trigger on it
            # that starts this device.
            self.__intermediate = _PrawnDOIntermediateDevice(f'{name:s}__intermediate',
                                                             clock_line)
            PseudoclockDevice.__init__(self, name, self.__intermediate, 'internal', **kwargs)
        else:
            # normal pseudoclock device triggering
            PseudoclockDevice.__init__(self, name, trigger_device, trigger_connection, **kwargs)

        # The pseudoclock and clock line that the digital outputs hang from.
        self.__pseudoclock = Pseudoclock(f'{name:s}__pseudoclock', self, '_', max_clock_lines=1)
        self.__clockline = ClockLine(f'{name:s}__clockline', self.__pseudoclock, '_')
        self.outputs = _PrawnDigitalOutputs(f'{name:s}__pod', self.__clockline)

        self.BLACS_connection = com_port

        self._initial_trigger_time = 0

    # These three defs keep initial_trigger_time at 0 when a clock_line triggers this
    # device through the internal intermediate device.
    @property
    def initial_trigger_time(self):
        return self._initial_trigger_time

    @initial_trigger_time.setter
    def initial_trigger_time(self, value):
        if value != 0 and self.__intermediate is not None:
            raise LabscriptError("You cannot set the initial trigger time when the PrawnDO is directly triggered by a clockline")
        self._initial_trigger_time = value

    def set_initial_trigger_time(self, *args, **kwargs):
        """Set the initial trigger time in seconds, unless `clock_line` triggers this device."""
        if self.__intermediate is not None:
            raise LabscriptError("You cannot set the initial trigger time when the PrawnDO is directly triggered by a clockline")
        return super().set_initial_trigger_time(*args, **kwargs)

    def add_device(self, device):
        if isinstance(device, Pseudoclock):
            super().add_device(device)
        elif isinstance(device, DigitalOut):
            raise LabscriptError(f"Digital outputs must be connected to {self.name:s}.outputs")
        else:
            raise LabscriptError(f"You have connected unsupported {device.name:s} (class {device.__class__}) "
                                 f"to {self.name:s}")

    def generate_code(self, hdf5_file):
        PseudoclockDevice.generate_code(self, hdf5_file)

        # The clock line ticks where the outputs change; the pseudoclock's clock
        # instructions also hold its waits.
        outputs = self.get_all_outputs()
        times = self.__pseudoclock.times[self.__clockline]
        instructions = self.__pseudoclock.clock
        if len(times) == 0:
            # No instructions: no PULSE_PROGRAM is written, and the worker does not
            # program the board.
            return

        # get where wait instructions should be added from clock instructions:
        # each goes before the tick it resumes on, counted in times, where a
        # ramp's instruction is many ticks and a wait none
        wait_idxs = []
        ticks = 0
        for instr in instructions:
            if instr == 'WAIT':
                wait_idxs.append(ticks)
            else:
                ticks += instr['reps']

        # Each DigitalOut's raw_output at each tick is its bit of the output word; an
        # unused pin stays low.
        bits = [np.zeros(len(times), dtype=np.uint16)] * 16
        for output in outputs:
            chan = int(output.connection.split('do')[-1])
            bits[chan] = np.asarray(output.raw_output, dtype = np.uint16)
        # Merge the 16 bit arrays into one array of 16-bit integers, bit n being do<n>.
        bit_sets = np.array(bitfield(bits, dtype=np.uint16))

        # reps is the time between changes, in clock cycles.
        reps = self.quantise_to_pseudoclock(np.diff(times), ticks=True)
        if reps.size and reps.max() > self.max_reps:
            i = int(np.argmax(reps))
            max_interval = self.max_reps * self.clock_resolution
            raise LabscriptError(
                f"{self.description} {self.name} has no output changes between "
                f"t={times[i]} s and t={times[i + 1]} s. This interval of "
                f"{times[i + 1] - times[i]} s is longer than the maximum of "
                f"{max_interval:.1f} s between instructions."
            )
        reps = reps.astype(np.uint32)

        # The final output is already in bit_sets. A reps of 0 holds it, and a second
        # row of reps 0, whose bit set is ignored, makes the pair a stop.
        reps = np.append(reps, 0)
        bit_sets = np.append(bit_sets, 0)
        reps = np.append(reps, 0)

        # Each wait is a row of reps 0 that outputs the bit set of the tick it resumes on.
        reps = np.insert(reps, wait_idxs, 0)
        bit_sets = np.insert(bit_sets, wait_idxs, bit_sets[wait_idxs])

        if reps.size > self.max_instructions:
            raise LabscriptError(
                f"{self.name} has {reps.size} instructions, but {self.pico_board} "
                f"supports only {self.max_instructions}. Reduce the number of output "
                "changes and waits."
            )

        group = hdf5_file['devices'].require_group(self.name)
        # The worker sends these bytes to the firmware's adm command as they are: six per
        # instruction, a little-endian 16-bit output word, then a 32-bit reps.
        dtype = np.dtype([('bit_sets', '<u2'),
                          ('reps', '<u4')])
        pulse_program = np.zeros(len(reps), dtype=dtype)
        pulse_program['bit_sets'] = bit_sets
        pulse_program['reps'] = reps
        group.create_dataset('PULSE_PROGRAM', data=pulse_program)


class _PrawnDOIntermediateDevice(IntermediateDevice):
    """The internal device between a clock line and the trigger that starts a PrawnDO."""

    description = "PrawnDO Internal Intermediate Device"

    allowed_children = [Trigger]
