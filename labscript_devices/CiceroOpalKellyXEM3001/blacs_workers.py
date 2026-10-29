#####################################################################
#                                                                   #
# /labscript_devices/CiceroOpalKellyXEM3001/blacs_workers.py        #
#                                                                   #
# Copyright 2013, Monash University                                 #
#                                                                   #
# This file is part of the module labscript_devices, in the         #
# labscript suite (see http://labscriptsuite.org), and is           #
# licensed under the Simplified BSD License. See the license.txt    #
# file in the root of the project for the full license.             #
#                                                                   #
#####################################################################

from labscript_devices.pseudoclock import PseudoclockWorker

import labscript_utils.properties
from labscript_utils import ensure_str


def int_to_bytes(n, m):
    """Return the integer `n` as a list of `m` bytes, most significant first."""
    out = [(n >> (i*8)) & 0xFF for i in range(m-1, -1, -1)]
    return out


def bits_to_int(m, *args):
    """Join the integers `args`, each of `m` bits, into one; the first is least significant."""
    total = 0
    for i, byte in enumerate(args):
        total += byte << (m*i)
    return total


def add_instruction_to_bytearray(data, instruction, on, off, reps):
    """Pack instruction number `instruction` into its 16 bytes of `data`."""
    on_period = int_to_bytes(on, 6)
    off_period = int_to_bytes(off, 6)
    reps = int_to_bytes(reps, 4)

    offset = 16*instruction

    # Each 16-bit word is written low byte first, the most significant word first.
    # Bytes 0-5 are for on_period (in multiples of clock period)
    data[offset+0] = on_period[1]
    data[offset+1] = on_period[0]
    data[offset+2] = on_period[3]
    data[offset+3] = on_period[2]
    data[offset+4] = on_period[5]
    data[offset+5] = on_period[4]
    # Bytes 6-11 are for off_period (in multiples of clock period)
    data[offset+6] = off_period[1]
    data[offset+7] = off_period[0]
    data[offset+8] = off_period[3]
    data[offset+9] = off_period[2]
    data[offset+10] = off_period[5]
    data[offset+11] = off_period[4]
    # Bytes 12-15 are for the number of reps
    data[offset+12] = reps[1]
    data[offset+13] = reps[0]
    data[offset+14] = reps[3]
    data[offset+15] = reps[2]


