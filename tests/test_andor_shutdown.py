#####################################################################
#                                                                   #
# /tests/test_andor_shutdown.py                                     #
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
import ctypes
import threading
import unittest
from unittest import mock

# The SDK module loads Andor's library when imported; a mock stands in for it.
with mock.patch.object(ctypes.cdll, 'LoadLibrary'):
    import labscript_devices.AndorSolis.andor_sdk.andor_utils as andor_utils


class ShutdownTests(unittest.TestCase):
    def shut_down(self, set_functions):
        """Shut down a camera on a fake SDK, and return the SDK calls in order."""
        calls = []
        camera = andor_utils.AndorCam.__new__(andor_utils.AndorCam)
        camera.armed = False
        camera.setfuncs = set_functions
        camera.acquisition_attributes = dict(
            camera.default_acquisition_attrs, shutter_output='high'
        )
        with mock.patch.multiple(
            andor_utils,
            SetShutter=lambda *args: calls.append(('SetShutter', args)),
            CoolerOFF=lambda: calls.append(('CoolerOFF',)),
            ShutDown=lambda: calls.append(('ShutDown',)),
        ):
            camera.shutdown()
        return calls

    def test_the_shutter_closes_and_the_cooler_stops_before_the_camera_shuts_down(self):
        self.assertEqual(
            self.shut_down(['TEMPERATURE']),
            [('SetShutter', (1, 2, 20, 20)), ('CoolerOFF',), ('ShutDown',)],
        )

    def test_a_camera_that_cannot_set_its_temperature_is_not_sent_cooleroff(self):
        self.assertEqual(
            [call[0] for call in self.shut_down([])], ['SetShutter', 'ShutDown']
        )

    def test_a_camera_armed_but_never_started_shuts_down_after_an_abort(self):
        calls = []
        camera = andor_utils.AndorCam.__new__(andor_utils.AndorCam)
        camera.chatty = False
        camera._abort_lock = threading.Lock()
        camera.armed = True
        camera.setfuncs = []
        camera.acquisition_attributes = dict(camera.default_acquisition_attrs)
        with mock.patch.multiple(
            andor_utils,
            AbortAcquisition=lambda: calls.append('AbortAcquisition'),
            GetStatus=lambda: 'DRV_IDLE',
            SetShutter=lambda *args: calls.append('SetShutter'),
            ShutDown=lambda: calls.append('ShutDown'),
        ):
            camera.abort_acquisition()
            camera.shutdown()
        self.assertEqual(calls[-1], 'ShutDown')


if __name__ == '__main__':
    unittest.main()
