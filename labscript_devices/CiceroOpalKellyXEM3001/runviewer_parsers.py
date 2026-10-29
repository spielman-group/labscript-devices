#####################################################################
#                                                                   #
# /labscript_devices/CiceroOpalKellyXEM3001/runviewer_parsers.py    #
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
import labscript_utils.properties
from labscript_devices.common.runviewer import PseudoclockParser


class CiceroOpalKellyXEM3001Parser(PseudoclockParser):
    def get_traces(self, add_trace, clock=None):
        with h5py.File(self.path, 'r') as f:
            pulse_program = f[f'devices/{self.name}/PULSE_PROGRAM'][:]
            device_properties = labscript_utils.properties.get(
                f, self.name, 'device_properties'
            )
            connection_table_properties = labscript_utils.properties.get(
                f, self.name, 'connection_table_properties'
            )

        clock_frequency = connection_table_properties['clock_frequency']
        # A secondary's program begins with the wait for its first trigger, its start.
        if not device_properties['is_master_pseudoclock']:
            pulse_program = pulse_program[1:]

        segments = [[]]
        for row in pulse_program:
            # A row of 0 reps is a wait.
            if row['reps'] == 0:
                segments.append([])
            else:
                high = row['on_period'] / clock_frequency
                low = row['off_period'] / clock_frequency
                segments[-1].append((high, low, row['reps']))

        trace = self.clock_trace(clock, device_properties['trigger_delay'], segments)
        return self.add_clock_lines(add_trace, trace, 'Clock Out')
