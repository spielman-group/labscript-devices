#####################################################################
#                                                                   #
# /labscript_devices/pseudoclock.py                                 #
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
import time

from blacs.device_base_class import DeviceTab
from blacs.tab_base_classes import MODE_BUFFERED, MODE_MANUAL, Worker, define_state


class PseudoclockWorker(Worker):
    """The worker of a pseudoclock device.

    BLACS begins the transition to manual mode when the master pseudoclock has
    finished, and a secondary one may still be running then, so
    ``transition_to_manual`` calls :meth:`wait_for_end_of_shot` first. A master
    whose tab has already seen it finish may skip it.

    ``end_of_shot_timeout`` is how many seconds a board may run on once BLACS
    begins to stop it, by the transition or by an abort. A worker argument sets
    it, and it is 5 s otherwise.
    """

    def shot_finished(self):
        """Return whether the board has finished the shot. A board that cannot
        tell is taken to have finished."""
        return True

    def wait_for_end_of_shot(self, ended=None):
        """Wait until ``ended()``, :meth:`shot_finished` if not given, returns
        True. An abort passes its own test."""
        ended = ended or self.shot_finished
        # Not a class attribute, which BLACS would not let a worker argument set:
        timeout = getattr(self, 'end_of_shot_timeout', 5)
        deadline = time.monotonic() + timeout
        while not ended():
            if time.monotonic() > deadline:
                raise TimeoutError(
                    f"{self.device_name} had not ended the shot within its "
                    f"end_of_shot_timeout of {timeout} s."
                )
            time.sleep(0.01)


class PseudoclockTab(DeviceTab):
    """The tab of a pseudoclock device whose worker says, through its
    ``shot_finished``, whether the shot it started is over. A tab that shows the
    board's status refreshes it in its own state function, on its own timer."""

    @define_state(MODE_BUFFERED, True)
    def start_run(self, notify_queue):
        """Start the device, and tell BLACS through ``notify_queue`` when the
        shot is over."""
        # TODO: This 100ms (+ overhead) limits the minimum time you can have between 2 consecutive wait commands in labscript. Anything faster than this will not be detected properly.
        self.statemachine_timeout_add(100, self.status_monitor, notify_queue)
        yield(self.queue_work(self.primary_worker, 'start_run'))

    @define_state(MODE_BUFFERED | MODE_MANUAL, True)
    def status_monitor(self, notify_queue):
        # An abort leaves the tab in manual mode, and then there is no shot to watch.
        if self.mode == MODE_MANUAL:
            self.statemachine_timeout_remove(self.status_monitor)
            return

        status = yield(self.queue_work(self.primary_worker, 'shot_finished'))
        if status:
            notify_queue.put('done')
            self.statemachine_timeout_remove(self.status_monitor)
            self.shot_over()
        elif status is None:
            # The worker failed. TODO: This is a bit of a hack. We fake a restart
            # in order to notify the queue that something went wrong and that it
            # should abort the shot.
            self.statemachine_timeout_remove(self.status_monitor)
            for f in self._restart_receiver:
                try:
                    f(self.device_name)
                except Exception:
                    self.logger.exception('Could not notify a connected receiver function')

    def shot_over(self):
        """Called once the worker says the shot it started is over."""
