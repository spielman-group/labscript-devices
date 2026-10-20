#####################################################################
#                                                                   #
# /labscript_devices/deadline.py                                    #
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
from contextlib import contextmanager
import time


class Deadline:
    """The time by which a device must have done something, so that a worker
    waiting on it raises rather than hangs. Once it passes, it raises a
    TimeoutError: "<device_name> did not <what> within <seconds> s."
    """

    def __init__(self, device_name, what, seconds):
        self.device_name = device_name
        self.what = what
        self.seconds = seconds
        self.end = time.monotonic() + seconds

    def remaining(self):
        """The seconds left, for a library call's own timeout. Raises the
        TimeoutError if none are, since a library takes a timeout of 0 as "do
        not wait", or as "wait forever"."""
        left = self.end - time.monotonic()
        if left <= 0:
            raise self._timed_out()
        return left

    def wait(self, done):
        """Poll ``done()`` every 0.01 s until it returns True."""
        while not done():
            time.sleep(min(0.01, self.remaining()))

    @contextmanager
    def timeout_for(self, *library_errors):
        """Yield the seconds left for a library call's own timeout, and raise the
        deadline's TimeoutError in place of the library's timeout errors."""
        seconds = self.remaining()
        try:
            yield seconds
        except library_errors:
            # The library's timeout was the deadline's, even if it ran out a
            # moment early
            raise self._timed_out() from None

    def _timed_out(self):
        return TimeoutError(
            f"{self.device_name} did not {self.what} within {self.seconds} s."
        )
