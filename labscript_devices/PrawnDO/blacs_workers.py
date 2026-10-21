#####################################################################
#                                                                   #
# /labscript_devices/PrawnDO/blacs_workers.py                       #
#                                                                   #
# Copyright 2023, Philip Starkey, Carter Turnbaugh, Patrick Miller  #
#                                                                   #
# This file is part of labscript_devices, in the labscript suite    #
# (see http://labscriptsuite.org), and is licensed under the        #
# Simplified BSD License. See the license.txt file in the root of   #
# the project for the full license.                                 #
#                                                                   #
#####################################################################
from labscript_utils.file_utils import warn_legacy_file
from labscript_devices.pseudoclock import PseudoclockWorker
import labscript_utils.h5_lock, h5py
import labscript_utils
from labscript import LabscriptError
import numpy as np
import re


class PrawnDOInterface:
    min_version = (1, 2, 0)
    """Minimum compatible firmware version tuple"""

    def __init__(self, com_port, pico_board):
        global serial; import serial
        global struct; import struct

        self.timeout = 0.2
        self.conn = serial.Serial(com_port, 1000000, timeout=self.timeout)
        self.pico_board = pico_board

        version = self.get_version()
        print(f'Connected to version: {version}')

        assert version >= self.min_version, f'Incompatible firmware {version}, must be >= {self.min_version}. Update the PrawnDO firmware.'

        if version >= (1, 3, 0):
            board = self.get_board()
        else:
            board = 'pico1'
            print(f'Version {version} too low to use pico2 firmware, consider upgrading firmware')

        print(f'Connected to board: {board}')
        if board.strip() != self.pico_board.strip():
            raise LabscriptError(f'Firmware reports {board} attached, but labscript expects {self.pico_board}. Set pico_board to match the attached board.')

        current_status = self.status()
        print(f'Current status is {current_status}')

    def get_version(self):
        """Return the firmware version as a (major, minor, patch) tuple."""
        version_str = self.send_command('ver')
        assert version_str.startswith("Version: "), f"Version command failed, got: {version_str!r}"
        version = tuple(int(i) for i in version_str[9:].split('.'))
        assert len(version) == 3, f"Firmware version {version} does not have three numbers."

        return version

    def get_board(self):
        """Return "pico1" or "pico2", the board the firmware reports."""
        resp = self.send_command('brd')
        assert resp.startswith('board:'), f'Board command failed, got: {resp}'
        pico_str = resp.split(':')[-1].strip()

        return pico_str

    def _read_full_buffer(self):
        """Read every line the device sends before the serial timeout."""
        resp = self.conn.readlines()
        str_resp = ''.join([st.decode() for st in resp])

        return str_resp

    def send_command(self, command, readlines=False):
        """Send command and return the response; readlines reads several lines, waiting for the timeout."""
        command += '\r\n'
        self.conn.write(command.encode())

        if readlines:
            str_resp = self._read_full_buffer()
        else:
            str_resp = self.conn.readline().decode()

        return str_resp

    def send_command_ok(self, command):
        """Send command and raise LabscriptError unless the response is 'ok'."""
        resp = self.send_command(command)
        if resp != 'ok\r\n':
            # get complete error message
            resp += self._read_full_buffer()
            raise LabscriptError(f"Command '{command}' failed. Got response {resp!r}.")

    # Run status: 0 manual, 1 transitioning to buffered, 2 buffered, 3 abort requested,
    # 4 aborting, 5 last buffered run aborted, 6 transitioning to manual.
    # Clock status: 0 internal clock, 1 external clock.
    def status(self):
        """Return the firmware's (run_status, clock_status) codes."""
        resp = self.send_command('sts')
        match = re.match(r"run-status:(\d) clock-status:(\d)(\r\n)?", resp)
        if match:
            return int(match.group(1)), int(match.group(2))
        else:
            resp += self._read_full_buffer()
            raise LabscriptError(
                f"PrawnDO returned {resp!r} instead of 'run-status:<int> clock-status:<int>'. "
                "Check the serial connection and that the board runs PrawnDO firmware."
            )

    def output_state(self):
        """Return the state of the 16 outputs as an integer, bit n being do<n>."""
        resp = self.send_command('gto')

        try:
            resp_i = int(resp, 16)
        except Exception as e:
            resp += self._read_full_buffer()
            raise LabscriptError(f"PrawnDO returned {resp!r} for its output state, not a hexadecimal number.") from e

        return resp_i

    def adm_batch(self, pulse_program):
        """Send the pulse program as one binary block with the adm command."""
        self.conn.write(f'adm 0 {len(pulse_program):x}\n'.encode())
        resp = self.conn.readline().decode()
        if resp != 'ready\r\n':
            resp += self._read_full_buffer()
            raise LabscriptError(f"The adm command failed: got {resp!r} instead of 'ready'.")
        self.conn.write(pulse_program.tobytes())
        resp = self.conn.readline().decode()
        if resp != 'ok\r\n':
            resp += self._read_full_buffer()
            raise LabscriptError(f"The board did not accept the pulse program: got {resp!r} instead of 'ok'.")

    def close(self):
        self.conn.close()


