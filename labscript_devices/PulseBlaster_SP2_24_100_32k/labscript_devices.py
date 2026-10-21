#####################################################################
#                                                                   #
# /labscript_devices/PulseBlaster_SP2_24_100_32k/labscript_devices.py #
#                                                                   #
# Copyright 2013, Monash University                                 #
#                                                                   #
# This file is part of labscript_devices, in the labscript suite    #
# (see http://labscriptsuite.org), and is licensed under the        #
# Simplified BSD License. See the license.txt file in the root of   #
# the project for the full license.                                 #
#                                                                   #
#####################################################################

from labscript_devices.PulseBlaster_No_DDS.labscript_devices import PulseBlaster_No_DDS


class PulseBlaster_SP2_24_100_32k(PulseBlaster_No_DDS):
    """A SpinCore PulseBlaster-SP2-24-100-32k, with 24 flags and a 100 MHz core clock."""

    description = 'SpinCore PulseBlaster-SP2-24-100-32k'
    clock_limit = 5.0e6
    clock_resolution = 10e-9
    n_flags = 24
    clock_frequency = 100e6

    def __init__(self, *args, **kwargs):
        """`max_instructions` defaults to 32000, and the rest are those of
        `PulseBlaster_No_DDS`."""
        if 'max_instructions' not in kwargs:
            kwargs['max_instructions'] = 32000
        PulseBlaster_No_DDS.__init__(self, *args, **kwargs)
