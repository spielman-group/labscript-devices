"""A camera whose images come from a function, and change with the shot's globals.

DummyCamera evaluates each exposure's image function while the shot compiles,
when the globals are in scope, and stores the images in the shot file. Its BLACS
worker hands them back one per grab, so the images reach `images/` through the
save path every camera shares and a lyse script cannot tell them from a real
camera's.

Two things are worth guarding and neither is visible from one end alone. The
images must be stored in the order the triggers arrive rather than the order
expose() was called, because that is the order transition_to_manual matches them
up with the exposures in -- get it wrong and every frame is filed under the wrong
name, silently and plausibly. And the grid the functions are evaluated on must be
in object-plane micrometres, because a function that models a cloud in microns
against a grid of pixel indices produces a perfectly reasonable-looking image of
the wrong size.
"""
import os
import textwrap
import threading
import time
import unittest
from unittest import mock

import numpy as np
import zmq

import labscript_utils.h5_lock  # must precede h5py, as labscript itself does
import h5py

from labscript_devices.DummyCamera.blacs_workers import (
    DummyCameraInterface,
    DummyCameraWorker,
)
from labscript_devices.IMAQdxCamera.blacs_workers import IMAQdxCameraWorker
import labscript_devices.common.triggerable_camera.blacs_workers as camera_workers

from test_compile_device_tables import CompileTestCase

try:
    import lyse
except ImportError:
    # lyse is not a dependency of labscript_devices. Where it is installed, the
    # last test below reads the images the way an analysis script would.
    lyse = None


PREAMBLE = textwrap.dedent(
    '''
    import numpy as np
    from labscript import start, stop, Trigger
    from labscript_devices.DummyPseudoclock.labscript_devices import (
        DummyPseudoclock,
    )
    from labscript_devices.DummyIntermediateDevice.labscript_devices import (
        DummyIntermediateDevice,
    )
    from labscript_devices.DummyCamera.labscript_devices import DummyCamera

    DummyPseudoclock(name='pseudoclock')
    DummyIntermediateDevice(
        name='intermediate_device', parent_device=pseudoclock.clockline
    )
    Trigger(
        name='camera_trigger',
        parent_device=intermediate_device,
        connection='port0/line0',
    )
    DummyCamera(
        name='camera',
        parent_device=camera_trigger,
        connection='trigger',
        trigger_duration=0.01,
        camera_attributes={'Width': 64, 'Height': 48, 'PixelFormat': 'Mono16'},
        pixel_size=[5.0, 5.0],
        magnification=2.0,
    )
    '''
)


# An absorption image's three frames, from one function called three ways.
# 'optical_density' is a global of the shot: nothing passes it in, it is simply
# in scope by the time the function is called.
ABSORPTION_SHOT = PREAMBLE + textwrap.dedent(
    '''
    def absorption_frame(X, Y, atoms):
        """A probe beam, with a cloud absorbed out of it when atoms is True."""
        probe = 1000.0 * np.exp(-(X ** 2 + Y ** 2) / (2 * 60.0 ** 2))
        if not atoms:
            return probe
        cloud = np.exp(-(X ** 2 + Y ** 2) / (2 * 15.0 ** 2))
        return probe * np.exp(-optical_density * cloud)

    start()
    # Exposed out of time order on purpose.
    camera.expose(0.3, 'absorption', 'dark', function=lambda X, Y: np.zeros(X.shape))
    camera.expose(0.1, 'absorption', 'atoms', function=absorption_frame, atoms=True)
    camera.expose(0.2, 'absorption', 'probe', function=absorption_frame, atoms=False)
    stop(1.0)
    '''
)


# One frame holding the x coordinate itself, shifted so none of it clips.
COORDINATE_SHOT = PREAMBLE + textwrap.dedent(
    '''
    start()
    camera.expose(0.1, 'grid', 'x', function=lambda X, Y: X - X.min())
    stop(1.0)
    '''
)


# One frame with no function at all.
DEFAULT_IMAGE_SHOT = PREAMBLE + textwrap.dedent(
    '''
    start()
    camera.expose(0.1, 'an exposure')
    stop(1.0)
    '''
)


