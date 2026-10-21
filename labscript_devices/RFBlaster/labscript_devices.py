#####################################################################
#                                                                   #
# /labscript_devices/RFBlaster/labscript_devices.py                 #
#                                                                   #
# Copyright 2013, Monash University                                 #
#                                                                   #
# This file is part of labscript_devices, in the labscript suite    #
# (see http://labscriptsuite.org), and is licensed under the        #
# Simplified BSD License. See the license.txt file in the root of   #
# the project for the full license.                                 #
#                                                                   #
#####################################################################
import os
from labscript import (
    PseudoclockDevice, Pseudoclock, ClockLine, IntermediateDevice, DDS, compiler,
    startupinfo, LabscriptError, set_passed_properties, renamed_keyword,
)
import numpy as np


class RFBlaster(PseudoclockDevice):
    """An RFBlaster board: a pseudoclock with two DDS outputs."""

    description = 'RF Blaster Rev1.1'
    clock_limit = 500e3
    clock_resolution = 13.33333333333333333333e-9
    allowed_children = [Pseudoclock]
    max_pseudoclocks = 1

    trigger_delay = 873.75e-6
    wait_delay = trigger_delay

    @set_passed_properties()
    def __init__(self, name, host=None, trigger_device=None, trigger_connection=None, **kwargs):
        """
        Parameters
        ----------
        name : str
            Python variable name of the device.
        host : str
            IP address of the board's web server, in dotted form such as
            ``'192.168.0.5'``; a host name is not accepted. BLACS contacts it on port
            8080. Required, though it defaults to ``None``: the deprecated keyword
            `ip_address` is accepted in its place.
        trigger_device : :class:`~labscript.IntermediateDevice`, optional
            Device that sends the hardware start trigger. An RFBlaster must be a
            secondary pseudoclock, since its BLACS tab cannot start a shot.
        trigger_connection : str, optional
            Output of `trigger_device` wired to the board's hardware trigger input.
        **kwargs
            Passed to :class:`~labscript.PseudoclockDevice`.
        """
        # LEGACY IP_ADDRESS KEYWORD COMPATIBILITY. DEPRECATED CODE, WILL BE REMOVED.
        host = renamed_keyword(kwargs, 'ip_address', 'host', host, 'RFBlaster', stacklevel=4)
        if host is None:
            raise LabscriptError(
                f'RFBlaster {name} needs the host of its board. Pass its IP address as host.'
            )
        PseudoclockDevice.__init__(self, name, trigger_device, trigger_connection, **kwargs)
        self.BLACS_connection = host

        self._pseudoclock = Pseudoclock(f'{name}_pseudoclock', self, 'clock', max_clock_lines=1)
        self._clock_line = ClockLine(f'{name}_clock_line', self.pseudoclock, 'internal')
        # The board's DDSs connect to this device, which hangs from the internal clock line.
        self._direct_output_device = RFBlasterDirectOutputs(
            f'{name}_direct_output_device', self._clock_line
        )

    @property
    def pseudoclock(self):
        """The board's pseudoclock."""
        return self._pseudoclock

    @property
    def direct_outputs(self):
        """The device the board's two DDSs connect to, on ``'dds 0'`` and ``'dds 1'``."""
        return self._direct_output_device

    def generate_code(self, hdf5_file):
        """Write the output tables, and each DDS's assembly and binary, to the shot file."""
        from rfblaster import caspr
        import rfblaster.rfjuice
        rfjuice_folder = os.path.dirname(rfblaster.rfjuice.__file__)

        import rfblaster.rfjuice.const as c
        from rfblaster.rfjuice.cython.make_diff_table import make_diff_table
        from rfblaster.rfjuice.cython.compile import compileD
        import tempfile
        from subprocess import Popen, PIPE

        # This generates the pseudoclock's times, which the tables below are built on.
        PseudoclockDevice.generate_code(self, hdf5_file)
        dtypes = [
            ('time', float),
            ('amp0', float), ('freq0', float), ('phase0', float),
            ('amp1', float), ('freq1', float), ('phase1', float),
        ]

        times = self.pseudoclock.times[self._clock_line]

        data = np.zeros(len(times), dtype=dtypes)
        data['time'] = times
        for dds in self.direct_outputs.child_devices:
            prefix, connection = dds.connection.split()
            data[f'freq{connection}'] = dds.frequency.raw_output
            data[f'amp{connection}'] = dds.amplitude.raw_output
            data[f'phase{connection}'] = dds.phase.raw_output
        group = self.init_device_group(hdf5_file)
        group.create_dataset('TABLE_DATA', compression=compiler.compression, data=data)

        quantised_dtypes = [
            ('time', np.int64),
            ('amp0', np.int32), ('freq0', np.int32), ('phase0', np.int32),
            ('amp1', np.int32), ('freq1', np.int32), ('phase1', np.int32),
        ]

        quantised_data = np.zeros(len(times), dtype=quantised_dtypes)
        quantised_data['time'] = np.array(c.tT*1e6*data['time']+0.5)
        for dds in self.direct_outputs.child_devices:
            prefix, connection = dds.connection.split()
            # The board's range: 0 Hz off to 350 MHz, and amplitude to its full code;
            # a phase wraps, as NovaTechDDS9M's does
            quantised_data[f'freq{connection}'], _ = dds.quantise_channel(
                'frequency', c.fF*1e-6, limits=(0, 350e6), dtype=np.int32
            )
            quantised_data[f'amp{connection}'], _ = dds.quantise_channel(
                'amplitude', 2**c.bitsA - 1, limits=(0, 1), dtype=np.int32
            )
            quantised_data[f'phase{connection}'], _ = dds.quantise_channel(
                'phase', c.pP, period=360, dtype=np.int32
            )
        group.create_dataset(
            'QUANTISED_DATA', compression=compiler.compression, data=quantised_data
        )
        # Generate some assembly code and compile it to machine code:
        assembly_group = group.create_group('ASSEMBLY_CODE')
        binary_group = group.create_group('BINARY_CODE')
        diff_group = group.create_group('DIFF_TABLES')
        # The times of the triggers that start the board and resume it after each wait,
        # quantised like the table's times.
        quantised_trigger_times = np.array(
            [c.tT*1e6*t + 0.5 for t in self.trigger_times], dtype=np.int64
        )
        for dds in range(2):
            abs_table = np.zeros((len(times), 4), dtype=np.int64)
            abs_table[:, 0] = quantised_data['time']
            abs_table[:, 1] = quantised_data[f'amp{dds}']
            abs_table[:, 2] = quantised_data[f'freq{dds}']
            abs_table[:, 3] = quantised_data[f'phase{dds}']

            # split up the table into chunks delimited by trigger times:
            abs_tables = []
            for i, t in enumerate(quantised_trigger_times):
                subtable = abs_table[abs_table[:, 0] >= t]
                try:
                    next_trigger_time = quantised_trigger_times[i+1]
                except IndexError:
                    # No next trigger time
                    pass
                else:
                    subtable = subtable[subtable[:, 0] < next_trigger_time]
                subtable[:, 0] -= t
                abs_tables.append(subtable)

            diff_tables = [make_diff_table(tab) for tab in abs_tables]
            with tempfile.NamedTemporaryFile(delete=False) as f:
                temp_assembly_filepath = f.name
            with tempfile.NamedTemporaryFile(delete=False) as f:
                temp_binary_filepath = f.name

            try:
                with open(temp_assembly_filepath, 'w') as assembly_file:
                    for i, dtab in enumerate(diff_tables):
                        compileD(dtab, assembly_file, init=(i == 0),
                                 jump_to_start=(i == 0),
                                 jump_from_end=False,
                                 close_end=(i == len(diff_tables) - 1),
                                 local_loop_pre=str(i),
                                 set_defaults=(i == 0))
                with open(temp_assembly_filepath) as assembly_file:
                    assembly_code = assembly_file.read()
                    assembly_group.create_dataset(f'DDS{dds}', data=assembly_code)
                    for i, diff_table in enumerate(diff_tables):
                        diff_group.create_dataset(
                            f'DDS{dds}_difftable{i}',
                            compression=compiler.compression,
                            data=diff_table,
                        )
                compilation = Popen([caspr, temp_assembly_filepath, temp_binary_filepath],
                                    stdout=PIPE, stderr=PIPE, cwd=rfjuice_folder,
                                    startupinfo=startupinfo)
                stdout, stderr = compilation.communicate()
                if compilation.returncode:
                    print(stdout)
                    raise LabscriptError(
                        f'RFBlaster compilation of DDS {dds} exited with code '
                        f'{compilation.returncode}.\n\n'
                        f'Stdout was:\n {stdout}\nStderr was:\n{stderr}\n'
                    )
                with open(temp_binary_filepath, 'rb') as binary_file:
                    binary_data = binary_file.read()
                # np.bytes_ is a fixed-length string. h5py stores Python bytes as a
                # variable-length string, which cannot contain embedded nulls, and the
                # binary can contain them.
                binary_group.create_dataset(f'DDS{dds}', data=np.bytes_(binary_data))
            finally:
                os.remove(temp_assembly_filepath)
                os.remove(temp_binary_filepath)


class RFBlasterDirectOutputs(IntermediateDevice):
    """The device an RFBlaster's two DDSs connect to, on ``'dds 0'`` and ``'dds 1'``."""

    allowed_children = [DDS]
    clock_limit = RFBlaster.clock_limit
    description = 'RFBlaster Direct Outputs'

    def add_device(self, device):
        try:
            prefix, number = device.connection.split()
            assert int(number) in range(2)
            assert prefix == 'dds'
        except Exception:
            raise LabscriptError(
                f"The connection of {device.name} must be 'dds 0' or 'dds 1', "
                f"not {device.connection!r}."
            )

        if isinstance(device, DDS):
            # A digital line as this DDS's gate makes no sense.
            if device.gate is not None:
                raise LabscriptError(
                    f'You cannot specify a digital gate for {device.name}, a DDS '
                    f'connected to {self.name}. Remove its digital_gate.'
                )

        IntermediateDevice.add_device(self, device)
