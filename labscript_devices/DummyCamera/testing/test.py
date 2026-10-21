"""An absorption image with no hardware behind it.

Make `atom_number` and `cloud_radius` globals in runmanager and the images in the
shot file follow them; the values below apply until you do, so this compiles as it
stands. BLACS acquires the images as it does any camera's, and a lyse script reads
them from images/side/absorption as it reads any camera's.

The physics is all in `absorption_frame`: the camera only calls a function on its
own pixels and stores what comes back.
"""
import builtins

import numpy as np

from labscript import *
from labscript.remote import RemoteBLACS
from labscript_devices.DummyPseudoclock.labscript_devices import DummyPseudoclock
from labscript_devices.DummyIntermediateDevice.labscript_devices import DummyIntermediateDevice
from labscript_devices.DummyCamera.labscript_devices import DummyCamera

# labscript_init('test.h5', new=True, overwrite=True)

# The cloud these images show. A shot's globals are in builtins, so a global of the
# same name wins; these values apply when there is none.
atom_number = getattr(builtins, 'atom_number', 2.0e5)
cloud_radius = getattr(builtins, 'cloud_radius', 60.0)  # Gaussian sigma, micrometres

# The resonant absorption cross section of Rb-87 on the D2 line, in um^2.
CROSS_SECTION = 0.2907


def absorption_frame(X, Y, atoms):
    """A frame of an absorption image in counts, with the cloud if `atoms`."""
    # X and Y are in micrometres in the object plane, so lengths here are microns.
    probe = 8000.0 * np.exp(-(X ** 2 + Y ** 2) / (2 * 400.0 ** 2))
    if not atoms:
        return probe
    peak_density = atom_number / (2 * np.pi * cloud_radius ** 2)
    column_density = peak_density * np.exp(
        -(X ** 2 + Y ** 2) / (2 * cloud_radius ** 2)
    )
    return probe * np.exp(-CROSS_SECTION * column_density)


DummyPseudoclock('pseudoclock')
DummyIntermediateDevice('intermediatedevice', parent_device=pseudoclock.clockline)
Trigger('camera_trigger', parent_device=intermediatedevice, connection='do0')

RemoteBLACS('test_remote', 'localhost')
DummyCamera(
    'camera',
    camera_trigger,
    'trigger',
    orientation='side',
    trigger_duration=0.01,
    pixel_size=[5.2, 5.2],
    magnification=2.0,
    camera_attributes={'Width': 512, 'Height': 512, 'PixelFormat': 'Mono16'},
    worker=test_remote,
)

start()

camera.expose(1.0, 'absorption', 'atoms', function=absorption_frame, atoms=True)
camera.expose(1.1, 'absorption', 'probe', function=absorption_frame, atoms=False)
camera.expose(1.2, 'absorption', 'dark', function=lambda X, Y: np.zeros(X.shape))

stop(2)
