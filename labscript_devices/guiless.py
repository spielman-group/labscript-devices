#####################################################################
#                                                                   #
# /labscript_devices/guiless.py                                     #
#                                                                   #
# Copyright 2026, JQI                                               #
# Author: Ian Spielman                                              #
#                                                                   #
# This file is part of labscript_devices, in the labscript suite    #
# (see http://labscriptsuite.org), and is licensed under the        #
# Simplified BSD License. See the license.txt file in the root of   #
# the project for the full license.                                 #
#                                                                   #
#####################################################################
from blacs.device_base_class import DeviceTab
from blacs.tab_base_classes import Worker


class GuilessTab(DeviceTab):
    """The tab of a device with no front panel, such as a remote acquisition
    board: it shows and saves nothing. A subclass names its worker in
    ``worker_class``, the worker's full import path."""

    worker_class = None

    def initialise_GUI(self):
        pass

    def get_save_data(self):
        return {}

    def restore_save_data(self, data):
        pass

    def initialise_workers(self):
        self.create_worker("main_worker", self.worker_class, {})
        self.primary_worker = "main_worker"


class GuilessWorker(Worker):
    """The worker of a device with no front panel, which has nothing to program
    in manual mode."""

    def program_manual(self, front_panel_values):
        return front_panel_values
