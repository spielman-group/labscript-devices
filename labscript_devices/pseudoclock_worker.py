#####################################################################
#                                                                   #
# /labscript_devices/pseudoclock_worker.py                          #
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

from blacs.tab_base_classes import Worker


class PseudoclockWorker(Worker):
    """The worker of a pseudoclock device.

    BLACS begins the transition to manual mode when the master pseudoclock has
    finished, and a secondary one may still be running then, so
    ``transition_to_manual`` calls :meth:`wait_for_end_of_shot` first. A master
    whose tab has already seen it finish may skip it.

    ``end_of_shot_timeout`` is how many seconds a board may run on once the
    transition begins. A worker argument or connection table property sets it,
    and it is 5 s otherwise.
    """

    def shot_finished(self):
        """Return whether the board has finished the shot. A board that cannot
        tell is taken to have finished."""
        return True

    def wait_for_end_of_shot(self):
        # Not a class attribute, which BLACS would not let a worker argument set:
        timeout = getattr(self, 'end_of_shot_timeout', 5)
        deadline = time.monotonic() + timeout
        while not self.shot_finished():
            if time.monotonic() > deadline:
                raise TimeoutError(
                    f"{self.device_name} had not finished the shot "
                    f"{timeout} s after the transition to manual "
                    "mode began. Is it being triggered?"
                )
            time.sleep(0.01)
