#####################################################################
#                                                                   #
# /labscript_devices/PulseBlasterESRPro500/labscript_devices.py     #
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


class PulseBlasterESRPro500(PulseBlaster_No_DDS):
    """A SpinCore PulseBlaster ESR-PRO-500, with 24 flags and a 500 MHz core clock.

    Flags 21 to 23 control the short-pulse feature on firmware that has it. This
    device does not use the feature, and on that firmware they must be set high for
    the board to produce any output.
    """

    description = 'SpinCore PulseBlaster ESR-PRO-500'
    clock_limit = 50.0e6 # can probably go faster
    clock_resolution = 4e-9
    n_flags = 24
    clock_frequency = 500e6
