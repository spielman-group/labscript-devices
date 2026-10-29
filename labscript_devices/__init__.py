
import importlib
import os
import sys
import warnings

from labscript_utils.versions import package_version

__version__ = package_version(__package__)

from labscript_utils.device_registry import *


def lazy_attributes(package, names_by_submodule):
    """Return a module ``__getattr__`` that imports each name when first asked for.

    A device package uses it so that its tab, worker and parser stay importable
    from the package without a compile importing BLACS::

        __getattr__ = lazy_attributes(__name__, {'blacs_tabs': ['MyTab']})

    Parameters
    ----------
    package : str
        The package the ``__getattr__`` belongs to, normally ``__name__``.
    names_by_submodule : dict of str to list of str
        The names to import, under the module that defines them: a submodule of
        `package`, or a dotted path taken as the full module name.
    """
    submodules = {
        name: submodule
        for submodule, names in names_by_submodule.items()
        for name in names
    }

    def __getattr__(name):
        if name not in submodules:
            raise AttributeError(f"module {package!r} has no attribute {name!r}")
        module = submodules[name]
        if '.' not in module:
            module = f'{package}.{module}'
        return getattr(importlib.import_module(module), name)

    return __getattr__


class LegacyAttribute:
    """A class attribute that warns, wherever it is read, that it will be removed."""

    def __init__(self, value, message):
        self.value = value
        self.message = message

    def __get__(self, instance, owner):
        warnings.warn(self.message, FutureWarning, stacklevel=2)
        return self.value


if __name__ == '__main__':
    # If this module is run as __main__, make sure importing submodules still works,
    # without double-importing this file:
    __path__ = [os.path.dirname(os.path.abspath(__file__))]
    sys.modules['labscript_devices'] = sys.modules['__main__']