# A pixel deeper than the sensor holds, and one below zero.
SATURATION_SHOT = PREAMBLE.replace("'Mono16'", "'Mono8'") + textwrap.dedent(
    '''
    start()
    camera.expose(
        0.1,
        'bright',
        function=lambda X, Y: np.where(X < 0, -5.0, 1000.0),
    )
    stop(1.0)
    '''
)


# A camera told to save none of its attributes to the shot file.
NO_SAVED_ATTRIBUTES_SHOT = ABSORPTION_SHOT.replace(
    "camera_attributes={'Width': 64, 'Height': 48, 'PixelFormat': 'Mono16'},",
    "camera_attributes={'Width': 64, 'Height': 48, 'PixelFormat': 'Mono16'},\n"
    "        saved_attribute_visibility_level=None,",
)


# A function whose arithmetic goes non-finite somewhere.
NOT_FINITE_SHOT = PREAMBLE + textwrap.dedent(
    '''
    start()
    camera.expose(
        0.1, 'nan', function=lambda X, Y: np.full(X.shape, np.nan)
    )
    stop(1.0)
    '''
)


# A camera whose attributes never say how big its images are.
NO_SENSOR_SIZE_SHOT = PREAMBLE.replace(
    "camera_attributes={'Width': 64, 'Height': 48, 'PixelFormat': 'Mono16'},",
    "camera_attributes={'PixelFormat': 'Mono16'},",
) + textwrap.dedent(
    '''
    start()
    camera.expose(0.1, 'an exposure')
    stop(1.0)
    '''
)


# A function that does not return an image the size of the sensor.
WRONG_SHAPE_SHOT = PREAMBLE + textwrap.dedent(
    '''
    start()
    camera.expose(0.1, 'wrong', function=lambda X, Y: np.zeros((2, 2)))
    stop(1.0)
    '''
)


class DummyCameraTestCase(CompileTestCase):
    """CompileTestCase that can compile the shot more than once, with globals.

    A run file carrying globals is what runmanager hands the compiler, and
    compiling the same shot twice with a global changed is the only way to see
    whether the images followed it.
    """

    worker_class = DummyCameraWorker

    def setUp(self):
        super().setUp()
        self.shot_count = 0

    def compile_with_globals(self, **shot_globals):
        """Compile the shot from a fresh run file carrying these globals."""
        self.run_file = os.path.join(self.directory, 'shot_%d.h5' % self.shot_count)
        self.shot_count += 1
        with h5py.File(self.run_file, 'w') as f:
            group = f.create_group('globals')
            for name, value in shot_globals.items():
                group.attrs[name] = value
        self.compile_the_shot()
        with h5py.File(self.run_file, 'r') as f:
            return f['devices/camera/IMAGES'][:]

    def run_the_shot(self, **shot_globals):
        """Compile the shot and have a worker acquire and save its images.

        Returns the images the compile produced, so that what the shot file
        ends up holding can be compared against them.
        """
        worker, compiled = self.start_the_shot(**shot_globals)
        worker.transition_to_manual()
        return compiled

    def start_the_shot(self, **shot_globals):
        """Compile the shot, and return a worker acquiring it, and the images."""
        compiled = self.compile_with_globals(**shot_globals)
        worker = self.new_worker()
        worker.transition_to_buffered('camera', self.run_file, {}, True)
        return worker, compiled

    def new_worker(self, context=None, image_receiver_port=0):
        """Start a worker as BLACS does, sending its images to `context`'s socket,
        by default an :obj:`AZMQContext`'s."""
        worker = self.started_worker = self.worker_class.__new__(self.worker_class)
        # What BLACS passes a camera worker when it starts it:
        worker.device_name = 'camera'
        worker.serial_number = 0x0
        worker.orientation = None
        worker.camera_attributes = {'Width': 64, 'Height': 48}
        worker.manual_mode_camera_attributes = {}
        worker.parent_host = '127.0.0.1'
        worker.image_receiver_port = image_receiver_port
        worker.mock = False
        with mock.patch.object(camera_workers, 'Context', context or AZMQContext):
            worker.init()
        return worker


