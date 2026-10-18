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
# and gives for each the BLACS modules it brought in, forgetting them again
# after each, or the vendor library it could not load.
PROBE = """
import importlib, json, sys
results = {}
for package in sys.argv[1:]:
    for module in (package, package + '.labscript_devices'):
        try:
            importlib.import_module(module)
        except OSError as e:
            results[module] = f'OSError: {e}'
        blacs = [name for name in sys.modules if name.split('.')[0] == 'blacs']
        results.setdefault(module, sorted(blacs)[:3])
        for name in blacs:
            del sys.modules[name]
        if isinstance(results[module], str):
            break
print(json.dumps(results))
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
        for module, found in json.loads(result.stdout.splitlines()[-1]).items():
            with self.subTest(module=module):
                # AlazarTechBoard's compile loads the AlazarTech library, so it
                # cannot be checked where that library is not installed.
                alazar = module.startswith('labscript_devices.AlazarTechBoard')
                if isinstance(found, str) and alazar and 'ATSApi' in found:
                    self.skipTest(found)
                self.assertEqual(found, [])


if __name__ == '__main__':
    unittest.main()
