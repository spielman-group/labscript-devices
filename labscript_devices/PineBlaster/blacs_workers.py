#####################################################################
#                                                                   #
# /labscript_devices/PineBlaster/blacs_workers.py                   #
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


class PineBlasterWorker(PseudoclockWorker):
    def init(self):
        global h5py; import labscript_utils.h5_lock, h5py
        global serial; import serial
        global time; import time
        self.smart_cache = []

        self.pineblaster = serial.Serial(self.com_port, 115200, timeout=1)
        # Device has a finite startup time.
        time.sleep(5)
        self.pineblaster.write(b'hello\r\n')
        response = self.pineblaster.readline().decode()

        if response == 'hello\r\n':
            return
        elif response:
            raise Exception(
                f"PineBlaster on {self.com_port} answered 'hello' with {response!r}. "
                "Check that com_port is the PineBlaster's."
            )
        else:
            raise Exception(
                f"PineBlaster on {self.com_port} did not answer 'hello'. "
                "Check its connection, or reboot it."
            )

    def shutdown(self):
        self.pineblaster.close()

    def program_manual(self, front_panel_values):
        # 'internal', the clock line's output, is the only front panel value.
        value = front_panel_values['internal']
        self.pineblaster.write(b'go high\r\n' if value else b'go low\r\n')
        response = self.pineblaster.readline().decode()
        assert response == 'ok\r\n', f"PineBlaster said {response!r}, expected 'ok'."
        return {}

    def transition_to_buffered(self, device_name, h5_file, front_panel_values, fresh):
        if fresh:
            self.smart_cache = []
        self.program_manual({'internal': 0})

        with h5py.File(h5_file, 'r') as hdf5_file:
            group = hdf5_file[f'devices/{device_name}']
            pulse_program = group['PULSE_PROGRAM'][:]
            device_properties = labscript_utils.properties.get(
                hdf5_file, device_name, 'device_properties'
            )
            self.is_master_pseudoclock = device_properties['is_master_pseudoclock']

        for i, instruction in enumerate(pulse_program):
            if i == len(self.smart_cache):
                # Pad the smart cache out to be as long as the program.
                self.smart_cache.append(None)

            # Only program instructions that differ from what's in the smart cache.
            if self.smart_cache[i] != instruction:
                self.pineblaster.write(
                    b'set %d %d %d\r\n' % (i, instruction['period'], instruction['reps'])
                )
                response = self.pineblaster.readline().decode()
                assert response == 'ok\r\n', f"PineBlaster said {response!r}, expected 'ok'."
                self.smart_cache[i] = instruction

        if not self.is_master_pseudoclock:
            # Get ready for a hardware trigger.
            self.pineblaster.write(b'hwstart\r\n')
            response = self.pineblaster.readline().decode()
            assert response == 'ok\r\n', f"PineBlaster said {response!r}, expected 'ok'."

        # Always finish on 0.
        return {'internal': 0}

    def start_run(self):
        # BLACS starts only the master pseudoclock, in software; a secondary starts on
        # its hardware trigger.
        self.pineblaster.write(b'start\r\n')
        response = self.pineblaster.readline().decode()
        assert response == 'ok\r\n', f"PineBlaster said {response!r}, expected 'ok'."

    def shot_finished(self):
        # Wait for the board's 'done', for up to the serial timeout, 1 s.
        response = self.pineblaster.readline().decode()
        if response:
            assert response == 'done\r\n', (
                f"PineBlaster said {response!r}, expected 'done'."
            )
            return True
        return False

    def transition_to_manual(self):
        # The master's 'done' was read already, by its tab's status monitor.
        if not self.is_master_pseudoclock:
            self.wait_for_end_of_shot()
        return True

    def abort_buffered(self):
        return self.abort()

    def abort_transition_to_buffered(self):
        return self.abort()

    def abort(self):
        self.pineblaster.write(b'restart\r\n')
        time.sleep(5)
        self.shutdown()
        self.init()
        return True