class AbsorptionImageTests(DummyCameraTestCase):
    shot = ABSORPTION_SHOT

    def test_one_image_is_compiled_for_each_exposure(self):
        images = self.compile_with_globals(optical_density=1.0)

        # Height by width, as an image is, and as the camera attributes say.
        self.assertEqual(images.shape, (3, 48, 64))
        self.assertEqual(images.dtype, np.dtype('uint16'))

    def test_the_images_are_stored_in_the_order_the_triggers_arrive(self):
        images = self.compile_with_globals(optical_density=1.0)

        atoms, probe, dark = images
        # The dark frame was exposed first and is last here, because it is the
        # last of the three in time.
        self.assertEqual(dark.max(), 0)
        # The atoms frame is the probe with a cloud taken out of it.
        self.assertLess(atoms.sum(), probe.sum())
        self.assertEqual(atoms[0, 0], probe[0, 0])

    def test_the_images_follow_a_global_the_function_uses(self):
        thin = self.compile_with_globals(optical_density=0.5)
        thick = self.compile_with_globals(optical_density=3.0)

        # A denser cloud absorbs more, in the atoms frame only.
        self.assertLess(thick[0].sum(), thin[0].sum())
        np.testing.assert_array_equal(thick[1], thin[1])
        np.testing.assert_array_equal(thick[2], thin[2])


class CoordinateGridTests(DummyCameraTestCase):
    shot = COORDINATE_SHOT

    def test_the_grid_is_the_object_plane_in_micrometres(self):
        images = self.compile_with_globals()

        x = images[0]
        # 64 pixels of 5 um at 2x magnification: 2.5 um apart in the object
        # plane, spanning 63 of those from the first pixel to the last.
        self.assertEqual(x[0, 0], 0)
        self.assertEqual(x[0, -1], int(63 * 5.0 / 2.0))
        # x does not vary down a column.
        np.testing.assert_array_equal(x[0], x[-1])


class DefaultImageTests(DummyCameraTestCase):
    shot = DEFAULT_IMAGE_SHOT

    def test_an_exposure_with_no_function_gets_a_blank_frame(self):
        images = self.compile_with_globals()

        # A real image, of nothing: the camera models nothing on its own
        # account, so with no function to ask there is nothing in the frame.
        self.assertEqual(images.shape, (1, 48, 64))
        self.assertEqual(images.dtype, np.dtype('uint16'))
        self.assertEqual(images[0].max(), 0)


class RejectedFunctionTests(DummyCameraTestCase):
    """What the camera does with a function it cannot store the output of."""

    shot = NOT_FINITE_SHOT

    def test_a_function_returning_a_nan_stops_the_compile(self):
        # np.clip passes a NaN through and the cast to counts is undefined, so
        # without this the shot file gets a plausible-looking frame of zeros.
        with self.assertRaises(ValueError):
            self.compile_with_globals()


class SensorSizeTests(DummyCameraTestCase):
    shot = NO_SENSOR_SIZE_SHOT

    def test_a_camera_never_told_its_size_stops_before_the_shot_file_is_written(self):
        # Raised from the constructor, not from generate_code: a failure there
        # leaves the shot file half written and unable to be compiled again.
        with self.assertRaises(ValueError):
            self.compile_with_globals()

        with h5py.File(self.run_file, 'r') as f:
            self.assertNotIn('devices', f)


class AnImageSocket:
    """The socket the worker sends each acquired frame to the BLACS tab down.

    Standing in for it is what lets the real worker methods run with no tab at
    the other end. It answers the way the tab does, so the code that sends the
    frames is the real one too.
    """

    def __init__(self):
        self.images = []

    def connect(self, address):
        pass

    def setsockopt(self, option, value):
        pass

    def poll(self, timeout):
        return True

    def send_json(self, metadata, flags=0):
        self.metadata = metadata

    def send(self, image, copy=True):
        self.images.append(np.array(image))

    def recv(self):
        return b'ok'


class AZMQContext:
    """Hands out :obj:`AnImageSocket` in place of a real ZMQ context."""

    def socket(self, kind):
        return AnImageSocket()


