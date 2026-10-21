#####################################################################
#                                                                   #
# /labscript_devices/DummyPseudoclock/labscript_devices.py          #
#                                                                   #
# Copyright 2017, Christopher Billington                            #
#                                                                   #
# This file is part of labscript_devices, in the labscript suite    #
# (see http://labscriptsuite.org), and is licensed under the        #
# Simplified BSD License. See the license.txt file in the root of   #
# the project for the full license.                                 #
#                                                                   #
#####################################################################

from labscript import (
    PseudoclockDevice,
    Pseudoclock,
    ClockLine,
    compiler,
    LabscriptError,
)
import numpy as np


class DummyPseudoclock(PseudoclockDevice):
    """A pseudoclock without hardware, for testing BLACS and labscript.

    A shot can use it as its only device.
    """

    description = 'Dummy pseudoclock'
    clock_limit = 10e6
    clock_resolution = 25e-9
    trigger_delay = 350e-9
    wait_delay = 2.5e-6
    allowed_children = [Pseudoclock]
    max_pseudoclocks = 1
    max_instructions = 1e5

    def __init__(
        self, name='dummy_pseudoclock', BLACS_connection='dummy_connection', **kwargs
    ):
        """
        Parameters
        ----------
        name : str, optional
            Python variable name of the device; ``'dummy_pseudoclock'`` by default.
        BLACS_connection : str, optional
            Connection string BLACS shows on the device's tab; ``'dummy_connection'``
            by default. It must not be empty, or BLACS makes no tab for the device.
            The device has no hardware, so nothing else uses it.
        **kwargs
            Passed to :class:`~labscript.PseudoclockDevice`, except `trigger_device`
            and `trigger_connection`, which are not accepted: this is always the
            master pseudoclock.
        """
        self.BLACS_connection = BLACS_connection
        PseudoclockDevice.__init__(self, name, None, None, **kwargs)
        self._pseudoclock = Pseudoclock(
            name=f'{name}_pseudoclock',
            pseudoclock_device=self,
            connection='pseudoclock',
            max_clock_lines=1,
        )
        # The runviewer parser finds the clock line by its connection, 'internal'.
        self._clock_line = ClockLine(
            name=f'{name}_clock_line',
            pseudoclock=self.pseudoclock,
            connection='internal',
        )

    @property
    def pseudoclock(self):
        """The pseudoclock the device creates."""
        return self._pseudoclock

    @property
    def clockline(self):
        """The clock line the device creates, the parent of the devices it clocks."""
        return self._clock_line

    def generate_code(self, hdf5_file):
        """Write PULSE_PROGRAM, rows of period and reps, to the shot file."""
        PseudoclockDevice.generate_code(self, hdf5_file)
        group = self.init_device_group(hdf5_file)

        # Merge consecutive instructions of the same period, ignoring their
        # enabled_clocks: there is only one clock line.
        reduced_instructions = []
        for instruction in self.pseudoclock.clock:
            if instruction == 'WAIT':
                # A period of 0 with 1 rep is a wait.
                reduced_instructions.append({'period': 0, 'reps': 1})
                continue
            reps = instruction['reps']
            # The period is in whole ticks of clock_resolution.
            period = self.quantise_to_pseudoclock(instruction['step'], ticks=True)
            if reduced_instructions and reduced_instructions[-1]['period'] == period:
                reduced_instructions[-1]['reps'] += reps
            else:
                reduced_instructions.append({'period': period, 'reps': reps})
        # A period of 0 with 0 reps is the stop instruction.
        reduced_instructions.append({'period': 0, 'reps': 0})
        if len(reduced_instructions) > self.max_instructions:
            raise LabscriptError(
                f"{self.description} {self.name} has too many instructions: it has "
                f"{len(reduced_instructions)} and can support only "
                f"{int(self.max_instructions)}. Reduce the number of waits and "
                "clock-period changes."
            )
        dtypes = [('period', int), ('reps', int)]
        pulse_program = np.zeros(len(reduced_instructions), dtype=dtypes)
        for i, instruction in enumerate(reduced_instructions):
            pulse_program[i]['period'] = instruction['period']
            pulse_program[i]['reps'] = instruction['reps']
        group.create_dataset(
            'PULSE_PROGRAM', compression=compiler.compression, data=pulse_program
        )
