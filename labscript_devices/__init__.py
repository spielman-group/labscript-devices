
import importlib
import os
import sys

from labscript_utils.versions import package_version

__version__ = package_version(__package__)

from labscript_utils.device_registry import *


def lazy_attributes(package, names_by_submodule):
    """Return a module ``__getattr__`` that imports each listed name from its
    submodule of ``package`` only when it is first asked for.

    A device package uses it so that its tab, worker and parser stay importable
    from the package without a compile importing BLACS::

        __getattr__ = lazy_attributes(__name__, {'blacs_tabs': ['MyTab']})
    """
    submodules = {
        name: submodule
        for submodule, names in names_by_submodule.items()
        for name in names
    }

    def __getattr__(name):
        if name not in submodules:
            raise AttributeError(f"module {package!r} has no attribute {name!r}")
        return getattr(importlib.import_module(f'{package}.{submodules[name]}'), name)

    return __getattr__


if __name__ == '__main__':
    # If this module is run as __main__, make sure importing submodules still works,
    # without double-importing this file:
    __path__ = [os.path.dirname(os.path.abspath(__file__))]
    sys.modules['labscript_devices'] = sys.modules['__main__']
