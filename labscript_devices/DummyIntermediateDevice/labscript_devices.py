#####################################################################
#                                                                   #
# /labscript_devices/DummyIntermediateDevice/labscript_devices.py   #
#                                                                   #
# Copyright 2013, Monash University                                 #
#                                                                   #
# This file is part of labscript_devices, in the labscript suite    #
# (see http://labscriptsuite.org), and is licensed under the        #
# Simplified BSD License. See the license.txt file in the root of   #
# the project for the full license.                                 #
#                                                                   #
#####################################################################

"""
Overview
~~~~~~~~

A dummy intermediate device, for testing BLACS and labscript. Attached to a
clock line of a pseudoclock device, it tests the pseudoclock's behaviour
without a real intermediate device.

Any number of :class:`~labscript.DigitalOut` and :class:`~labscript.AnalogOut`
outputs, or subclasses of them, can be attached; a device of any other class
raises ``LabscriptError`` when attached. The device writes the raw values of its
outputs, one row for each clock tick, to the ``OUTPUTS`` table of its group in
the shot file; with no outputs it writes no table.

Usage
~~~~~

.. code-block:: python

    from labscript import *

    from labscript_devices.DummyPseudoclock.labscript_devices import DummyPseudoclock
    from labscript_devices.DummyIntermediateDevice.labscript_devices import DummyIntermediateDevice

    DummyPseudoclock(name='dummy_clock', BLACS_connection='dummy')
    DummyIntermediateDevice(name='dummy_device', BLACS_connection='dummy2',
                            parent_device=dummy_clock.clockline)

    DigitalOut(name='do1', parent_device=dummy_device, connection='dummy_do1')
    DigitalOut(name='do2', parent_device=dummy_device, connection='dummy_do2')

    start()
    stop(1)

Detailed Documentation
~~~~~~~~~~~~~~~~~~~~~~

"""

from labscript import IntermediateDevice, DigitalOut, AnalogOut, compiler
import numpy as np


class DummyIntermediateDevice(IntermediateDevice):
    """An intermediate device without hardware, for testing BLACS and labscript."""

    description = 'Dummy IntermediateDevice'
    clock_limit = 1e6

    # generate_code chooses a dtype for each of these classes: one added here needs
    # a dtype there too.
    allowed_children = [DigitalOut, AnalogOut]

    def __init__(
        self, name, parent_device, BLACS_connection='dummy_connection', **kwargs
    ):
        """
        Parameters
        ----------
        name : str
            Python variable name of the device.
        parent_device : :class:`~labscript.ClockLine`
            Clock line that clocks the device, such as a DummyPseudoclock's
            `clockline`.
        BLACS_connection : str, optional
            Connection string BLACS shows on the device's tab; ``'dummy_connection'``
            by default. It must not be empty, or BLACS makes no tab for the device.
            The device has no hardware, so nothing else uses it.
        **kwargs
            Passed to :class:`~labscript.IntermediateDevice`.
        """
        self.BLACS_connection = BLACS_connection
        IntermediateDevice.__init__(self, name, parent_device, **kwargs)

    def generate_code(self, hdf5_file):
        """Write OUTPUTS, a row for each clock tick and a column for each output."""
        IntermediateDevice.generate_code(self, hdf5_file)
        group = self.init_device_group(hdf5_file)

        clockline = self.parent_device
        pseudoclock = clockline.parent_device
        times = pseudoclock.times[clockline]

        dtypes = []
        for device in self.child_devices:
            if isinstance(device, DigitalOut):
                device_dtype = np.int8
            elif isinstance(device, AnalogOut):
                device_dtype = np.float64
            dtypes.append((device.name, device_dtype))
        # h5py cannot write a table whose rows have no fields.
        if not dtypes:
            return

        out_table = np.zeros(len(times), dtype=dtypes)
        for device in self.child_devices:
            out_table[device.name][:] = device.raw_output

        group.create_dataset(
            'OUTPUTS', compression=compiler.compression, data=out_table
        )
