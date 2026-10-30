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
        if not self.child_devices:
            return

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
