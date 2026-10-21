#####################################################################
#                                                                   #
# /labscript_devices/PrawnDO/runviewer_parsers.py                   #
#                                                                   #
# Copyright 2023, Philip Starkey, Carter Turnbaugh, Patrick Miller  #
#                                                                   #
# This file is part of labscript_devices, in the labscript suite    #
# (see http://labscriptsuite.org), and is licensed under the        #
# Simplified BSD License. See the license.txt file in the root of   #
# the project for the full license.                                 #
#                                                                   #
#####################################################################
import labscript_utils.h5_lock
import h5py
import numpy as np

import labscript_utils.properties as properties
from labscript_utils.file_utils import warn_legacy_file
from labscript_devices.runviewer_parsing import rising_edge_times


class PrawnDOParser:
    def __init__(self, path, device):
        self.path = path
        self.name = device.name
        self.device = device

    def get_traces(self, add_trace, clock=None):
        if clock is not None:
            clock_ticks = rising_edge_times(clock)

        with h5py.File(self.path, "r") as f:
            device_properties = properties.get(f, self.name, 'device_properties')
            self.clock_resolution = device_properties['clock_resolution']
            self.trigger_delay = device_properties['trigger_delay']
            self.wait_delay = device_properties['wait_delay']

            group = f['devices/' + self.name]
            # LEGACY PULSE_PROGRAM NAME COMPATIBILITY. DEPRECATED CODE, WILL BE REMOVED.
            # Shot files compiled before the dataset's name was upper case.
            dataset = 'PULSE_PROGRAM' if 'PULSE_PROGRAM' in group else 'pulse_program'
            if 'pulse_program' in group:
                warn_legacy_file(
                    self.path, "names the PrawnDO's pulse program pulse_program, not PULSE_PROGRAM"
                )
            pulse_program = group[dataset][()]
            wait_times = np.sort(f['waits']['time'])

        # remove final element from program (2nd part of stop instruction)
        pulse_program = np.delete(pulse_program, -1)
        time_deltas_table = pulse_program['reps']*self.clock_resolution
        # re-add trigger delay
        trigger_index = 0
        t = 0 if clock is None else clock_ticks[trigger_index] + self.trigger_delay
        time_deltas_table[0] += t
        # re-add wait delays (ignoring final one, which is from the 1st part of stop command)
        wait_idxs = np.nonzero(pulse_program['reps']==0)[0][:-1]
        if clock is None:
            time_deltas_table[wait_idxs] += self.wait_delay
        # insert t=0 for cumsum, remove final value (from stop instruction)
        times_table = np.cumsum(np.insert(time_deltas_table,0,0.0))[:-1]
        if clock is not None:
            # The nth wait resumes a trigger delay after the master's tick at the shot's
            # nth wait time, not at this device's own, which its coarser clock can round
            # past that tick. 1 ps allows for the float error in the drawn ticks.
            for wait_idx, wait_time in zip(wait_idxs, wait_times):
                tick = clock_ticks[np.searchsorted(clock_ticks, wait_time - 1e-12)]
                times_table[wait_idx + 1:] += tick + self.trigger_delay - times_table[wait_idx + 1]

        # Convert bit sets back to individual bits for each output: reshape so each
        # number has its own row, byteswap and view as uint8 so unpackbits reads its high
        # byte first, then flip so column i is output do<i>.
        do_bitfield = np.fliplr(
            np.unpackbits(
                pulse_program['bit_sets']
                .reshape(pulse_program.shape + (1,))
                .byteswap()
                .view(np.uint8),
                axis=1,
            )
        )

        digital_outs = {}

        # Walk down the device tree from the PrawnDO to its digital outputs.
        for pseudoclock_name, pseudoclock in self.device.child_list.items():
            for clock_line_name, clock_line in pseudoclock.child_list.items():
                for internal_device_name, internal_device in clock_line.child_list.items():
                    for channel_name, channel in internal_device.child_list.items():
                        chan = int(channel.parent_port.split('do')[-1])
                        output_trace = (times_table, do_bitfield[:,chan])
                        digital_outs[channel_name] = output_trace
                        add_trace(channel_name, output_trace,
                                  self.name, channel.parent_port)

        return digital_outs


class _PrawnDOIntermediateParser:
    def __init__(self, path, device):
        self.path = path
        self.name = device.name
        self.device = device

    def get_traces(self, add_trace, clock=None):
        return {list(self.device.child_list.keys())[0]: clock}
