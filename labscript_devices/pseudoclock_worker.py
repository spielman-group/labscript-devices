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
    """

    # Seconds a board may run on once the transition to manual mode begins:
    end_of_shot_timeout = 5

    def shot_finished(self):
        """Return whether the board has finished the shot. A board that cannot
        tell is taken to have finished."""
        return True

    def wait_for_end_of_shot(self):
        deadline = time.monotonic() + self.end_of_shot_timeout
        while not self.shot_finished():
            if time.monotonic() > deadline:
                raise TimeoutError(
                    f"{self.device_name} had not finished the shot "
                    f"{self.end_of_shot_timeout} s after the transition to manual "
                    "mode began. Is it being triggered?"
                )
            time.sleep(0.01)
