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
import unittest
from unittest import mock

from labscript_devices.PrawnBlaster.blacs_workers import PrawnBlasterWorker


class EndOfShotTests(unittest.TestCase):
    """A secondary pseudoclock still running when the transition to manual begins."""

    def worker(self, run_statuses, **workerargs):
        # The board reports these run statuses in turn. BLACS's Worker.run gives
        # the worker its arguments; its once-per-process logging setup and job
        # loop are stood in for, and so is its naming of this process to zlock.
        worker = PrawnBlasterWorker.__new__(PrawnBlasterWorker)
        worker.read_status = lambda: (next(run_statuses), 0)
        worker.mainloop = lambda: None
        workerargs.update(is_master_pseudoclock=False, wait_table=None)
        with mock.patch('labscript_utils.setup_logging.setup_logging'), \
             mock.patch('labscript_utils.excepthook.set_logger'), \
             mock.patch('labscript_utils.ls_zprocess.ProcessTree'):
            worker.run('main_worker', 'prawnblaster', workerargs)
        return worker

    def test_the_transition_waits_for_the_board_to_finish(self):
        run_statuses = iter([2, 2, 2, 0])
        self.assertTrue(self.worker(run_statuses).transition_to_manual())
        self.assertEqual(list(run_statuses), [])

    def test_a_board_that_never_finishes_fails_after_the_timeout_it_is_given(self):
        # 0.2 s of polling every 0.01 s reads fewer than 100 statuses; the 5 s
        # default would run out of them first.
        worker = self.worker(iter([2] * 100), end_of_shot_timeout=0.2)
        with self.assertRaises(TimeoutError):
            worker.transition_to_manual()


if __name__ == '__main__':
    unittest.main()
