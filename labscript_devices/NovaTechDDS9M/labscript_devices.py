#####################################################################
#                                                                   #
# /labscript_devices/NovaTechDDS9M/labscript_devices.py             #
#                                                                   #
# Copyright 2013, Monash University                                 #
#                                                                   #
# This file is part of the module labscript_devices, in the         #
# labscript suite (see http://labscriptsuite.org), and is           #
# licensed under the Simplified BSD License. See the license.txt    #
# file in the root of the project for the full license.             #
#                                                                   #
#####################################################################

from labscript import IntermediateDevice, DDS, StaticDDS, Device, compiler, LabscriptError, set_passed_properties
from labscript_utils.unitconversions import NovaTechDDS9mFreqConversion, NovaTechDDS9mAmpConversion

import warnings

import numpy as np

# Each baud rate, with the command that sets the NovaTech to it.
bauds = {9600: b'Kb 78',
         19200: b'Kb 3c',
         38400: b'Kb 1e',
         57600: b'Kb 14',
         115200: b'Kb 0a'}

class NovaTechDDS9M(IntermediateDevice):
    """A NovaTech DDS9M with four DDS outputs; 'dds 2' and 'dds 3' cannot change during a shot."""
    description = 'NT-DDS9M'
    allowed_children = [DDS, StaticDDS]
    # A realistic estimate of the max clock rate: 100us for TS/pin10 processing to load
    # the next value into the buffer and 100ns pipeline delay on a pin 14 edge to update
    # the output values.
    clock_limit = 9990

    # Longer than the NovaTech's technical requirement, because the tri-state buffer or
    # similar electronics some groups put in front of its clock input might limit how
    # fast it can go. 1us is a compromise; a subclass or a monkey-patch can override it.
    minimum_clock_high_time = 1e-6

    @set_passed_properties(
        property_names={
            'connection_table_properties': [
                'com_port',
                'baud_rate',
                'default_baud_rate',
                'update_mode',
                'synchronous_first_line_repeat',
                'phase_mode',
            ]
        }
    )
    def __init__(
        self,
        name,
        parent_device,
        com_port="",
        baud_rate=115200,
        default_baud_rate=None,
        update_mode='synchronous',
        synchronous_first_line_repeat=False,
        phase_mode='continuous',
        **kwargs
    ):
        """
        Parameters
        ----------
        name : str
            Python variable name of the device.
        parent_device : :class:`~labscript.ClockLine`
            Clock line that clocks the device.
        com_port : str, optional
            Serial port of the NovaTech, such as ``'COM1'``; ``''`` by default.
        baud_rate : int, optional
            Baud rate BLACS switches the NovaTech to and programs it at: 9600, 19200,
            38400, 57600 or 115200; 115200 by default.
        default_baud_rate : int or None, optional
            Baud rate the NovaTech starts at, one of the values for `baud_rate`, or
            ``None``, the default, for none assumed. BLACS connects at it first, or
            at `baud_rate` if it is ``None``, and sets the NovaTech back to it on
            shutdown.
        update_mode : str, optional
            ``'synchronous'``, the default, has the NovaTech update its outputs by
            hardware on rising clock edges (BLACS sends ``I e``); ``'asynchronous'``
            leaves it in automatic update, which updates them on falling edges.
        synchronous_first_line_repeat : bool, optional
            Repeat the first line of the table in synchronous mode, as asynchronous
            mode always does; ``False`` by default. A simple delay line in front of
            the NovaTech's clock input seems to need it; the tristate driver described
            in the Novatech DDS 9m documentation, the way its manual says to clock it
            and so likely the most reliable, does not.
        phase_mode : str, optional
            ``'continuous'``, the default, or ``'aligned'``: the phase mode BLACS sets
            on the NovaTech, with ``m n`` or ``m a``.
        **kwargs
            Passed to :class:`~labscript.IntermediateDevice`.
        """
        IntermediateDevice.__init__(self, name, parent_device, **kwargs)
        self.BLACS_connection = f'{com_port},{baud_rate}'

        if not update_mode in ['synchronous', 'asynchronous']:
            raise LabscriptError(
                f"update_mode must be 'synchronous' or 'asynchronous', not {update_mode!r}."
            )

        if not baud_rate in bauds:
            raise LabscriptError(
                f"baud_rate must be one of {list(bauds)}, not {baud_rate!r}."
            )

        if not default_baud_rate in bauds and default_baud_rate is not None:
            raise LabscriptError(
                f"default_baud_rate must be one of {list(bauds)} or None (for no default), "
                f"not {default_baud_rate!r}."
            )

        if not phase_mode in ['aligned', 'continuous']:
            raise LabscriptError(
                f"phase_mode must be 'aligned' or 'continuous', not {phase_mode!r}."
            )

        self.update_mode = update_mode
        self.phase_mode = phase_mode
        self.synchronous_first_line_repeat = synchronous_first_line_repeat

    def add_device(self, device):
        # LEGACY 'channel n' CONNECTION COMPATIBILITY. DEPRECATED CODE, WILL BE REMOVED.
        if device.connection.startswith('channel '):
            connection = 'dds ' + device.connection.split()[-1]
            warnings.warn(
                f"{device.name} connects as {device.connection!r}, not {connection!r}. "
                "That legacy form will be removed.", FutureWarning, stacklevel=4
            )
            device.connection = connection
        Device.add_device(self, device)
        # The Novatech doesn't support 0Hz output; set the default frequency of the DDS to 0.1 Hz:
        device.frequency.default_value = 0.1

    def get_default_unit_conversion_classes(self, device):
        """Return the frequency, amplitude and phase unit conversion classes, None for phase."""
        return NovaTechDDS9mFreqConversion, NovaTechDDS9mAmpConversion, None

    # Each takes a DDS's output, or a subclass's transformed copy of it, and the
    # DDS, and returns the output in the device's units, with the scale: 0.1 Hz,
    # 1/45.5111 of a degree and 1/1023 of full amplitude.

    def quantise_freq(self, data, device):
        return device.quantise_channel(device.frequency, 10, values=data, limits=(0.1, 171e6), dtype=np.uint32)

    def quantise_phase(self, data, device):
        return device.quantise_channel(device.phase, 45.511111111111113, values=data, period=360, dtype=np.uint16)

    def quantise_amp(self, data, device):
        return device.quantise_channel(device.amplitude, 1023, values=data, limits=(0, 1), dtype=np.uint16)

    def generate_code(self, hdf5_file):
        DDSs = {}
        for output in self.child_devices:
            # Check that the instructions will fit into RAM; the -2 includes space for
            # dummy instructions.
            if isinstance(output, DDS) and len(output.frequency.raw_output) > 16384 - 2:
                raise LabscriptError(
                    f"{self.name} can only support 16382 instructions, but {output.name} "
                    f"has {len(output.frequency.raw_output)}. Decrease the sample rates of "
                    f"devices on the same clock, or connect {self.name} to a different "
                    "pseudoclock."
                )
            try:
                prefix, channel = output.connection.split()
                channel = int(channel)
            except:
                raise LabscriptError(
                    f"{output.description} {output.name} has invalid connection string: "
                    f"{output.connection!r}. Format must be 'dds n' with n from 0 to 3."
                )
            DDSs[channel] = output
        for connection in DDSs:
            dds = DDSs[connection]
            if connection in range(4):
                dds.frequency.raw_output, dds.frequency.scale_factor = self.quantise_freq(dds.frequency.raw_output, dds)
                dds.phase.raw_output, dds.phase.scale_factor = self.quantise_phase(dds.phase.raw_output, dds)
                dds.amplitude.raw_output, dds.amplitude.scale_factor = self.quantise_amp(dds.amplitude.raw_output, dds)
            else:
                raise LabscriptError(
                    f"{dds.description} {dds.name} has invalid connection string: "
                    f"{dds.connection!r}. Format must be 'dds n' with n from 0 to 3."
                )

        dtypes = [('freq%d'%i,np.uint32) for i in range(2)] + \
                 [('phase%d'%i,np.uint16) for i in range(2)] + \
                 [('amp%d'%i,np.uint16) for i in range(2)]

        static_dtypes = [('freq%d'%i,np.uint32) for i in range(2,4)] + \
                        [('phase%d'%i,np.uint16) for i in range(2,4)] + \
                        [('amp%d'%i,np.uint16) for i in range(2,4)]

        clockline = self.parent_clock_line
        pseudoclock = clockline.parent_device
        times = pseudoclock.times[clockline]

        out_table = np.zeros(len(times),dtype=dtypes)
        out_table['freq0'].fill(1)
        out_table['freq1'].fill(1)

        static_table = np.zeros(1, dtype=static_dtypes)
        static_table['freq2'].fill(1)
        static_table['freq3'].fill(1)

        for connection in range(2):
            if not connection in DDSs:
                continue
            dds = DDSs[connection]
            out_table['freq%d'%connection][:] = dds.frequency.raw_output
            out_table['amp%d'%connection][:] = dds.amplitude.raw_output
            out_table['phase%d'%connection][:] = dds.phase.raw_output
        for connection in range(2,4):
            if not connection in DDSs:
                continue
            dds = DDSs[connection]
            static_table['freq%d'%connection] = dds.frequency.raw_output[0]
            static_table['amp%d'%connection] = dds.amplitude.raw_output[0]
            static_table['phase%d'%connection] = dds.phase.raw_output[0]

        if self.update_mode == 'asynchronous' or self.synchronous_first_line_repeat:
            # Repeat the first line, or we are one step ahead in the table from the start of
            # a run. Asynchronous mode outputs it before the first trigger from the master
            # clock; a simple delay line in synchronous mode also seems to need it.
            out_table = np.concatenate([out_table[0:1], out_table])

        grp = self.init_device_group(hdf5_file)
        grp.create_dataset('TABLE_DATA',compression=compiler.compression,data=out_table)
        grp.create_dataset('STATIC_DATA',compression=compiler.compression,data=static_table)
        self.set_property('frequency_scale_factor', 10, location='device_properties')
        self.set_property('amplitude_scale_factor', 1023, location='device_properties')
        self.set_property('phase_scale_factor', 45.511111111111113, location='device_properties')
