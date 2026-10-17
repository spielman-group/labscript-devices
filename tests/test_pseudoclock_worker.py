#####################################################################
#                                                                   #
# /tests/test_pseudoclock_worker.py                                 #
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
import itertools
import unittest

from labscript_devices.PrawnBlaster.blacs_workers import PrawnBlasterWorker


class EndOfShotTests(unittest.TestCase):
    """A secondary pseudoclock still running when the transition to manual begins."""

    def worker(self, run_statuses):
        # Only the board is stood in for: it reports these run statuses in turn.
        worker = PrawnBlasterWorker.__new__(PrawnBlasterWorker)
        worker.device_name = 'prawnblaster'
        worker.wait_table = None
        worker.end_of_shot_timeout = 0.2
        worker.read_status = lambda: (next(run_statuses), 0)
        return worker

    def test_the_transition_waits_for_the_board_to_finish(self):
        run_statuses = iter([2, 2, 2, 0])
        self.assertTrue(self.worker(run_statuses).transition_to_manual())
        self.assertEqual(list(run_statuses), [])

    def test_a_board_that_never_finishes_fails_the_transition(self):
        with self.assertRaises(TimeoutError):
            self.worker(itertools.repeat(2)).transition_to_manual()


if __name__ == '__main__':
    unittest.main()
