
import os
import sys
import warnings

from labscript_utils.versions import package_version

__version__ = package_version(__package__)

from labscript_utils.device_registry import *


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
