#####################################################################
#                                                                   #
# /labscript_devices/common/runviewer.py                            #
#                                                                   #
# Copyright 2026, JQI                                               #
# Author: Ian Spielman                                              #
#                                                                   #
# This file is part of labscript_devices, in the labscript suite    #
# (see http://labscriptsuite.org), and is licensed under the        #
# Simplified BSD License. See the license.txt file in the root of   #
# the project for the full license.                                 #
#                                                                   #
#####################################################################
import labscript_utils.h5_lock, h5py
import numpy as np
import labscript_utils.properties as properties
from labscript_utils.file_utils import warn_legacy_file


class PseudoclockParser:
    """The base of a pseudoclock device's runviewer parser.

    Runviewer draws the script's time, in which a wait takes no time: each device
    resumes where its wait begins. A master's own program places its waits. A
    secondary, given the `clock` it is triggered by, starts `trigger_delay` after
    its trigger and resumes `trigger_delay` after each retrigger.
    """

    def __init__(self, path, device):
        self.path = path
        self.name = device.name
        self.device = device

    def resume_times(self, clock, trigger_delay):
        """Return ``resume(n, t)``, when the program starts or resumes.

        Call it with 0 and 0 for the start, then with each wait's number and the
        time the program reaches it. A master carries on from `t`. A secondary
        resumes `trigger_delay` after its nth trigger time, as labscript saved it.
        """
        if clock is None:
            return lambda n, t: t
        with h5py.File(self.path, 'r') as f:
            device_properties = properties.get(f, self.name, 'device_properties')
            wait_times = f['waits']['time']
        triggers = device_properties.get('trigger_times')
        # LEGACY TRIGGER TIMES COMPATIBILITY. DEPRECATED CODE, WILL BE REMOVED.
        # Shot files compiled before labscript saved a secondary's trigger times: its
        # nth retrigger is the clock's edge nearest the nth wait's time.
        if triggers is None:
            warn_legacy_file(self.path, "lacks its secondaries' trigger times")
            edges = rising_edge_times(clock)
            after = np.clip(np.searchsorted(edges, wait_times), 1, len(edges) - 1)
            later = edges[after] - wait_times < wait_times - edges[after - 1]
            retriggers = np.where(later, edges[after], edges[after - 1])
            triggers = np.concatenate([[edges[0]], retriggers])
        triggers = np.asarray(triggers) + trigger_delay
        return lambda n, t: triggers[n]

    def clock_trace(self, clock, trigger_delay, segments):
        """Return the ``(times, states)`` of the ticks of `segments`.

        `segments` holds a list of ``(high, low, reps)`` rows for the program's
        start and one for after each wait: `reps` ticks, each high for `high`
        seconds and then low for `low`.
        """
        resume = self.resume_times(clock, trigger_delay)
        times, states = [], []
        t = 0.0
        for n, rows in enumerate(segments):
            t = resume(n, t)
            for high, low, reps in rows:
                for i in range(reps):
                    times.append(t)
                    states.append(1)
                    t += high
                    times.append(t)
                    states.append(0)
                    t += low
        return np.array(times), np.array(states)

    def add_clock_lines(self, add_trace, trace, port, pseudoclock=None):
        """Add `trace` as each clock line on a port starting with `port`.

        The clock lines are those of `pseudoclock`, or of all the device's
        pseudoclocks. Return the traces by clock line name, for runviewer to pass
        to the devices on them.
        """
        pseudoclocks = [pseudoclock] if pseudoclock else self.device.child_list.values()
        clock_lines = {}
        for pseudoclock in pseudoclocks:
            for name, clock_line in pseudoclock.child_list.items():
                if clock_line.parent_port.startswith(port):
                    clock_lines[name] = trace
                    add_trace(name, trace, self.name, clock_line.parent_port)
        return clock_lines


def rising_edge_times(clock):
    """Return the times of the rising edges of a clock that runviewer passes to a
    parser, as a (times, values) pair. A clock that is high at the first time has a
    rising edge at that time."""
    times, values = clock
    indices = np.flatnonzero(values[1:] - values[:-1] == 1) + 1
    if values[0] == 1:
        indices = np.insert(indices, 0, 0)
    return times[indices]
