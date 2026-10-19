#####################################################################
#                                                                   #
# /labscript_devices/PulseBlaster_No_DDS/blacs_tabs.py              #
#                                                                   #
# Copyright 2013, Monash University                                 #
#                                                                   #
# This file is part of labscript_devices, in the labscript suite    #
# (see http://labscriptsuite.org), and is licensed under the        #
# Simplified BSD License. See the license.txt file in the root of   #
# the project for the full license.                                 #
#                                                                   #
#####################################################################

from labscript_devices.PulseBlaster.blacs_tabs import PulseBlasterBaseTab


class PulseBlaster_No_DDS_Tab(PulseBlasterBaseTab):
    # Capabilities
    num_DO = 24
    worker_class = 'labscript_devices.PulseBlaster_No_DDS.blacs_workers.PulseBlaster_No_DDS_Worker'
