#####################################################################
#                                                                   #
# /labscript_devices/PrawnBlaster/runviewer_parsers.py              #
#                                                                   #
# Copyright 2021, Philip Starkey                                    #
#                                                                   #
# This file is part of labscript_devices, in the labscript suite    #
# (see http://labscriptsuite.org), and is licensed under the        #
# Simplified BSD License. See the license.txt file in the root of   #
# the project for the full license.                                 #
#                                                                   #
#####################################################################

import labscript_utils.h5_lock  # noqa: F401
import h5py

import labscript_utils.properties as properties
from labscript_devices.runviewer_parsing import PseudoclockParser


class PrawnBlasterParser(PseudoclockParser):
    """Runviewer parser for the PrawnBlaster Pseudoclocks."""

    def get_traces(self, add_trace, clock=None):
        """Add the clock lines' traces to runviewer and return them."""
        pulse_programs = []
        with h5py.File(self.path, "r") as f:
            device_properties = properties.get(f, self.name, "device_properties")
            connection_table_properties = properties.get(f, self.name, "connection_table_properties")

            self.clock_resolution = device_properties["clock_resolution"]
            self.trigger_delay = device_properties["trigger_delay"]

            num_pseudoclocks = connection_table_properties["num_pseudoclocks"]
            for i in range(num_pseudoclocks):
                pulse_programs.append(f[f"devices/{self.name}/PULSE_PROGRAM_{i}"][:])

        clocklines_and_triggers = {}

        for pseudoclock_name, pseudoclock in self.device.child_list.items():
            connection_parts = pseudoclock.parent_port.split()
            # Skip if not one of the 4 possible pseudoclock outputs (there is one for
            # the wait monitor too potentially)
            if connection_parts[0] != "pseudoclock":
                continue

            index = int(connection_parts[1])
            pulse_program = pulse_programs[index]

            clock_factor = self.clock_resolution / 2.0
            segments = [[]]
            last_instruction_was_wait = False
            for row in pulse_program:
                # As in the firmware, a zero half_period and reps is the stop, and
                # reps 0 alone a wait
                if row["reps"] == 0 and row["half_period"] == 0:
                    break
                if row["reps"] == 0 and not last_instruction_was_wait:  # WAIT
                    last_instruction_was_wait = True
                    segments.append([])
                elif row["reps"] == 0:
                    # As in the firmware, waits in a row are one wait: two make it
                    # indefinite, so we just skip this instruction.
                    continue
                else:
                    last_instruction_was_wait = False
                    half = row["half_period"] * clock_factor
                    segments[-1].append((half, half, row["reps"]))

            trace = self.clock_trace(clock, self.trigger_delay, segments)
            # The GPIO ports only: the internal wait monitor's clock line has none.
            clocklines_and_triggers.update(
                self.add_clock_lines(add_trace, trace, "GPIO", pseudoclock)
            )

        return clocklines_and_triggers
