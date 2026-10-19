#####################################################################
#                                                                   #
# /labscript_devices/PulseBlasterESRPro200/blacs_tabs.py            #
#                                                                   #
# Copyright 2013, Monash University                                 #
#                                                                   #
# This file is part of labscript_devices, in the labscript suite    #
# (see http://labscriptsuite.org), and is licensed under the        #
# Simplified BSD License. See the license.txt file in the root of   #
# the project for the full license.                                 #
#                                                                   #
#####################################################################

from labscript_devices.PulseBlaster_No_DDS.blacs_tabs import PulseBlaster_No_DDSTab


class PulseBlasterESRPro200Tab(PulseBlaster_No_DDSTab):
    # Capabilities
    num_DO = 21
    worker_class = 'labscript_devices.PulseBlasterESRPro200.blacs_workers.PulseBlasterESRPro200Worker'
