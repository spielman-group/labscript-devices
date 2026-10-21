#####################################################################
#                                                                   #
# /labscript_devices/PulseBlasterUSB/blacs_tabs.py                  #
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


class PulseBlasterUSBTab(PulseBlaster_No_DDSTab):
    num_DO = 24
    worker_class = 'labscript_devices.PulseBlasterUSB.blacs_workers.PulseBlasterUSBWorker'
