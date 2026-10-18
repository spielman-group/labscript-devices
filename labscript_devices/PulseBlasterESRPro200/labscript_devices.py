#####################################################################
#                                                                   #
# /PulseblasterESRpro500.py                                         #
#                                                                   #
# Copyright 2013, Monash University                                 #
#                                                                   #
# This file is part of labscript_devices, in the labscript suite    #
# (see http://labscriptsuite.org), and is licensed under the        #
# Simplified BSD License. See the license.txt file in the root of   #
# the project for the full license.                                 #
#                                                                   #
#####################################################################
from labscript_devices import BLACS_tab, runviewer_parser
from labscript_devices.PulseBlaster_No_DDS.labscript_devices import PulseBlaster_No_DDS
from labscript_devices.PulseBlaster_No_DDS.blacs_tabs import Pulseblaster_No_DDS_Tab
from labscript_devices.PulseBlaster_No_DDS.blacs_workers import PulseblasterNoDDSWorker
from labscript_devices.PulseBlaster_No_DDS.runviewer_parsers import PulseBlaster_No_DDS_Parser


class PulseBlasterESRPro200(PulseBlaster_No_DDS):
    description = 'SpinCore PulseBlaster ESR-PRO-200'
    clock_limit = 200.0e6
    clock_resolution = 5e-9
    n_flags = 21
    core_clock_freq = 200.0


@BLACS_tab
class pulseblasteresrpro200(Pulseblaster_No_DDS_Tab):
    # Capabilities
    num_DO = 21
    def __init__(self,*args,**kwargs):
        self.device_worker_class = PulseblasterESRPro200Worker 
        Pulseblaster_No_DDS_Tab.__init__(self,*args,**kwargs)


class PulseblasterESRPro200Worker(PulseblasterNoDDSWorker):
    core_clock_freq = 200.0


@runviewer_parser
class PulseblasterESRPro200Parser(PulseBlaster_No_DDS_Parser):
    num_dds = 0
    num_flags = 21