class SavedImageTests(DummyCameraTestCase):
    """Where the images end up once BLACS has run the shot.

    transition_to_buffered and transition_to_manual are the real ones, inherited
    whole from TriggerableCameraWorker. The only thing stood in for is the
    socket carrying each frame to the tab, which needs a tab at the other end.
    So what these tests read is the layout an analysis script meets.
    """

    shot = ABSORPTION_SHOT

    def test_the_images_are_saved_where_a_real_camera_saves_them(self):
        self.run_the_shot(optical_density=2.0)

        with h5py.File(self.run_file, 'r') as f:
            group = f['images/camera/absorption']
            frames = {name: group[name][:] for name in group}
            attrs = dict(f['images/camera'].attrs)

        self.assertEqual(set(frames), {'atoms', 'probe', 'dark'})
        for frame in frames.values():
            self.assertEqual(frame.shape, (48, 64))
            self.assertEqual(frame.dtype, np.dtype('uint16'))
        self.assertEqual(attrs['camera'], 'camera')
        self.assertFalse(attrs['failed_shot'])

    def test_each_frame_is_saved_under_the_exposure_that_asked_for_it(self):
        compiled = self.run_the_shot(optical_density=2.0)

        with h5py.File(self.run_file, 'r') as f:
            group = f['images/camera/absorption']
            np.testing.assert_array_equal(group['atoms'][:], compiled[0])
            np.testing.assert_array_equal(group['probe'][:], compiled[1])
            np.testing.assert_array_equal(group['dark'][:], compiled[2])

    def test_the_saved_images_are_marked_as_mock_data(self):
        self.run_the_shot(optical_density=2.0)

        with h5py.File(self.run_file, 'r') as f:
            attrs = dict(f['images/camera'].attrs)

        self.assertTrue(attrs['mock_data'])

    def test_the_datasets_declare_themselves_to_be_images(self):
        self.run_the_shot(optical_density=2.0)

        with h5py.File(self.run_file, 'r') as f:
            attrs = dict(f['images/camera/absorption/atoms'].attrs)

        self.assertEqual(attrs['CLASS'], b'IMAGE')
        self.assertEqual(attrs['IMAGE_SUBCLASS'], b'IMAGE_GRAYSCALE')

    @unittest.skipIf(lyse is None, 'lyse is not installed')
    def test_an_analysis_script_reads_them_as_it_reads_any_camera_s(self):
        self.run_the_shot(optical_density=2.0)

        run = lyse.Run(self.run_file, no_write=True)
        atoms, probe, dark = run.get_images('camera', 'absorption',
                                            'atoms', 'probe', 'dark')

        optical_density = -np.log(
            (atoms[24, 32] - dark[24, 32]) / (probe[24, 32] - dark[24, 32])
        )
        self.assertAlmostEqual(optical_density, 2.0, delta=0.05)


class SaturationTests(DummyCameraTestCase):
    shot = SATURATION_SHOT

    def test_a_pixel_saturates_at_the_depth_pixelformat_gives(self):
        images = self.compile_with_globals()

        # A real camera saturates rather than wrapping around, and its images
        # are counts, so neither end of this can silently become something else
        # when the image is stored.
        self.assertEqual(images[0].max(), 255)
        self.assertEqual(images[0].min(), 0)


class WrongShapeTests(DummyCameraTestCase):
    shot = WRONG_SHAPE_SHOT

    def test_a_function_returning_the_wrong_shape_stops_the_compile(self):
        with self.assertRaises(ValueError):
            self.compile_with_globals()


class UnsavedAttributeTests(DummyCameraTestCase):
    shot = NO_SAVED_ATTRIBUTES_SHOT

    def test_the_marker_survives_a_camera_that_saves_no_attributes(self):
        # saved_attribute_visibility_level says how much camera metadata to
        # keep, and this camera keeps none of it. The one thing saying these
        # images were made up is not metadata anyone may decide not to keep, so
        # it does not travel that way.
        self.run_the_shot(optical_density=2.0)

        with h5py.File(self.run_file, 'r') as f:
            attrs = dict(f['images/camera'].attrs)

        self.assertTrue(attrs['mock_data'])
        # The rest of them really are switched off.
        self.assertNotIn('Width', attrs)


class AnOldStyleCamera:
    """A camera written as upstream documents one: a plain class that reads its
    attributes one at a time, with no get_attributes_as_dict."""

    def __init__(self, serial_number):
        self._camera = DummyCameraInterface(serial_number)

    def __getattr__(self, name):
        if name == 'get_attributes_as_dict':
            raise AttributeError(name)
        return getattr(self._camera, name)


class AnOldStyleWorker(DummyCameraWorker, IMAQdxCameraWorker):
    """A lab's own worker, subclassing IMAQdxCameraWorker to drive that camera."""

    interface_class = AnOldStyleCamera


