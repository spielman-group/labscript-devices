"""Runviewer draws the script's time across waits.

A secondary's outputs change at their script times whether a shared clock line or
a trigger line resumes it, and no drawn time runs backward, with waits off the
master's grid that round down, up and from a tie, one called out of order.
"""
import textwrap
import unittest

import labscript_utils.h5_lock  # must precede h5py, as labscript itself does
import h5py
import numpy as np
from labscript_utils import device_registry
from labscript_utils.connections import ConnectionTable

from test_compile_device_tables import CompileTestCase


class SecondaryAcrossWaitsTests(CompileTestCase):
    shot = textwrap.dedent(
        '''
        from labscript import start, stop, wait, DigitalOut
        from labscript_devices.PrawnBlaster.labscript_devices import PrawnBlaster
        from labscript_devices.PrawnDO.labscript_devices import PrawnDO
        from labscript_devices.NI_DAQmx.models.NI_PCI_6534 import NI_PCI_6534

        PrawnBlaster(name='master', com_port='COM1')
        line = master.clocklines[0]
        PrawnDO(name='on_line', clock_line=line, com_port='COM2')
        NI_PCI_6534(name='ni', parent_device=line, clock_terminal='/ni/PFI0')
        PrawnDO(name='on_trigger', trigger_device=ni, trigger_connection='port0/line0')
        DigitalOut('shared', ni, 'port0/line1')
        DigitalOut('line_out', on_line.outputs, 'do1')
        DigitalOut('trigger_out', on_trigger.outputs, 'do1')

        start()
        # On a 20 ns grid, 20.006 us rounds down, 30.014 us up, and 40.03 us is a
        # tie, which labscript rounds to even, up.
        waits = [10e-6, 20.006e-6, 30.014e-6, 40.03e-6]
        for n in range(4):
            for out in (line_out, trigger_out):
                out.go_high(10e-6 * n + 5e-6)
                out.go_low(10e-6 * n + 7e-6)
        # One wait called out of time order.
        for n in (0, 1, 3, 2):
            wait(f'wait {n}', waits[n])
        shared.go_high(39.9e-6)
        line_out.go_high(45e-6)
        trigger_out.go_high(45e-6)
        stop(50e-6)
        '''
    )

    def test_a_secondary_changes_at_its_script_times_across_waits(self):
        self.compile_the_shot()
        table = ConnectionTable(self.run_file)
        traces = {}

        def load(device, clock=None):  # as runviewer walks the devices
            parser = device_registry.get_runviewer_parser(device.device_class)
            add = lambda name, trace, *args: traces.update({name: trace})
            for name, trace in parser(self.run_file, device).get_traces(add, clock).items():
                for child in table.find_by_name(name).child_list.values():
                    load(child, trace)

        load(table.find_by_name('master'))
        for name, (times, values) in traces.items():
            self.assertTrue(np.all(np.diff(times) >= 0), f'{name} runs backward')
        for name in ('line_out', 'trigger_out'):
            times, values = traces[name]
            changes = times[1:][np.diff(values) != 0] * 1e6
            np.testing.assert_allclose(changes, [5, 7, 15, 17, 25, 27, 35, 37, 45], atol=1e-6)


if __name__ == '__main__':
    unittest.main()
