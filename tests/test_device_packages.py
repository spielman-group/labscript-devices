#####################################################################
#                                                                   #
# /tests/test_device_packages.py                                    #
#                                                                   #
# Copyright 2026, JQI                                               #
# Author: Ian Spielman                                              #
#                                                                   #
# This file is part of labscript_devices, in the labscript suite    #
# (see http://labscriptsuite.org), and is licensed under the        #
# Simplified BSD License. See the license.txt file in the root of   #
# the project for the full license.                                 #
#                                                                   #
#####################################################################
import json
import subprocess
import sys
import unittest
from pathlib import Path

import labscript_devices

# Run in a fresh interpreter: it imports each device package as a compile does,
# and names those that brought in BLACS, forgetting BLACS again after each.
PROBE = """
import importlib, json, sys
found = {}
for package in sys.argv[1:]:
    for module in (package, package + '.labscript_devices'):
        importlib.import_module(module)
        blacs = [name for name in sys.modules if name.split('.')[0] == 'blacs']
        if blacs:
            found[module] = sorted(blacs)[:3]
            for name in blacs:
                del sys.modules[name]
print(json.dumps(found))
"""


class CompileImportTests(unittest.TestCase):
    def test_importing_a_device_for_a_compile_never_imports_blacs(self):
        root = Path(labscript_devices.__file__).parent
        packages = sorted(
            f'labscript_devices.{path.parent.name}'
            for path in root.glob('*/labscript_devices.py')
        )
        result = subprocess.run(
            [sys.executable, '-c', PROBE, *packages],
            capture_output=True, text=True, check=True,
        )
        self.assertEqual(json.loads(result.stdout.splitlines()[-1]), {})


if __name__ == '__main__':
    unittest.main()
