# The labscript-side names are imported here and make up __all__, so a star
# import of this package never loads BLACS. Its tab, worker and parser names
# load only when asked for by name.
from labscript_devices import lazy_attributes
from .labscript_devices import (
    TestDevice,
    test_device,
)

__all__ = [
    'TestDevice',
    'test_device',
]

__getattr__ = lazy_attributes(
    __name__,
    {
        'blacs_tabs': [
            'TestDeviceTab',
        ],
        'blacs_workers': [
            'TestDeviceWorker',
        ],
        'runviewer_parsers': [
            'TestDeviceParser',
        ],
    },
)
