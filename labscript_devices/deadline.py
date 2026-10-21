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
    """A limit on how long a worker waits for its device to do something.

    Once it has passed, :meth:`remaining` and :meth:`timeout_for` raise a
    TimeoutError, "<device_name> did not <what> within <seconds> s.", and so does
    :meth:`wait` at its next poll that returns False.
    """

    def __init__(self, device_name, what, seconds):
        """
        Parameters
        ----------
        device_name : str
            The device's name, as the error gives it.
        what : str
            What the device is to do, completing "did not ...": ``'end the shot'``.
        seconds : float
            How long the device has, from now.
        """
        self.device_name = device_name
        self.what = what
        self.seconds = seconds
        self.end = time.monotonic() + seconds

    def remaining(self):
        """Return the seconds left, for a library call's own timeout.

        Raises the TimeoutError once none are left, since a library may take a
        timeout of 0 as "do not wait" or as "wait forever".
        """
        left = self.end - time.monotonic()
        if left <= 0:
            raise self._timed_out()
        return left

    def wait(self, done):
        """Poll ``done()`` every 0.01 s until it is True.

        The deadline is checked only between polls that return False, so a True
        poll returns even once it has passed; a False one after it raises the
        TimeoutError.
        """
        while not done():
            time.sleep(min(0.01, self.remaining()))

    @contextmanager
    def timeout_for(self, *library_errors):
        """Yield the seconds left for a library call's own timeout.

        Parameters
        ----------
        *library_errors : type
            The library's timeout exceptions. One raised in the block becomes the
            deadline's TimeoutError.
        """
        seconds = self.remaining()
        try:
            yield seconds
        except library_errors:
            # The library's timeout was the deadline's, even if it ran out a
            # moment early.
            raise self._timed_out() from None

    def _timed_out(self):
        return TimeoutError(
            f"{self.device_name} did not {self.what} within {self.seconds} s."
        )
