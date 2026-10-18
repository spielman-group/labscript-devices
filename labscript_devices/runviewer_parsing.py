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
import numpy as np


def rising_edge_times(clock):
    """Return the times of the rising edges of a clock that runviewer passes to a
    parser as ``(times, values)``.

    A clock that starts high counts as rising at its first time, since it is low
    before the shot.
    """
    times, values = clock[0], clock[1]
    edges = np.where((values[1:] - values[:-1]) == 1)[0] + 1
    if values[0] == 1:
        edges = np.insert(edges, 0, 0)
    return times[edges]
