import numpy as np
import labscript_utils.h5_lock
import h5py

from blacs.tab_base_classes import Worker
from labscript import LabscriptError
import labscript_utils.properties


class TekScopeWorker(Worker):
    """Arms the scope for each shot, then saves its displayed channels to the shot file."""

    def init(self):
        global TekScope
        from .driver import TekScope

        self.scope = TekScope(self.addr, termination=self.termination)
        manufacturer, model, sn, revision = self.scope.idn.split(',')
        assert manufacturer.lower() == 'tektronix', (
            f"The device matching {self.addr} is a {model} made by {manufacturer}, not by "
            "Tektronix. Set addr to the VISA address of a Tektronix scope."
        )
        print(f'Connected to {model} (SN: {sn})')

    def transition_to_buffered(self, device_name, h5_file, front_panel_values, fresh):
        self.h5_file = h5_file  # We'll need this in transition_to_manual
        self.device_name = device_name
        with h5py.File(h5_file, 'r') as hdf5_file:
            print('\n' + h5_file)
            self.device_properties = labscript_utils.properties.get(
                hdf5_file, device_name, 'device_properties'
            )

        # pyvisa's timeout is in milliseconds, and the device's in seconds.
        self.scope.dev.timeout = 1000 * self.device_properties.get('timeout', 5)

        self.scope.unlock()
        # A channel asked for is switched on, as a hidden one returns no waveform.
        wanted = self.device_properties.get('channels')
        if wanted is not None:
            channels = self.scope.channels()
            unknown = set(wanted) - set(channels)
            if unknown:
                raise LabscriptError(
                    f"{self.device_name} has no channel {', '.join(sorted(unknown))}. "
                    f"Choose from {', '.join(channels)}."
                )
            for ch in wanted:
                self.scope.write(f'SELECT:{ch} ON')
        self.scope.set_acquire_state(True)
        # Shot files compiled before these were properties take the values then fixed.
        self.scope.write(
            f"ACQUIRE:MODE {self.device_properties.get('acquire_mode', 'SAMPLE')}"
        )
        self.scope.write(
            f"ACQUIRE:STOPAFTER {self.device_properties.get('stop_after', 'SEQUENCE')}"
        )
        self.scope.write('ACQUIRE:STATE RUN')
        return {}

    def transition_to_manual(self):
        channels = self.scope.channels()
        wanted = self.device_properties.get('channels')
        wfmp = {}
        vals = {}
        wtype = [('t', 'float')]
        print('Downloading...')
        for ch, enabled in channels.items():
            if enabled if wanted is None else ch in wanted:
                wfmp[ch], t, vals[ch] = self.scope.waveform(
                    ch,
                    int16=self.device_properties.get('int16', False),
                    preamble_string=self.preamble_string,
                )
                wtype.append((ch, 'float'))
                print(wfmp[ch]['WFID'])
        if not vals:
            raise LabscriptError(
                f"{self.device_name} has no channel displayed, so there is no trace to "
                "save. Display at least one channel on the scope."
            )

        # Collate all data in a structured array, on the time axis of the last
        # channel downloaded.
        data = np.empty(len(t), dtype=wtype)
        data['t'] = t
        for ch in vals:
            data[ch] = vals[ch]

        # Open the file after download so as not to hog the file lock
        with h5py.File(self.h5_file, 'r+') as hdf_file:
            grp = hdf_file.require_group('/data/traces')
            print('Saving traces...')
            dset = grp.create_dataset(self.device_name, data=data)
            # ch is the last channel, so only its preamble is saved.
            dset.attrs.update(wfmp[ch])

        print('Done!')
        return True

    def program_manual(self, front_panel_values):
        return front_panel_values

    def abort(self):
        print('aborting!')
        return True

    def abort_buffered(self):
        print('abort_buffered: ...')
        return self.abort()

    def abort_transition_to_buffered(self):
        print('abort_transition_to_buffered: ...')
        return self.abort()

    def shutdown(self):
        self.scope.close()
