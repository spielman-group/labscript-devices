from labscript_devices import lazy_attributes
from .labscript_devices import test_device

__getattr__ = lazy_attributes(
    __name__,
    {
        'blacs_tabs': ['Tab'],
        'blacs_workers': ['Worker'],
        'runviewer_parsers': ['Parser'],
    },
)
