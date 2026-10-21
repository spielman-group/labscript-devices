"""Drawing a secondary pseudoclock's program in runviewer across waits.

Runviewer draws the script's time, in which a wait takes no time, so each output
of a secondary changes at the time the script gave it, before and after every
wait. The PrawnDO here is clocked on a line it shares with another device, which
ticks just before the last wait, and also triggered from an NI line.
"""
import textwrap
import unittest

import labscript_utils.h5_lock  # must precede h5py, as labscript itself does
import h5py
import numpy as np

from labscript_utils import device_registry
from labscript_utils.connections import ConnectionTable

from test_compile_device_tables import CompileTestCase


WAITS_SHOT = textwrap.dedent(
    '''
    from labscript import start, stop, wait, DigitalOut
    from labscript_devices.PrawnBlaster.labscript_devices import PrawnBlaster
    from labscript_devices.PrawnDO.labscript_devices import PrawnDO
    from labscript_devices.NI_DAQmx.models.NI_PCIe_6363 import NI_PCIe_6363
    from labscript_devices.NI_DAQmx.models.NI_PCI_6534 import NI_PCI_6534

    PrawnBlaster(name='prawnblaster', num_pseudoclocks=2, com_port='COM1')
    PrawnDO(name='on_line', clock_line=prawnblaster.clocklines[0], com_port='COM2')
    NI_PCI_6534(
        name='sharing',
        parent_device=prawnblaster.clocklines[0],
        clock_terminal='/sharing/PFI0',
        MAX_name='sharing',
    )
    NI_PCIe_6363(
        name='triggering',
        parent_device=prawnblaster.clocklines[1],
        clock_terminal='/triggering/PFI0',
        MAX_name='triggering',
    )
    PrawnDO(
        name='on_trigger',
        trigger_device=triggering,
        trigger_connection='port0/line0',
        com_port='COM3',
    )
    # Even numbers of digital outputs, which the DAQmx library needs.
    DigitalOut('sharing_out', sharing, 'port0/line0')
    DigitalOut('sharing_spare', sharing, 'port0/line1')
    DigitalOut('triggering_spare', triggering, 'port0/line1')
    DigitalOut('line_out', on_line.outputs, 'do1')
    DigitalOut('trigger_out', on_trigger.outputs, 'do1')

    start()
    for n, t in enumerate([10e-6, 20e-6, 30e-6, 40e-6]):
        line_out.go_high(t - 5e-6)
        trigger_out.go_high(t - 5e-6)
        line_out.go_low(t - 3e-6)
        trigger_out.go_low(t - 3e-6)
        wait(f'wait {n}', t)
    sharing_out.go_high(39.9e-6)
    line_out.go_high(45e-6)
    trigger_out.go_high(45e-6)
    stop(50e-6)
    '''
)

# The script's changes of each PrawnDO output, in microseconds.
CHANGES = [5, 7, 15, 17, 25, 27, 35, 37, 45]


def draw(path):
    """Return every trace, walking the devices from the master as runviewer does."""
    connection_table = ConnectionTable(path)
    with h5py.File(path, 'r') as f:
        master = f['connection table'].attrs['master_pseudoclock']
    traces = {}

    def load(device, clock=None):
        parser = device_registry.get_runviewer_parser(device.device_class)
        added = {}
        returned = parser(path, device).get_traces(
            lambda name, trace, *args: added.update({name: trace}), clock
        )
        traces.update(added)
        for name, trace in returned.items():
            for child in connection_table.find_by_name(name).child_list.values():
                load(child, trace)

    load(connection_table.find_by_name(master))
    return traces


class SecondaryAcrossWaitsTests(CompileTestCase):
    shot = WAITS_SHOT

    def setUp(self):
        super().setUp()
        self.compile_the_shot()
        self.traces = draw(self.run_file)

    def assert_drawn_at_script_times(self, output):
        times, values = self.traces[output]
        self.assertTrue(np.all(np.diff(times) >= 0), 'time runs backward')
        changes = times[1:][np.diff(values) != 0]
        np.testing.assert_allclose(changes * 1e6, CHANGES, atol=1e-6)

    def test_a_prawndo_on_a_shared_clock_line_changes_at_its_script_times(self):
        self.assert_drawn_at_script_times('line_out')

    def test_a_triggered_prawndo_changes_at_its_script_times(self):
        self.assert_drawn_at_script_times('trigger_out')


if __name__ == '__main__':
    unittest.main()
