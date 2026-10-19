#####################################################################
#                                                                   #
# /labscript_devices/PulseBlaster_No_DDS/labscript_devices.py       #
#                                                                   #
# Copyright 2013, Monash University                                 #
#                                                                   #
# This file is part of labscript_devices, in the labscript suite    #
# (see http://labscriptsuite.org), and is licensed under the        #
# Simplified BSD License. See the license.txt file in the root of   #
# the project for the full license.                                 #
#                                                                   #
#####################################################################

from labscript_devices.PulseBlaster.labscript_devices import PulseBlasterBase


class PulseBlaster_No_DDS(PulseBlasterBase):

    description = 'generic DO only Pulseblaster'
    clock_limit = 8.3e6 # can probably go faster
    clock_resolution = 20e-9
    n_flags = 24
    clock_frequency = 100e6
