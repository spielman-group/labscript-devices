
import os
import sys

from labscript_utils.versions import package_version

__version__ = package_version(__package__)

from labscript_utils.device_registry import *


if __name__ == '__main__':
    # If this module is run as __main__, make sure importing submodules still works,
    # without double-importing this file:
    __path__ = [os.path.dirname(os.path.abspath(__file__))]
    sys.modules['labscript_devices'] = sys.modules['__main__']