class OldStyleCameraTests(DummyCameraTestCase):
    shot = ABSORPTION_SHOT
    worker_class = AnOldStyleWorker

    def test_a_camera_without_the_interface_still_runs_a_shot(self):
        compiled = self.run_the_shot(optical_density=2.0)

        with h5py.File(self.run_file, 'r') as f:
            atoms = f['images/camera/absorption/atoms'][:]
            attrs = dict(f['images/camera'].attrs)

        np.testing.assert_array_equal(atoms, compiled[0])
        self.assertEqual(attrs['Width'], 64)


class PlaybackTests(unittest.TestCase):
    """What the worker's camera does with the images the shot compiled."""

    def setUp(self):
        self.camera = DummyCameraInterface(0x0)
        self.camera.set_attributes({'Width': 5, 'Height': 4})
        self.frames = np.arange(3 * 4 * 5, dtype='uint16').reshape(3, 4, 5)

    def test_the_camera_returns_the_compiled_frames_one_per_grab(self):
        self.camera.load_images(self.frames)

        images = []
        self.camera.grab_multiple(3, images)

        self.assertEqual(len(images), 3)
        for grabbed, compiled in zip(images, self.frames):
            np.testing.assert_array_equal(grabbed, compiled)

    def test_a_second_shot_starts_again_at_the_first_frame(self):
        self.camera.load_images(self.frames)
        self.camera.grab_multiple(3, [])

        self.camera.load_images(self.frames)

        np.testing.assert_array_equal(self.camera.grab(), self.frames[0])

    def test_manual_mode_after_a_shot_does_not_grab_the_shot_again(self):
        # BLACS resumes continuous acquisition after a shot by configuring a
        # continuous acquisition. Without this the first grab of the resumed
        # loop raises, or -- on a shot that ended early -- hands back the
        # leftover frames of the finished shot as though they were live.
        self.camera.load_images(self.frames)
        self.camera.grab_multiple(3, [])

        self.camera.configure_acquisition(continuous=True)

        image = self.camera.grab()
        self.assertEqual(image.shape, (4, 5))
        self.assertEqual(image.max(), 0)

    def test_with_no_shot_loaded_it_returns_a_blank_frame(self):
        # Manual mode: pressing Snap in the tab, with no shot and so no image
        # function. It is still this camera's sensor that answers, and what it
        # answers with is a real image of nothing.
        image = self.camera.grab()

        self.assertEqual(image.shape, (4, 5))
        self.assertEqual(image.dtype, np.dtype('uint16'))
        self.assertEqual(image.max(), 0)



class AStillAcquiringCamera(DummyCameraInterface):
    """A camera whose shot never gets its triggers: grab waits until aborted."""

    aborted_while_grabbing = None
    closed_while_grabbing = None

    def __init__(self, serial_number=None):
        super().__init__(serial_number)
        self.grabbing = threading.Event()

    def grab(self):
        self.grabbing.set()
        while not self._abort_acquisition:
            time.sleep(0.01)
        self.grabbing.clear()
        return super().grab()

    def abort_acquisition(self):
        self.aborted_while_grabbing = self.grabbing.is_set()
        super().abort_acquisition()

    def close(self):
        self.closed_while_grabbing = self.grabbing.is_set()


class AStillAcquiringWorker(DummyCameraWorker):
    interface_class = AStillAcquiringCamera


class ShutdownTests(DummyCameraTestCase):
    shot = ABSORPTION_SHOT
    worker_class = AStillAcquiringWorker

    def test_shutting_down_mid_shot_ends_the_acquisition_before_closing_the_camera(self):
        worker, _ = self.start_the_shot(optical_density=1.0)
        acquisition = worker.acquisition_thread
        self.assertTrue(worker.camera.grabbing.wait(timeout=5))

        worker.shutdown()

        self.assertIs(worker.camera.aborted_while_grabbing, True)
        self.assertFalse(acquisition.is_alive())
        self.assertIs(worker.camera.closed_while_grabbing, False)



class ACameraThatRefusesItsAttributes(DummyCameraInterface):
    closed = False

    def set_attributes(self, attributes):
        raise RuntimeError('refused')

    def close(self):
        self.closed = True


