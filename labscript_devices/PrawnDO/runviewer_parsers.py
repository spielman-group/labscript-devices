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
from labscript_devices.runviewer_parsing import PseudoclockParser


class PrawnDOParser(PseudoclockParser):
    def get_traces(self, add_trace, clock=None):
        with h5py.File(self.path, "r") as f:
            device_properties = properties.get(f, self.name, 'device_properties')
            self.clock_resolution = device_properties['clock_resolution']
            self.trigger_delay = device_properties['trigger_delay']

            group = f['devices/' + self.name]
            # LEGACY PULSE_PROGRAM NAME COMPATIBILITY. DEPRECATED CODE, WILL BE REMOVED.
            # Shot files compiled before the dataset's name was upper case.
            dataset = 'PULSE_PROGRAM' if 'PULSE_PROGRAM' in group else 'pulse_program'
            if 'pulse_program' in group:
                warn_legacy_file(
                    self.path, "names the PrawnDO's pulse program pulse_program, not PULSE_PROGRAM"
                )
            pulse_program = group[dataset][()]

        # remove final element from program (2nd part of stop instruction)
        pulse_program = np.delete(pulse_program, -1)
        durations = pulse_program['reps'] * self.clock_resolution
        # Rows of 0 reps are the waits, and last the stop's first part.
        wait_idxs = np.nonzero(pulse_program['reps'] == 0)[0][:-1]
        # Each stretch of rows up to a wait is drawn from its start.
        starts = self.start_and_resume_times(clock, self.trigger_delay)
        bounds = np.concatenate([[0], wait_idxs + 1, [len(pulse_program)]])
        times_table = np.empty(len(pulse_program))
        for start, first, end in zip(starts, bounds[:-1], bounds[1:]):
            times_table[first:end] = np.cumsum(np.insert(durations[first:end - 1], 0, start))
        # The trace starts at 0 with the first row's output.
        times_table[0] = 0

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