class CiceroOpalKellyXEM3001Worker(PseudoclockWorker):
    def init(self):
        global h5py; import labscript_utils.h5_lock, h5py
        global time; import time
        global zprocess; import zprocess
        global ok; import ok

        # If the module has no okCFrontPanel, take it from the ok module inside it
        # (FrontPanel v4 and v5 apparently differ here).
        if not hasattr(ok, 'okCFrontPanel'):
            from ok import ok

        global numpy; import numpy

        # Posted as each wait completes, when all have, and when their durations are saved.
        self.all_waits_finished = zprocess.Event('all_waits_finished', role='post')
        self.wait_durations_analysed = zprocess.Event('wait_durations_analysed', role='post')
        self.wait_completed = zprocess.Event('wait_completed', role='post')
        self.current_wait = 0
        self.wait_table = None
        self.measured_waits = None
        self.h5_file = None

        self.dev = ok.okCFrontPanel()
        assert self.dev.OpenBySerial(self.serial_number) == self.dev.NoError

        try:
            assert self.dev.IsFrontPanelEnabled()
        except AssertionError:
            # FrontPanel is not enabled, so flash the FPGA bit file.
            self.flash_FPGA()

        # Ensure the FPGA's state machine is deactivated.
        assert self.dev.ActivateTriggerIn(0x40, 1) == self.dev.NoError

    def flash_FPGA(self):
        import os
        if self.reference_clock == 'internal':
            fpga_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.realpath(__file__))),
                'CiceroOpalKellyXEM3001_fpga_internal.bit',
            )
        elif self.reference_clock == 'external':
            fpga_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.realpath(__file__))),
                'CiceroOpalKellyXEM3001_fpga_external.bit',
            )
        else:
            raise RuntimeError(
                f"The reference_clock of {self.device_name} must be 'internal' or "
                f"'external', not {self.reference_clock!r}. Correct it in the connection "
                "table script."
            )

        # ConfigureFPGA apparently does not raise for a missing file, so check for it here.
        if not os.path.exists(fpga_path):
            raise RuntimeError(
                f"Cannot flash the FPGA of {self.device_name}: its {self.reference_clock} "
                f"reference clock needs the bit file {fpga_path}, which is missing. "
                "Put the file there."
            )

        self.logger.debug(f'Flashing FPGA bit file located at: {fpga_path}')
        self.dev.ConfigureFPGA(fpga_path)
        assert self.dev.IsFrontPanelEnabled(), (
            "Flashing the FPGA failed: the device is not configured correctly with "
            f"{fpga_path}."
        )

        return True

    def shutdown(self):
        # Signal the state machine to halt execution.
        self.dev.ActivateTriggerIn(0x40, 1)
        # Deleting the device closes the connection: Python has no close() function for it.
        del self.dev

    def program_manual(self, front_panel_values):
        # There is no manual mode for this device.
        return front_panel_values

    def transition_to_buffered(self, device_name, h5_file, front_panel_values, fresh):
        # The wait monitor posts events about this file and writes the measured waits to it.
        self.h5_file = h5_file
        self.current_wait = 0

        # Abort any previous run, which returns the output to 0 in preparation for the
        # clock to begin.
        self.abort()

        with h5py.File(h5_file, 'r') as hdf5_file:
            group = hdf5_file[f'devices/{device_name}']
            pulse_program = group['PULSE_PROGRAM'][:]
            device_properties = labscript_utils.properties.get(
                hdf5_file, device_name, 'device_properties'
            )
            self.connection_table_properties = labscript_utils.properties.get(
                hdf5_file, device_name, 'connection_table_properties'
            )
            self.is_master_pseudoclock = device_properties['is_master_pseudoclock']

            # This device measures the waits only if its own internal outputs are the wait
            # monitor's acquisition and timeout devices.
            dataset = hdf5_file['waits']
            acquisition_device = dataset.attrs['wait_monitor_acquisition_device']
            timeout_device = dataset.attrs['wait_monitor_timeout_device']
            if (
                len(dataset) > 0
                and acquisition_device == f'{device_name}_internal_wait_monitor_outputs'
                and timeout_device == f'{device_name}_internal_wait_monitor_outputs'
            ):
                self.wait_table = dataset[:]
                self.measured_waits = numpy.zeros(len(self.wait_table))
            else:
                self.wait_table = None
                self.measured_waits = None

        # Set the trigger debounce counter, in reference clock cycles.
        self.dev.SetWireInValue(
            0x01, self.connection_table_properties['trigger_debounce_clock_ticks']
        )
        self.dev.UpdateWireIns()

        if self.wait_table is not None and not self.is_master_pseudoclock:
            raise RuntimeError(
                f"{device_name} is a secondary pseudoclock, but the shot file makes it the "
                "wait monitor, which only a master can be. Recompile the shot; if this "
                "persists, report it to the labscript developers."
            )

        # Each instruction takes 16 bytes.
        data = bytearray(len(pulse_program)*16)
        for i, instruction in enumerate(pulse_program):
            add_instruction_to_bytearray(
                data, i, instruction['on_period'], instruction['off_period'], instruction['reps']
            )

        assert self.dev.WriteToPipeIn(0x80, data) == len(data)

        # A secondary starts now, so that its state machine reaches the first wait and is
        # ready to output on the first trigger.
        if not self.is_master_pseudoclock:
            self.start_run()

        # Always finish on 0.
        return {'Clock Out': 0}

    def start_run(self):
        # Start in software.
        assert self.dev.ActivateTriggerIn(0x40, 0) == self.dev.NoError

    def shot_finished(self):
        # Refresh the wire-out values read below.
        self.dev.UpdateWireOuts()

        if self.wait_table is not None and self.current_wait < len(self.wait_table):
            master_samples_generated = bits_to_int(
                16, self.dev.GetWireOutValue(0x22), self.dev.GetWireOutValue(0x23)
            )
            self.logger.debug(f'Master samples generated: {master_samples_generated}')

            clock_frequency = self.connection_table_properties['clock_frequency']

            wait_sample = int(self.wait_table[self.current_wait][1]*clock_frequency)
            self.logger.debug(f'Wait sample: {wait_sample}')
            if wait_sample < master_samples_generated:
                # A wait has happened. Make sure a second has not happened before this poll
                # noticed the first.
                if len(self.wait_table) > self.current_wait+1:
                    next_wait_sample = int(
                        self.wait_table[self.current_wait+1][1]*clock_frequency
                    )
                    assert next_wait_sample > master_samples_generated, (
                        'A wait came too soon after another: two passed between status '
                        'polls, so the length of each cannot be measured. Keep waits well '
                        'over 100 ms apart.'
                    )

                # The board's count appears to be the total of the wait samples so far, so the
                # last wait's length is that less the earlier waits', which measured_waits
                # keeps in clock samples for this.
                retrigger_wait_samples = bits_to_int(
                    16, self.dev.GetWireOutValue(0x26), self.dev.GetWireOutValue(0x27)
                )
                self.logger.debug(f'Retrigger wait samples: {retrigger_wait_samples}')
                self.measured_waits[self.current_wait] = (
                    retrigger_wait_samples-self.measured_waits.sum()
                )

                # Tell anything listening that a wait has completed.
                self.wait_completed.post(
                    self.h5_file,
                    data=ensure_str(self.wait_table[self.current_wait]['label']),
                )

                self.current_wait += 1

                if len(self.wait_table) == self.current_wait:
                    self.all_waits_finished.post(self.h5_file)

        # Status bit 0 means finished, and bit 1 aborted.
        status = self.dev.GetWireOutValue(0x25)
        assert not status & 2
        return status & 1

    def transition_to_manual(self):
        # The master's tab has seen it finish already.
        if not self.is_master_pseudoclock:
            self.wait_for_end_of_shot()
        clock_frequency = self.connection_table_properties['clock_frequency']

        if self.wait_table is not None:
            with h5py.File(self.h5_file, 'a') as hdf5_file:
                # Work out how long the waits were, save them, and post an event saying so.
                dtypes = [
                    ('label', 'S256'),
                    ('time', float),
                    ('timeout', float),
                    ('duration', float),
                    ('timed_out', bool),
                ]
                data = numpy.empty(len(self.wait_table), dtype=dtypes)
                data['label'] = self.wait_table['label']
                data['time'] = self.wait_table['time']
                data['timeout'] = self.wait_table['timeout']
                # Convert to seconds.
                data['duration'] = self.measured_waits/clock_frequency
                data['timed_out'] = data['duration'] >= data['timeout']

                hdf5_file.create_dataset('/data/waits', data=data)

            self.wait_durations_analysed.post(self.h5_file)

        return True

    def abort_buffered(self):
        return self.abort()

    def abort_transition_to_buffered(self):
        return self.abort()

    def abort(self):
        # Send the abort signal, soft_abort_trig_in. The state machine must notice first.
        assert self.dev.ActivateTriggerIn(0x40, 1) == self.dev.NoError

        # Return the aborted bit of the board's status.
        self.dev.UpdateWireOuts()
        return self.dev.GetWireOutValue(0x25) & 2