class PrawnDOWorker(PseudoclockWorker):
    def init(self):
        self.intf = PrawnDOInterface(self.com_port, self.pico_board)

        self.smart_cache = {'pulse_program':None}

    def _dict_to_int(self, d):
        """Return the integer mask of `d`, a dict of 'do<n>' states, with bit n for do<n>."""
        val = 0
        for conn, value in d.items():
            val |= value << int(conn.split('do')[-1])

        return val

    def _int_to_dict(self, val):
        """Return the dict of 'do<n>' states, 0 or 1, for the integer mask `val`."""
        return {f'do{i:d}':((val >> i) & 1) for i in range(16)}

    def check_status(self):
        """Return the firmware's (run_status, clock_status); see PrawnDOInterface.status."""
        return self.intf.status()

    def program_manual(self, front_panel_values):
        value = self._dict_to_int(front_panel_values)
        self.intf.send_command_ok(f'man {value:04x}')
        # Return the state read back from the board; BLACS sets the front panel to it.
        resp_i = self.intf.output_state()

        return self._int_to_dict(resp_i)

    def check_remote_values(self):
        resp_i = self.intf.output_state()

        return self._int_to_dict(resp_i)

    def transition_to_buffered(self, device_name, h5_file, front_panel_values, fresh):
        if fresh:
            self.smart_cache = {'pulse_program':None}

        with h5py.File(h5_file, 'r') as hdf5_file:
            group = hdf5_file['devices'][device_name]
            # LEGACY PULSE_PROGRAM NAME COMPATIBILITY. DEPRECATED CODE, WILL BE REMOVED.
            # Shot files compiled before the dataset's name was upper case.
            dataset = 'PULSE_PROGRAM' if 'PULSE_PROGRAM' in group else 'pulse_program'
            if 'pulse_program' in group:
                warn_legacy_file(
                    h5_file, "names the PrawnDO's pulse program pulse_program, not PULSE_PROGRAM"
                )
            if dataset not in group:
                # if no output commanded, return
                return {}
            self.device_properties = labscript_utils.properties.get(
                hdf5_file, device_name, "device_properties")
            pulse_program = group[dataset][()]

        # The firmware's clk takes 0 for the internal clock or 1 for the external one, on
        # pin 20, then the clock frequency in Hz.
        ext = self.device_properties['external_clock']
        freq = self.device_properties['clock_frequency']
        self.intf.send_command_ok(f"clk {ext:d} {freq:.0f}")

        # check if it is more efficient to fully refresh
        if not fresh and self.smart_cache['pulse_program'] is not None:
            curr_program = self.smart_cache['pulse_program']

            # if arrays aren't of same shape, only compare up to smaller array size
            n_curr = len(curr_program)
            n_new = len(pulse_program)
            if n_curr > n_new:
                # technically don't need to reprogram current elements beyond end of new elements
                new_inst = np.sum(curr_program[:n_new] != pulse_program)
            elif n_curr < n_new:
                n_diff = n_new - n_curr
                val_diffs = np.sum(curr_program != pulse_program[:n_curr])
                new_inst = val_diffs + n_diff
            else:
                new_inst = np.sum(curr_program != pulse_program)

            if new_inst / n_new > 0.1:
                fresh = True

        # if fresh or not smart cache, program full table as a batch
        # this is faster than going line by line
        if fresh or self.smart_cache['pulse_program'] is None:
            # clear the old program
            self.intf.send_command_ok('cls')
            self.intf.adm_batch(pulse_program)
        else:
            # only program table lines that have changed
            n_cache = len(self.smart_cache['pulse_program'])
            for i, instr in enumerate(pulse_program):
                if i >= n_cache:
                    print(f'programming step {i}')
                    self.intf.send_command_ok(f'set {i:x} {instr[0]:x} {instr[1]:x}')

                elif (self.smart_cache['pulse_program'][i] != instr):
                    print(f'programming step {i}')
                    self.intf.send_command_ok(f'set {i:x} {instr[0]:x} {instr[1]:x}')
        self.smart_cache['pulse_program'] = pulse_program

        # The last row's bit set is ignored; the row before it holds the final output.
        final_values = self._int_to_dict(pulse_program[-2][0])

        # start program, waiting for beginning trigger from parent
        self.intf.send_command_ok('run')

        return final_values

    def shot_finished(self):
        run_status, _ = self.intf.status()
        if run_status in [3,4,5]:
            raise LabscriptError(f'PrawnDO reported run-status {run_status} during the shot, so the run was aborted.')
        return run_status == 0

    def transition_to_manual(self):
        try:
            self.wait_for_end_of_shot()
        except TimeoutError:
            # Stop the program, probably badly triggered, without waiting to see
            # it stop as abort_buffered does: a stuck board might never report it.
            try:
                self.intf.send_command_ok('abt')
            except Exception:
                self.logger.exception('Could not abort the PrawnDO.')
            raise
        return True

    def abort(self):
        """Abort a running buffered execution, or the transition to it."""
        # The firmware refuses to abort a board that is not at run status 1 or 2,
        # and such a board has nothing to abort.
        if self.intf.status()[0] not in (1, 2):
            return True
        self.intf.send_command_ok('abt')
        self.wait_for_end_of_shot(lambda: self.intf.status()[0] == 5)
        return True

    def abort_transition_to_buffered(self):
        return self.abort()

    def abort_buffered(self):
        return self.abort()

    def shutdown(self):
        self.intf.close()
