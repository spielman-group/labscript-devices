#####################################################################
#                                                                   #
# /labscript_devices/PulseBlaster_SP2_24_100_32k/blacs_workers.py   #
#                                                                   #
# Copyright 2013, Monash University                                 #
#                                                                   #
# This file is part of labscript_devices, in the labscript suite    #
# (see http://labscriptsuite.org), and is licensed under the        #
# Simplified BSD License. See the license.txt file in the root of   #
# the project for the full license.                                 #
#                                                                   #
#####################################################################

from labscript_devices.PulseBlaster_No_DDS.blacs_workers import PulseBlaster_No_DDS_Worker


class PulseBlaster_SP2_24_100_32k_Worker(PulseBlaster_No_DDS_Worker):
    core_clock_freq = 100.0