class ARefusedWorker(DummyCameraWorker):
    interface_class = ACameraThatRefusesItsAttributes


class FailedInitTests(DummyCameraTestCase):
    shot = ABSORPTION_SHOT
    worker_class = ARefusedWorker

    def test_a_worker_whose_init_failed_still_closes_its_camera(self):
        with self.assertRaises(RuntimeError):
            self.start_the_shot(optical_density=1.0)
        worker = self.started_worker

        worker.shutdown()

        self.assertTrue(worker.camera.closed)



class ARecordingCamera(DummyCameraInterface):
    calls = ()

    def abort_acquisition(self):
        self.calls += ('abort',)
        super().abort_acquisition()

    def stop_acquisition(self):
        self.calls += ('stop',)

    def close(self):
        self.calls += ('close',)


class ARecordingWorker(DummyCameraWorker):
    interface_class = ARecordingCamera


class ArmedWithoutAThreadTests(DummyCameraTestCase):
    """The camera is armed before its acquisition thread runs: abort disarms it."""

    shot = ABSORPTION_SHOT
    worker_class = ARecordingWorker

    def abort_after_a_failed_start(self, failure):
        with mock.patch.object(camera_workers.threading, 'Thread', failure):
            with self.assertRaises(RuntimeError):
                self.start_the_shot(optical_density=1.0)
        worker = self.started_worker
        worker.abort()
        return worker.camera.calls

    def test_abort_disarms_a_camera_whose_thread_was_never_made(self):
        def no_thread(*args, **kwargs):
            raise RuntimeError('no thread')

        self.assertEqual(self.abort_after_a_failed_start(no_thread), ('abort', 'stop'))

    def test_abort_disarms_a_camera_whose_thread_never_started(self):
        class AThreadThatWillNotStart(threading.Thread):
            def start(self):
                raise RuntimeError('not started')

        self.assertEqual(
            self.abort_after_a_failed_start(AThreadThatWillNotStart), ('abort', 'stop')
        )

    def test_shutdown_disarms_a_camera_interrupted_while_it_armed(self):
        with mock.patch.object(
            ARecordingCamera, 'configure_acquisition', side_effect=KeyboardInterrupt
        ):
            with self.assertRaises(KeyboardInterrupt):
                self.start_the_shot(optical_density=1.0)
        worker = self.started_worker

        worker.shutdown()

        self.assertEqual(worker.camera.calls, ('abort', 'stop', 'close'))


class AnAbsentTabTests(DummyCameraTestCase):
    shot = ABSORPTION_SHOT
    worker_class = ARecordingWorker

    def test_continuous_acquisition_stops_though_the_tab_never_replies(self):
        # The suite's secure context, as BLACS's image receiver uses.
        tab = camera_workers.Context().socket(zmq.REP)
        self.addCleanup(tab.close, linger=0)
        port = tab.bind_to_random_port('tcp://127.0.0.1')
        worker = self.new_worker(camera_workers.Context, port)
        worker.start_continuous(None)
        acquiring = worker.continuous_thread
        self.assertTrue(tab.poll(5000))
        tab.recv_multipart()  # The first frame, which is never answered.

        errors = []

        def shut_down():
            try:
                worker.shutdown()
            except Exception as e:
                errors.append(e)

        stopping = threading.Thread(target=shut_down, daemon=True)
        stopping.start()
        stopping.join(5)

        self.assertFalse(stopping.is_alive())
        if errors:
            raise errors[0]
        self.assertFalse(acquiring.is_alive())
        self.assertEqual(worker.camera.calls[-1], 'close')


class AnInterruptedStartTests(DummyCameraTestCase):
    shot = ABSORPTION_SHOT
    worker_class = AStillAcquiringWorker

    def test_abort_ends_an_acquisition_interrupted_once_its_thread_started(self):
        class AnInterruptedThread(threading.Thread):
            def start(self):
                super().start()
                raise RuntimeError('interrupted')

        with mock.patch.object(camera_workers.threading, 'Thread', AnInterruptedThread):
            with self.assertRaises(RuntimeError):
                self.start_the_shot(optical_density=1.0)
        worker = self.started_worker
        acquiring = worker.acquisition_thread

        worker.abort()

        self.assertFalse(acquiring.is_alive())


if __name__ == '__main__':
    unittest.main()
