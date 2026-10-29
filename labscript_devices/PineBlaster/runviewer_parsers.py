#####################################################################
#                                                                   #
# /labscript_devices/PineBlaster/runviewer_parsers.py               #
#                                                                   #
# Copyright 2013, Monash University                                 #
#                                                                   #
# This file is part of the module labscript_devices, in the         #
# labscript suite (see http://labscriptsuite.org), and is           #
# licensed under the Simplified BSD License. See the license.txt    #
# file in the root of the project for the full license.             #
#                                                                   #
#####################################################################

import labscript_utils.h5_lock, h5py
from labscript_devices.common.runviewer import PseudoclockParser

from .labscript_devices import PineBlaster


class PineBlasterParser(PseudoclockParser):
    clock_resolution = PineBlaster.clock_resolution
    trigger_delay = PineBlaster.trigger_delay

    def get_traces(self, add_trace, clock=None):
        with h5py.File(self.path, 'r') as f:
            pulse_program = f[f'devices/{self.name}/PULSE_PROGRAM'][:]

        # Each tick is high for half its period, then low for the other half.
        clock_factor = self.clock_resolution / 2.
        segments = [[]]
        for row in pulse_program:
            # A period of 0 is a wait, with 1 rep, or the stop instruction, with none.
            if row['period'] == 0:
                if row['reps'] == 1:
                    segments.append([])
            else:
                half = row['period'] * clock_factor
                segments[-1].append((half, half, row['reps']))

        trace = self.clock_trace(clock, self.trigger_delay, segments)
        return self.add_clock_lines(add_trace, trace, 'internal')
