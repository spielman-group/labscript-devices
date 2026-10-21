#####################################################################
#                                                                   #
# /labscript_devices/DummyPseudoclock/blacs_tabs.py                 #
#                                                                   #
# Copyright 2017, Christopher Billington                            #
#                                                                   #
# This file is part of labscript_devices, in the labscript suite    #
# (see http://labscriptsuite.org), and is licensed under the        #
# Simplified BSD License. See the license.txt file in the root of   #
# the project for the full license.                                 #
#                                                                   #
#####################################################################
from blacs.device_base_class import DeviceTab, define_state, MODE_BUFFERED


class DummyPseudoclockTab(DeviceTab):
    def initialise_workers(self):
        worker_initialisation_kwargs = {}
        self.create_worker(
            "main_worker",
            "labscript_devices.DummyPseudoclock.blacs_workers.DummyPseudoclockWorker",
            worker_initialisation_kwargs,
        )
        self.primary_worker = "main_worker"

    @define_state(MODE_BUFFERED, True)
    def start_run(self, notify_queue):
        self.wait_until_done(notify_queue)

    @define_state(MODE_BUFFERED, True)
    def wait_until_done(self, notify_queue):
        """Call shot_finished repeatedly in the worker until the shot is complete."""
        done = yield (self.queue_work(self.primary_worker, 'shot_finished'))
        # The shot is over: tell the queue manager.
        if done:
            notify_queue.put('done')
        else:
            # Not actual recursion: this only queues another call, to run after this
            # one returns.
            self.wait_until_done(notify_queue)
