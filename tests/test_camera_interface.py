"""The contract between a camera worker and the camera object it drives.

TriggerableCameraWorker duck-types its camera: it calls a set of methods and
reaches for two attributes, and nothing declares that set anywhere the worker
can check. A camera missing one of them fails partway through a shot, on
hardware, which is the worst place to find out -- with a NotImplementedError
naming it if it inherits TriggerableCameraInterface, and an AttributeError if
it does not.

The first test here is that list, checked against every camera in the tree. The
rest pin the behaviour of the shared grab_multiple, because each vendor's
acquisition loop is being replaced by it and the replacement has to keep every
one of their failure behaviours exactly: IMAQdx retries on its timeout code and
skips a frame when the shot says not to fail; Pylon and FlyCapture2 retry
forever on their own error classes; Spinnaker and the dummy camera do not retry
at all.
"""
import unittest

from labscript_devices.common.triggerable_camera.blacs_workers import (
    TriggerableCameraInterface,
)
from labscript_devices.IMAQdxCamera.blacs_workers import IMAQdxCameraInterface
from labscript_devices.PylonCamera.blacs_workers import PylonCameraInterface
from labscript_devices.SpinnakerCamera.blacs_workers import SpinnakerCameraInterface
from labscript_devices.FlyCapture2Camera.blacs_workers import FlyCapture2CameraInterface
from labscript_devices.AndorSolis.blacs_workers import AndorSolisInterface
from labscript_devices.DummyCamera.blacs_workers import DummyCameraInterface
from labscript_devices.ThorlabsTSICamera.blacs_workers import ThorlabsTSICameraInterface
from labscript_devices.GenICamCamera.blacs_workers import GenICamCameraInterface


# What TriggerableCameraWorker calls on self.camera that no base can supply,
# because there is nothing generic to say: it is all one vendor's API. A camera
# also writes set_attribute or set_attributes; the interface composes the other.
VENDOR_MUST_WRITE = [
    'grab',
    'configure_acquisition',
    'stop_acquisition',
    'close',
]

# Every camera in the tree.
EVERY_CAMERA = [
    IMAQdxCameraInterface,
    PylonCameraInterface,
    SpinnakerCameraInterface,
    FlyCapture2CameraInterface,
    AndorSolisInterface,
    DummyCameraInterface,
    ThorlabsTSICameraInterface,
    GenICamCameraInterface,
]


def written_by_the_camera(camera, name):
    """Whether this camera writes `name` itself.

    Resolving the name is not enough once every camera inherits
    TriggerableCameraInterface: it supplies a stub for each member of the
    contract, so getattr succeeds whether or not the camera implements it and
    the failure moves to the middle of a shot. What this asks is whether the
    camera brought its own.
    """
    return getattr(camera, name, None) is not getattr(TriggerableCameraInterface, name, None)


class ContractTests(unittest.TestCase):
    # How the vendor cameras are written, not what they do: their SDKs are absent
    # here, so this is the only check that runs on them.
    def test_every_camera_writes_the_members_only_it_can(self):
        for camera in EVERY_CAMERA:
            for name in VENDOR_MUST_WRITE:
                with self.subTest(camera=camera.__name__, member=name):
                    self.assertTrue(
                        written_by_the_camera(camera, name),
                        f'{camera.__name__} does not implement {name}(); it '
                        f'would inherit the stub, which raises mid-shot',
                    )
            with self.subTest(camera=camera.__name__, member='set_attribute'):
                self.assertTrue(
                    written_by_the_camera(camera, 'set_attribute')
                    or written_by_the_camera(camera, 'set_attributes'),
                    f'{camera.__name__} implements neither set_attribute() nor '
                    f'set_attributes()',
                )


class AWaitingForTrigger(Exception):
    """What a camera raises when no frame has arrived yet."""


class ACameraFault(Exception):
    """What a camera's own API raises when something is wrong with it."""


class AScriptedCamera(TriggerableCameraInterface):
    """A camera whose every grab is dictated by the test.

    Each entry of `outcomes` is either an image to return or an exception to
    raise. What the camera considers transient or skippable is set per test, so
    one fake stands in for all five vendors' policies.
    """

    def __init__(self, outcomes, transient=(), skippable=()):
        self.outcomes = list(outcomes)
        self.transient = transient
        self.skippable = skippable
        self.grabs = 0

    def is_transient_grab_error(self, exception):
        return isinstance(exception, self.transient)

    def is_skippable_grab_error(self, exception):
        return isinstance(exception, self.skippable)

    def grab(self):
        self.grabs += 1
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


class GrabMultipleTests(unittest.TestCase):
    def test_a_clean_acquisition_collects_every_frame_in_order(self):
        camera = AScriptedCamera([10, 20, 30])

        images = []
        camera.grab_multiple(3, images)

        self.assertEqual(images, [10, 20, 30])

    def test_a_camera_still_waiting_for_a_trigger_is_asked_again(self):
        # IMAQdx on its timeout code, Pylon on TimeoutException, FlyCapture2 on
        # Fc2error: the shot decides when the trigger comes, so the acquisition
        # waits rather than giving up.
        camera = AScriptedCamera(
            [AWaitingForTrigger(), AWaitingForTrigger(), 10, 20],
            transient=AWaitingForTrigger,
        )

        images = []
        camera.grab_multiple(2, images)

        self.assertEqual(images, [10, 20])
        self.assertEqual(camera.grabs, 4)

    def test_a_camera_that_does_not_retry_lets_the_failure_out(self):
        # Spinnaker and the dummy camera declare nothing transient, so their
        # acquisition fails rather than waiting.
        camera = AScriptedCamera([10, AWaitingForTrigger(), 30])

        with self.assertRaises(AWaitingForTrigger):
            camera.grab_multiple(3, [])

    def test_a_real_fault_ends_the_acquisition(self):
        camera = AScriptedCamera(
            [10, ACameraFault(), 30], transient=AWaitingForTrigger
        )

        with self.assertRaises(ACameraFault):
            camera.grab_multiple(3, [])

    def test_a_shot_told_not_to_fail_gives_up_the_frame_and_carries_on(self):
        # IMAQdx's behaviour under exception_on_failed_shot=False: the frame is
        # lost and the acquisition moves to the next exposure.
        camera = AScriptedCamera(
            [10, ACameraFault(), 30], skippable=ACameraFault
        )
        camera.exception_on_failed_shot = False

        images = []
        camera.grab_multiple(3, images)

        self.assertEqual(images, [10, 30])

    def test_a_shot_told_to_fail_fails_on_the_same_error(self):
        camera = AScriptedCamera(
            [10, ACameraFault(), 30], skippable=ACameraFault
        )
        camera.exception_on_failed_shot = True

        with self.assertRaises(ACameraFault):
            camera.grab_multiple(3, [])

    def test_an_abort_stops_between_frames_and_clears_the_flag(self):
        camera = AScriptedCamera([10, 20, 30])
        camera.abort_acquisition()

        images = []
        camera.grab_multiple(3, images)

        self.assertEqual(images, [])
        self.assertEqual(camera.grabs, 0)
        # Cleared, so the next shot is not aborted before it starts.
        self.assertFalse(camera._abort_acquisition)


if __name__ == '__main__':
    unittest.main()
