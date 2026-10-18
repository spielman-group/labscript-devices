# The names this package gives. The compile side's are imported here; those of
# BLACS and runviewer load only when asked for, so a compile never imports
# BLACS.
from labscript_devices import (
    BLACS_tab, lazy_attributes, runviewer_parser,
)
from .labscript_devices import (
    Device, LabscriptError, set_passed_properties, test_device,
)

__getattr__ = lazy_attributes(
    __name__,
    {
        'blacs_tabs': [
            'Tab',
        ],
        'blacs_workers': [
            'Worker',
        ],
        'runviewer_parsers': [
            'Parser',
        ],
    },
)
