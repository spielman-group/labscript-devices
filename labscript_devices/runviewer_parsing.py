#####################################################################
#                                                                   #
# /labscript_devices/runviewer_parsing.py                           #
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


class PseudoclockParser:
    """The base of a pseudoclock device's runviewer parser.

    Runviewer draws the script's time, in which a wait takes no time: each device
    resumes where its wait begins. A master's own program places its waits. A
    secondary starts `trigger_delay` after its trigger, the first rising edge of
    the `clock` runviewer passes it, and resumes `trigger_delay` after each
    retrigger.
    """

    def __init__(self, path, device):
        self.path = path
        self.name = device.name
        self.device = device

    def resume_times(self, clock, trigger_delay):
        """Return ``resume(n, t)``, when the program starts or resumes.

        Call it with 0 and 0 for the start, then with each wait's number and the
        time the program reaches it. A master carries on from `t`. A secondary's
        nth retrigger is its clock's edge nearest the nth wait's time: labscript
        rounds a trigger to the nearest tick of its clock, and keeps the wait's
        time unrounded.
        """
        if clock is None:
            return lambda n, t: t
        with h5py.File(self.path, 'r') as f:
            wait_times = f['waits']['time']
        edges = rising_edge_times(clock)
        after = np.clip(np.searchsorted(edges, wait_times), 1, len(edges) - 1)
        later = edges[after] - wait_times < wait_times - edges[after - 1]
        retriggers = np.where(later, edges[after], edges[after - 1])
        triggers = np.concatenate([[edges[0]], retriggers]) + trigger_delay
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
    """Return the times of a clock's rising edges.

    Parameters
    ----------
    clock : tuple of numpy.ndarray
        The ``(times, values)`` that runviewer passes to a parser's ``get_traces``
        as `clock`, with values of 0 and 1. The clock is taken to be low before its
        first time, so one that starts high rises at its first time.
    """
    times, values = clock[0], clock[1]
    edges = np.where((values[1:] - values[:-1]) == 1)[0] + 1
    if values[0] == 1:
        edges = np.insert(edges, 0, 0)
    return times[edges]
