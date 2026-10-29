#####################################################################
#                                                                   #
# /labscript_devices/DummyPseudoclock/blacs_workers.py              #
#                                                                   #
# Copyright 2017, Christopher Billington                            #
#                                                                   #
# This file is part of labscript_devices, in the labscript suite    #
# (see http://labscriptsuite.org), and is licensed under the        #
# Simplified BSD License. See the license.txt file in the root of   #
# the project for the full license.                                 #
#                                                                   #
#####################################################################
import time
import labscript_utils.h5_lock
import h5py
from labscript_devices.common.pseudoclock import PseudoclockWorker
import labscript_utils.properties as properties


class DummyPseudoclockWorker(PseudoclockWorker):
    # When the shot started, set by its first shot_finished.
    start_time = None

    def program_manual(self, front_panel_values):
        return {}

    def transition_to_buffered(self, device_name, h5_file, front_panel_values, fresh):
        # labscript saves stop_time, in seconds, for every pseudoclock device.
        with h5py.File(h5_file, 'r') as f:
            device_properties = properties.get(f, self.device_name, 'device_properties')
            self.stop_time = device_properties['stop_time']
        return {}

    def shot_finished(self):
        # The shot is timed from the first call, which the tab makes as the run starts.
        # Wait up to 1 s for stop_time seconds to pass since then, returning True if
        # they have and False if not.
        if self.start_time is None:
            self.start_time = time.time()
        timeout = min(self.start_time + self.stop_time - time.time(), 1)
        if timeout < 0:
            return True
        time.sleep(timeout)
        return self.start_time + self.stop_time < time.time()

    def transition_to_manual(self):
        self.wait_for_end_of_shot()
        self.start_time = None
        self.stop_time = None
        return True

    def shutdown(self):
        return

    def abort(self):
        self.start_time = None
        self.stop_time = None
        return True

    def abort_buffered(self):
        return self.abort()

    def abort_transition_to_buffered(self):
        return self.abort()
