#####################################################################
#                                                                   #
# /labscript_devices/PulseBlasterESRPro200/labscript_devices.py     #
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


class PulseBlasterESRPro200(PulseBlaster_No_DDS):
    """A SpinCore PulseBlaster ESR-PRO-200, with 21 flags and a 200 MHz core clock."""

    description = 'SpinCore PulseBlaster ESR-PRO-200'
    clock_limit = 200.0e6
    clock_resolution = 5e-9
    n_flags = 21
    clock_frequency = 200e6
