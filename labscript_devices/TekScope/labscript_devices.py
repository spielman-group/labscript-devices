from labscript import Device, LabscriptError, set_passed_properties


class TekScope(Device):
    """A Tektronix oscilloscope on VISA, whose displayed channels each shot saves.

    They are saved to ``/data/traces/<name>`` in the shot file.
    """
    description = 'Tektronix oscilloscope'

    @set_passed_properties(
        property_names={
            'connection_table_properties': ['termination', 'preamble_string'],
            'device_properties': ['timeout', 'int16'],
        }
    )
    def __init__(self, name, addr,
                 termination='\n', preamble_string='WFMP',
                 timeout=5, int16=False,
                 **kwargs):
        """
        Parameters
        ----------
        name : str
            Python variable name of the device.
        addr : str
            VISA address of the scope. The worker opens the first connected resource
            that matches it, so it can be a pattern such as ``'USB?*::INSTR'``.
        termination : str, optional
            Character signalling the end of a response; ``'\\n'`` by default. Set
            once, in the connection table.
        preamble_string : {'WFMP', 'WFMO'}, optional
            Base command for the waveform preamble; ``'WFMP'`` by default. Any other
            value is refused. Set once, in the connection table.
        timeout : float, optional
            Seconds to wait for the response to a query over the VISA interface; 5
            by default. Set per shot.
        int16 : bool, optional
            Download waveform points as 16-bit integers; ``False`` by default, which
            downloads 8-bit integers. Set per shot.
        **kwargs
            Passed to :class:`~labscript.Device`.
        """
        Device.__init__(self, name, None, addr, **kwargs)
        self.name = name
        self.BLACS_connection = addr
        self.termination = termination
        self.preamble_string = preamble_string
        assert preamble_string in ['WFMO', 'WFMP'], (
            f"{name}: preamble_string must be 'WFMO' or 'WFMP', not {preamble_string!r}."
        )

    def generate_code(self, hdf5_file):
        Device.generate_code(self, hdf5_file)
