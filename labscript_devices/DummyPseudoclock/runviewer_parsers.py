import labscript_utils.h5_lock  # noqa: F401
import h5py
from labscript_devices.common.runviewer import PseudoclockParser

from .labscript_devices import DummyPseudoclock


class DummyPseudoclockParser(PseudoclockParser):
    clock_resolution = DummyPseudoclock.clock_resolution
    trigger_delay = DummyPseudoclock.trigger_delay

    def get_traces(self, add_trace, clock=None):
        with h5py.File(self.path, 'r') as f:
            pulse_program = f[f'devices/{self.name}/PULSE_PROGRAM'][:]

        # Each tick is high for half its period, then low for the other half.
        clock_factor = self.clock_resolution / 2.
        segments = [[]]
        for row in pulse_program:
            # A period of 0 is a wait, with 1 rep, or the stop instruction, with none.
            if row['period'] == 0:
                if row['reps'] == 1:
                    segments.append([])
            else:
                half = row['period'] * clock_factor
                segments[-1].append((half, half, row['reps']))

        trace = self.clock_trace(clock, self.trigger_delay, segments)
        return self.add_clock_lines(add_trace, trace, 'internal')
