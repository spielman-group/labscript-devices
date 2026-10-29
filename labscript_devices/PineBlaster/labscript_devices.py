#####################################################################
#                                                                   #
# /labscript_devices/PineBlaster/labscript_devices.py               #
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
    PseudoclockDevice,
    Pseudoclock,
    ClockLine,
    compiler,
    LabscriptError,
    set_passed_properties,
)

import numpy as np


class PineBlaster(PseudoclockDevice):
    """A PineBlaster pseudoclock on a serial port, with one clock line, `clockline`."""

    description = 'PineBlaster'
    clock_limit = 10e6
    clock_resolution = 25e-9
    clock_type = 'fast clock'
    # Measured by Phil Starkey on 2015/9/24
    trigger_delay = 350e-9
    wait_delay = 2.5e-6
    allowed_children = [Pseudoclock]
    max_pseudoclocks = 1

    max_instructions = 15000

    @set_passed_properties(
        property_names={"connection_table_properties": ["com_port"]}
    )
    def __init__(
        self,
        name,
        trigger_device=None,
        trigger_connection=None,
        com_port='COM1',
        **kwargs,
    ):
        """
        Parameters
        ----------
        name : str
            Python variable name of the device.
        trigger_device : :class:`~labscript.IntermediateDevice`, optional
            Device whose output sends the hardware start trigger when this is a
            secondary pseudoclock. If `None`, the default, this is the master
            pseudoclock.
        trigger_connection : str, optional
            Output of `trigger_device` wired to the board's hardware trigger input;
            required if `trigger_device` is given.
        com_port : str, optional
            Serial port the board is on, such as ``'COM7'``; ``'COM1'`` by default.
        **kwargs
            Passed to :class:`~labscript.PseudoclockDevice`.
        """
        if 'usbport' in kwargs:
            raise LabscriptError(f"PineBlaster {name}: the keyword usbport is com_port.")
        self.com_port = com_port
        PseudoclockDevice.__init__(self, name, trigger_device, trigger_connection, **kwargs)
        self.BLACS_connection = com_port

        self._pseudoclock = Pseudoclock(
            f'{name}_pseudoclock', self, 'clock', max_clock_lines=1
        )
        # The board's one output, 'internal', is this clock line; its tab, worker and
        # runviewer parser find it by that name.
        self._clock_line = ClockLine(f'{name}_clock_line', self.pseudoclock, 'internal')

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
        """Write the pulse program to the shot file, as PULSE_PROGRAM rows of period and reps."""
        PseudoclockDevice.generate_code(self, hdf5_file)
        group = self.init_device_group(hdf5_file)

        # Merge consecutive instructions of the same period, to save room in the
        # instruction table.
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
                f"{self.max_instructions}. Reduce the number of waits and "
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
