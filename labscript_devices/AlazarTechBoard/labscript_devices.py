# A labscript device class for data acquisition boards made by Alazar Technologies Inc (ATS)
# Hacked up from NIboard.py by LDT 2017-01-26
#
# Copyright (c) Monash University 2017

import numpy as np

# Importing atsapi loads AlazarTech's SDK library, ATSApi.dll or libATSApi.so.
import labscript_devices.atsapi as ats

from labscript import Device, AnalogIn, compiler, set_passed_properties


class AlazarTechBoard(Device):
    """An Alazar Technologies (ATS) capture board; the worker supports only the ATS9462."""

    allowed_children = [AnalogIn]
    description = 'Generic_Alazar_Technologies_capture_board'

    # Many properties not supported. Examples include: AlazarSetExternalClockLevel,
    # SetDataFormat, anything to do with board memory, anything "for scanning".
    @set_passed_properties(
        property_names={
            "device_properties": [
                "ats_system_id", "ats_board_id",
                "requested_acquisition_rate", "acquisition_duration",
                "clock_source_id", "sample_rate_id", "clock_edge_id", "decimation",
                "trig_operation",
                "trig_engine_id1", "trig_source_id1", "trig_slope_id1", "trig_level_id1",
                "trig_engine_id2", "trig_source_id2", "trig_slope_id2", "trig_level_id2",
                "exttrig_coupling_id", "exttrig_range_id",
                "trig_delay_samples", "trig_timeout_10usecs",
                "channels",
                "chA_coupling_id", "chA_input_range", "chA_impedance_id", "chA_bw_limit",
                "chB_coupling_id", "chB_input_range", "chB_impedance_id", "chB_bw_limit",
            ]
        }
    )
    def __init__(
        self,
        name,
        server,
        ats_system_id=1,
        ats_board_id=1,
        requested_acquisition_rate=0,
        acquisition_duration=1,
        clock_source_id=ats.INTERNAL_CLOCK,
        sample_rate_id=ats.SAMPLE_RATE_180MSPS,
        clock_edge_id=ats.CLOCK_EDGE_RISING,
        decimation=0,
        trig_operation=ats.TRIG_ENGINE_OP_J,
        trig_engine_id1=ats.TRIG_ENGINE_J,
        trig_source_id1=ats.TRIG_EXTERNAL,
        trig_slope_id1=ats.TRIGGER_SLOPE_POSITIVE,
        trig_level_id1=150,
        trig_engine_id2=ats.TRIG_ENGINE_K,
        trig_source_id2=ats.TRIG_DISABLE,
        trig_slope_id2=ats.TRIGGER_SLOPE_POSITIVE,
        trig_level_id2=150,
        exttrig_coupling_id=ats.DC_COUPLING,
        exttrig_range_id=ats.ETR_5V,
        trig_delay_samples=0,
        trig_timeout_10usecs=0,
        channels=ats.CHANNEL_A | ats.CHANNEL_B,
        chA_coupling_id=ats.AC_COUPLING,
        chA_input_range=4000,
        chA_impedance_id=ats.IMPEDANCE_1M_OHM,
        chA_bw_limit=0,
        chB_coupling_id=ats.AC_COUPLING,
        chB_input_range=4000,
        chB_impedance_id=ats.IMPEDANCE_1M_OHM,
        chB_bw_limit=0,
        **kwargs,
    ):
        """
        ``ats`` below is `labscript_devices.atsapi`, whose constants set most keywords.
        Every keyword but `name` and `server` is saved in the shot file for the
        worker, which makes one acquisition per shot.

        Parameters
        ----------
        name : str
            Python variable name of the device.
        server : str
            Saved as the device's BLACS connection, which BLACS shows on the board's
            tab. The worker does not use it.
        ats_system_id : int, optional
            Board system ID; 1 by default. The worker does not read it and opens
            system 1.
        ats_board_id : int, optional
            Board ID in the system; 1 by default. The worker does not read it and
            opens board 1.
        requested_acquisition_rate : float, optional
            Sample rate to ask for, in samples per second. The default, 0, is no
            usable rate: set it. With ``ats.INTERNAL_CLOCK`` the worker takes the
            nearest rate in its ``atsSampleRates``, 1 kS/s to 180 MS/s. With
            ``ats.EXTERNAL_CLOCK_10MHz_REF`` it takes a rate at or just above this,
            from a PLL clock of 150 to 180 MHz over a divider, and raises if the
            divider would exceed 10000.
        acquisition_duration : float, optional
            Duration of the acquisition in seconds, rounded to a whole number of
            samples; 1 by default. The inputs' ``acquire`` calls do not set it.
        clock_source_id : int, optional
            Clock source, an ``ats`` ``*_CLOCK`` constant; ``ats.INTERNAL_CLOCK`` by
            default. The worker implements ``ats.INTERNAL_CLOCK`` and
            ``ats.EXTERNAL_CLOCK_10MHz_REF``, and raises for any other source.
        sample_rate_id : int, optional
            ``ats.SAMPLE_RATE_180MSPS`` by default. The worker does not read it: the
            rate comes from `requested_acquisition_rate`.
        clock_edge_id : int, optional
            ``ats.CLOCK_EDGE_RISING``, the default, or ``ats.CLOCK_EDGE_FALLING``.
            Both clock sources the worker implements use the rising edge, whatever
            this says.
        decimation : int, optional
            0 by default. The worker does not read it: it uses 0 with the internal
            clock and the divider minus one with the external.
        trig_operation : int, optional
            How the two trigger engines combine, an ``ats.TRIG_ENGINE_OP_*``
            constant; ``ats.TRIG_ENGINE_OP_J`` by default.
        trig_engine_id1, trig_engine_id2 : int, optional
            ``ats.TRIG_ENGINE_J`` or ``ats.TRIG_ENGINE_K``; the defaults are J for
            the first engine and K for the second.
        trig_source_id1, trig_source_id2 : int, optional
            Source of each engine, ``ats.TRIG_CHAN_A``, ``ats.TRIG_CHAN_B``,
            ``ats.TRIG_EXTERNAL`` or ``ats.TRIG_DISABLE``; the defaults are
            ``ats.TRIG_EXTERNAL`` for the first engine and ``ats.TRIG_DISABLE`` for
            the second.
        trig_slope_id1, trig_slope_id2 : int, optional
            ``ats.TRIGGER_SLOPE_POSITIVE``, the default, or
            ``ats.TRIGGER_SLOPE_NEGATIVE``.
        trig_level_id1, trig_level_id2 : int, optional
            An 8-bit level code; 150 by default. For the external trigger with
            ``ats.ETR_5V`` the level is (code - 128) / 128 * 5 V, so 150 is 860 mV.
        exttrig_coupling_id : int, optional
            ``ats.AC_COUPLING`` or ``ats.DC_COUPLING``, the default, for the external
            trigger input.
        exttrig_range_id : int, optional
            Range of the external trigger input, ``ats.ETR_5V`` (the default),
            ``ats.ETR_1V``, ``ats.ETR_TTL`` or ``ats.ETR_2V5``.
        trig_delay_samples : int, optional
            0 by default. The worker does not read it: the trigger delay is always 0.
        trig_timeout_10usecs : int, optional
            In units of 10 microseconds; 0 by default. The worker does not read it:
            the trigger timeout is always 0, so the board waits for a trigger
            forever.
        channels : int, optional
            Channels to acquire: ``ats.CHANNEL_A``, or both as
            ``ats.CHANNEL_A | ats.CHANNEL_B`` (the default). Channel B alone is not
            supported: the worker takes a lone channel to be channel A.
        chA_coupling_id, chB_coupling_id : int, optional
            ``ats.AC_COUPLING``, the default, or ``ats.DC_COUPLING``.
        chA_input_range, chB_input_range : int, optional
            Input range of the channel in millivolts, ``+/-`` this; 4000 by default.
            The worker accepts 200, 400, 800, 2000 and 4000, and raises
            :class:`~labscript.LabscriptError` for any other when the shot starts.
        chA_impedance_id, chB_impedance_id : int, optional
            An ``ats.IMPEDANCE_*`` constant; ``ats.IMPEDANCE_1M_OHM`` by default.
        chA_bw_limit, chB_bw_limit : int, optional
            1 turns on the channel's low-pass filter and 0, the default, turns it off.
        **kwargs
            Passed to :class:`~labscript.Device`.
        """
        Device.__init__(self, name, None, None, **kwargs)
        self.name = name
        # BLACS starts and stops only devices that have a BLACS_connection.
        self.BLACS_connection = server

    def add_device(self, output):
        Device.add_device(self, output)

    def generate_code(self, hdf5_file):
        """Write the inputs' acquisitions to the shot file as the ACQUISITIONS table."""
        Device.generate_code(self, hdf5_file)
        inputs = {}
        for device in self.child_devices:
            if isinstance(device, AnalogIn):
                inputs[device.connection] = device
            else:
                raise Exception(
                    f"{device.name} is connected to the AlazarTechBoard {self.name} "
                    "but is not an AnalogIn. Connect only AnalogIn devices to it."
                )
        input_connections = sorted(inputs)
        input_attrs = []
        acquisitions = []
        for connection in input_connections:
            input_attrs.append(self.name+'/'+connection)
            for acq in inputs[connection].acquisitions:
                acquisitions.append((
                    connection, acq['label'], acq['start_time'], acq['end_time'],
                    acq['wait_label'], acq['scale_factor'], acq['units'],
                ))
        # 'S' strings are bytes, the same on disk as the 'a' alias numpy 2 removed.
        acquisitions_table_dtypes = [
            ('connection', 'S256'), ('label', 'S256'), ('start', float), ('stop', float),
            ('wait label', 'S256'), ('scale factor', float), ('units', 'S256'),
        ]
        acquisition_table = np.empty(
            len(acquisitions), dtype=acquisitions_table_dtypes)
        for i, acq in enumerate(acquisitions):
            acquisition_table[i] = acq
        # The table must be non-empty.
        if len(acquisition_table):
            grp = self.init_device_group(hdf5_file)
            grp.create_dataset(
                'ACQUISITIONS', compression=compiler.compression, data=acquisition_table)
            self.set_property('analog_in_channels', ', '.join(
                input_attrs), location='device_properties')
