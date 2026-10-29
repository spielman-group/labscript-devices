#####################################################################
#                                                                   #
# /labscript_devices/PhaseMatrixQuickSyn/labscript_devices.py       #
#                                                                   #
# Copyright 2013, Monash University                                 #
#                                                                   #
# This file is part of labscript_devices, in the labscript suite    #
# (see http://labscriptsuite.org), and is licensed under the        #
# Simplified BSD License. See the license.txt file in the root of   #
# the project for the full license.                                 #
#                                                                   #
#####################################################################

import numpy as np

from labscript import (
    Device,
    StaticDDS,
    StaticAnalogQuantity,
    StaticDigitalOut,
    compiler,
    LabscriptError,
    set_passed_properties,
)
import labscript_utils.properties


class QuickSynDDS(StaticDDS):
    """The QuickSyn's output: a static frequency and gate, with no amplitude or phase."""
    description = 'PhaseMatrix QuickSyn DDS'
    allowed_children = [StaticAnalogQuantity, StaticDigitalOut]
    generation = 2

    @set_passed_properties()
    def __init__(self, name, parent_device, connection, freq_limits=None, freq_conv_class=None, freq_conv_params={}, **kwargs):
        """
        Parameters
        ----------
        name : str
            Python variable name of the device.
        parent_device : :class:`PhaseMatrixQuickSyn`
            The synthesiser this is the output of.
        connection : str
            ``'dds 0'``, the synthesiser's only output.
        freq_limits : tuple of float, optional
            `(minimum, maximum)` allowed for the frequency, in Hz, checked when it
            is set; ``None`` by default. A compile also refuses a frequency outside
            0.5 to 10 GHz.
        freq_conv_class : optional
            Unit conversion class for the frequency, applied when `setfreq` is given
            `units`; ``None`` by default.
        freq_conv_params : dict, optional
            Keyword arguments for `freq_conv_class`; empty by default.
        **kwargs
            Passed to :class:`~labscript.Device`.
        """
        # Not StaticDDS.__init__, which would create amplitude and phase channels too.
        Device.__init__(self, name, parent_device, connection, **kwargs)
        self.frequency = StaticAnalogQuantity(self.name + '_freq', self, 'freq', freq_limits, freq_conv_class, freq_conv_params)
        # The lowest frequency quantise_freq accepts, in Hz, for a shot that sets none.
        self.frequency.default_value = 0.5e9
        self.gate = StaticDigitalOut(self.name + '_gate', self, 'gate')

    def setamp(self, value, units=None):
        """Raise :class:`~labscript.LabscriptError`: the QuickSyn has no amplitude control."""
        raise LabscriptError(
            f'{self.name} has no amplitude control: QuickSynDDS sets only a frequency, with setfreq.'
        )

    def setphase(self, value, units=None):
        """Raise :class:`~labscript.LabscriptError`: the QuickSyn has no phase control."""
        raise LabscriptError(
            f'{self.name} has no phase control: QuickSynDDS sets only a frequency, with setfreq.'
        )

    def enable(self):
        """Set the gate high for the whole shot. Takes no `t`, unlike StaticDDS's."""
        self.gate.go_high()

    def disable(self):
        """Set the gate low for the whole shot. Takes no `t`, unlike StaticDDS's.

        The worker does not apply the gate: it turns the output on for every shot.
        """
        self.gate.go_low()


class PhaseMatrixQuickSyn(Device):
    """A PhaseMatrix QuickSyn frequency synthesiser, which has no parent device and one :class:`QuickSynDDS`."""
    description = 'QuickSyn Frequency Synthesiser'
    allowed_children = [QuickSynDDS]
    generation = 0

    @set_passed_properties()
    def __init__(self, name, com_port, **kwargs):
        """
        Parameters
        ----------
        name : str
            Python variable name of the device.
        com_port : str
            Serial port of the synthesiser, such as ``'COM1'``.
        **kwargs
            Passed to :class:`~labscript.Device`.
        """
        Device.__init__(self, name, None, None, **kwargs)
        self.BLACS_connection = com_port

    def quantise_freq(self, data, device):
        """Return `data`, a DDS's frequencies in Hz, in mHz as uint64, with the scale 1000."""
        return device.quantise_channel(device.frequency, 1000, values=data, limits=(0.5e9, 10e9), dtype=np.uint64)

    def generate_code(self, hdf5_file):
        """Write the frequency, in mHz, and the gate to the shot file's STATIC_DATA."""
        if len(self.child_devices) != 1:
            raise LabscriptError(
                f"{self.description} {self.name} needs exactly one QuickSynDDS, "
                f"with the connection 'dds 0', but has {len(self.child_devices)}."
            )
        for output in self.child_devices:
            try:
                prefix, channel = output.connection.split()
                channel = int(channel)
            except:
                raise LabscriptError(
                    f"{output.description} {output.name} has invalid connection string: "
                    f"{output.connection!r}. Format must be 'dds 0'."
                )
            if channel != 0:
                raise LabscriptError(
                    f"{output.description} {output.name} has invalid connection string: "
                    f"{output.connection!r}. Format must be 'dds 0'."
                )
            dds = output
        # A pseudoclock calls these on its outputs, and this device has none, so
        # they finish the static outputs here, defining their raw_output.
        ignore = dds.frequency.get_change_times()
        dds.frequency.make_timeseries([])
        dds.frequency.expand_timeseries()

        ignore = dds.gate.get_change_times()
        dds.gate.make_timeseries([])
        dds.gate.expand_timeseries()

        dds.frequency.raw_output, dds.frequency.scale_factor = self.quantise_freq(dds.frequency.raw_output, dds)
        static_dtypes = [('freq0', np.uint64)] + \
                        [('gate0', np.uint16)]
        static_table = np.zeros(1, dtype=static_dtypes)
        static_table['freq0'].fill(1)
        static_table['freq0'] = dds.frequency.raw_output[0]
        static_table['gate0'] = dds.gate.raw_output[0]
        grp = self.init_device_group(hdf5_file)
        grp.create_dataset('STATIC_DATA', compression=compiler.compression, data=static_table)
        self.set_property('frequency_scale_factor', 1000, location='device_properties')
