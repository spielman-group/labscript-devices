import labscript_utils.h5_lock
import h5py
import numpy as np

import labscript_utils.properties as properties
from labscript_utils import dedent
from labscript_devices.common.runviewer import rising_edge_times


class NI_DAQmxParser:
    """Runviewer parser for NI_DAQmx devices and their models."""

    def __init__(self, path, device):
        self.path = path
        self.name = device.name
        self.device = device

    def get_traces(self, add_trace, clock=None):
        """Add the outputs' traces to runviewer; return those that clock other devices."""

        with h5py.File(self.path, 'r') as f:

            group = f['devices/' + self.name]

            if 'AO' in group:
                AO_table = group['AO'][:]
            else:
                AO_table = None

            if 'DO' in f[f'devices/{self.name}']:
                DO_table = group['DO'][:]
            else:
                DO_table = None

            connection_table_properties = properties.get(f, self.name, 'connection_table_properties')

            version = connection_table_properties.get('__version__', None)
            if version is None:
                msg = """Shot was compiled with the old version of the NI_DAQmx device
                    class. The new runviewer parser is not backward compatible with old
                    shot files. Either downgrade labscript_devices to 2.2.0 or less, or
                    recompile the shot with labscript_devices 2.3.0 or greater."""
                raise RuntimeError(dedent(msg))

            ports = connection_table_properties['ports']
            static_AO = connection_table_properties['static_AO']
            static_DO = connection_table_properties['static_DO']

        clock_ticks = rising_edge_times(clock)

        traces = {}

        if DO_table is not None:
            ports_in_use = DO_table.dtype.names
            for port_str in ports_in_use:
                for line in range(ports[port_str]["num_lines"]):
                    # Extract each digital value from the packed bits:
                    line_vals = (((1 << line) & DO_table[port_str]) != 0).astype(float)
                    if static_DO:
                        line_vals = np.full(len(clock_ticks), line_vals[0])
                    traces[f'{port_str}/line{line}'] = (clock_ticks, line_vals)

        if AO_table is not None:
            for chan in AO_table.dtype.names:
                vals = AO_table[chan]
                if static_AO:
                    vals = np.full(len(clock_ticks), vals[0])
                traces[chan] = (clock_ticks, vals)

        triggers = {}
        for channel_name, channel in self.device.child_list.items():
            # A digital connection may have a PFI suffix, as in 'port0/line0 (PFI0)'.
            connection = channel.parent_port.split()[0]
            if connection in traces:
                trace = traces[connection]
                # A line with child devices, such as a Trigger of any class, clocks them:
                # return its trace so that runviewer loads them with it as their clock.
                if channel.child_list:
                    triggers[channel_name] = trace
                add_trace(channel_name, trace, self.name, channel.parent_port)

        return triggers
