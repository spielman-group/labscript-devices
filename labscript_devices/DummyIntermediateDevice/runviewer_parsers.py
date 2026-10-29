#####################################################################
#                                                                   #
# /labscript_devices/DummyIntermediateDevice/runviewer_parsers.py   #
#                                                                   #
# Copyright 2013, Monash University                                 #
#                                                                   #
# This file is part of labscript_devices, in the labscript suite    #
# (see http://labscriptsuite.org), and is licensed under the        #
# Simplified BSD License. See the license.txt file in the root of   #
# the project for the full license.                                 #
#                                                                   #
#####################################################################
import labscript_utils.h5_lock
import h5py

from labscript_devices.runviewer_parsing import rising_edge_times


class DummyIntermediateDeviceParser:
    def __init__(self, path, device):
        self.path = path
        self.name = device.name
        self.device = device

    def get_traces(self, add_trace, clock=None):
        if clock is None:
            raise Exception(
                f'No clock passed to {self.name}. The DummyIntermediateDevice must be '
                'clocked by another device.'
            )
        clock_ticks = rising_edge_times(clock)

        with h5py.File(self.path, 'r') as f:
            # A device with no outputs writes no table.
            if 'OUTPUTS' not in f[f'devices/{self.name}']:
                return {}
            outputs = f[f'devices/{self.name}/OUTPUTS'][:]

        triggers = {}
        for channel_name, channel in self.device.child_list.items():
            trace = (clock_ticks, outputs[channel_name])
            # A line with child devices, such as a Trigger of any class, clocks them:
            # return its trace so that runviewer loads them with it as their clock.
            if channel.child_list:
                triggers[channel_name] = trace
            add_trace(channel_name, trace, self.name, channel.parent_port)
        return triggers
