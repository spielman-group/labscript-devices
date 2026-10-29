#####################################################################
#                                                                   #
# /labscript_devices/common/pseudoclock.py                          #
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
from blacs.tab_base_classes import MODE_BUFFERED, MODE_MANUAL, Worker, define_state

from .deadline import Deadline


class PseudoclockWorker(Worker):
    """The worker of a pseudoclock device.

    BLACS begins the transition to manual mode when the master pseudoclock has
    finished, and a secondary one may still be running then, so a subclass's
    ``transition_to_manual`` calls :meth:`wait_for_end_of_shot` first. A master
    whose tab has already seen it finish may skip it.

    ``end_of_shot_timeout`` is how many seconds a board may run on once BLACS
    begins to stop it, by the transition or by an abort. A board's class or a
    worker argument may override it.
    """

    end_of_shot_timeout = 5

    def shot_finished(self):
        """Return whether the board has finished the shot, as `PseudoclockTab` polls.

        A board that cannot tell keeps this default, True.
        """
        return True

    def wait_for_end_of_shot(self, ended=None):
        """Wait for the board to stop.

        Raises a TimeoutError if it runs on past ``end_of_shot_timeout``.

        Parameters
        ----------
        ended : callable, optional
            Returns True once the board has stopped; :meth:`shot_finished` by
            default. An abort passes its own test.
        """
        Deadline(self.device_name, 'end the shot', self.end_of_shot_timeout).wait(
            ended or self.shot_finished
        )


class PseudoclockTab(DeviceTab):
    """The tab of a pseudoclock device whose worker says when the shot is over.

    ``start_run`` starts the worker's ``start_run`` and polls its ``shot_finished``
    every 100 ms. Once that returns True, the tab puts 'done' on the notify queue
    and calls :meth:`shot_over`. If the worker fails instead, BLACS is told the
    device restarted, which aborts the shot. A tab that shows the board's status
    refreshes it in its own state function, on its own timer.
    """

    @define_state(MODE_BUFFERED, True)
    def start_run(self, notify_queue):
        """Start the device, and put 'done' on `notify_queue` when the shot is over."""
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
            # The worker failed. Calling the restart receivers, as a restart does,
            # makes BLACS abort the shot.
            self.statemachine_timeout_remove(self.status_monitor)
            for f in self._restart_receiver:
                try:
                    f(self.device_name)
                except Exception:
                    self.logger.exception(
                        'Could not notify a connected receiver function'
                    )

    def shot_over(self):
        """Called once the worker says the shot it started is over."""
