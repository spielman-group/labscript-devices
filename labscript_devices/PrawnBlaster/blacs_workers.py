#####################################################################
#                                                                   #
# /labscript_devices/PrawnBlaster/blacs_workers.py                  #
#                                                                   #
# Copyright 2021, Philip Starkey                                    #
#                                                                   #
# This file is part of labscript_devices, in the labscript suite    #
# (see http://labscriptsuite.org), and is licensed under the        #
# Simplified BSD License. See the license.txt file in the root of   #
# the project for the full license.                                 #
#                                                                   #
#####################################################################
import labscript_utils.h5_lock
import h5py
import numpy as np
from labscript_devices.common.deadline import Deadline
from labscript_devices.common.pseudoclock import PseudoclockWorker
from labscript import LabscriptError
from labscript_utils import ensure_str
import labscript_utils.properties as properties


class PrawnBlasterWorker(PseudoclockWorker):
    """The primary worker for the PrawnBlaster."""

    def init(self):
        # fmt: off
        global h5py; import labscript_utils.h5_lock, h5py
        global serial; import serial
        global time; import time
        global re; import re
        global numpy; import numpy
        global struct; import struct
        global zprocess; import zprocess
        self.smart_cache = {}
        self.cached_pll_params = {}
        # fmt: on

        self.all_waits_finished = zprocess.Event("all_waits_finished", role="post")
        self.wait_durations_analysed = zprocess.Event(
            "wait_durations_analysed", role="post"
        )
        self.wait_completed = zprocess.Event("wait_completed", role="post")
        self.current_wait = 0
        self.wait_table = None
        self.measured_waits = None
        self.wait_timeout = None
        self.h5_file = None
        self.started = False
        self.min_version = (1, 1, 0)
        
        self.conn = serial.Serial(self.com_port, 115200, timeout=1)
        self.check_status()

        self.send_command_ok(f"setnumpseudoclocks {self.num_pseudoclocks}")

        for i, (out_pin, in_pin) in enumerate(zip(self.out_pins, self.in_pins)):
            self.send_command_ok(f"setoutpin {i} {out_pin}")
            self.send_command_ok(f"setinpin {i} {in_pin}")

        version, _ = self.get_version()
        print(f'Connected to version: {version}')
        assert version >= self.min_version, f'Incompatible firmware {version}, must be >= {self.min_version}. Update the PrawnBlaster firmware.'
        
        if version >= (1, 2, 0):
            board = self.get_board()
        else:
            board = 'pico1'
            print(f'Version {version} too low to use pico2 firmware, consider upgrading firmware')
        
        print(f'Connected to board: {board}')
        if board.strip() != self.pico_board.strip():
            raise LabscriptError(f'Firmware reports {board} attached, but labscript expects {self.pico_board}. Set pico_board to match the attached board.')

        current_status = self.read_status()
        print(f'Current status is {current_status}')

    def _read_full_buffer(self):
        """Read every line the device sends, after a failed command or for a multi-line reply."""

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
    
    def get_version(self):
        version_str = self.send_command('version', readlines=True)
        assert version_str.startswith("version: "), f"Version command failed, got: {version_str}"
        version = version_str[9:].strip()

        version_overclock_list = version.split('-')
        overclock = False
        if len(version_overclock_list) == 2:
            if version_overclock_list[1] == 'overclock':
                overclock = True

        version = tuple(int(v) for v in version_overclock_list[0].split('.'))
        assert len(version) == 3, f"Firmware version {version_overclock_list[0]} does not have three numbers."

        return version, overclock

    def get_board(self):
        """Return "pico1" or "pico2", the board the firmware reports."""
        resp = self.send_command('board')
        assert resp.startswith('board:'), f'Board command failed, got: {resp}'
        pico_str = resp.split(':')[-1].strip()

        return pico_str

    def check_status(self):
        """Read out the next wait if it has ended; return (run_status, clock_status, waits_pending)."""

        if (
            self.started
            and self.wait_table is not None
            and self.current_wait < len(self.wait_table)
        ):
            # Try to read out wait. For now, we're only reading out waits from
            # pseudoclock 0 since they should all be the same (requirement imposed by labscript)
            response = self.send_command(f'getwait {0} {self.current_wait}')
            if response != "wait not yet available\r\n":
                # Parse the response from the PrawnBlaster
                wait_remaining = int(response)
                # clock_resolution is a whole clock pulse, two system ticks; the firmware
                # counts wait timeouts in single ticks, so they convert to seconds via
                # the clock frequency.
                clock_resolution = self.device_properties["clock_resolution"] / 2
                input_response_time = self.device_properties["input_response_time"]
                timeout_length = round(
                    self.wait_table[self.current_wait]["timeout"] / clock_resolution
                )

                if wait_remaining == (2 ** 32 - 1):
                    # The wait hit the timeout - save the timeout duration as wait length
                    # and flag that this wait timedout
                    self.measured_waits[self.current_wait] = (
                        timeout_length * clock_resolution
                    )
                    self.wait_timeout[self.current_wait] = True
                else:
                    # The count runs from the end of the last pulse to the retrigger's
                    # detection; less input_response_time, the time the ASM code takes to
                    # detect it, it is the time to the retrigger itself.
                    self.measured_waits[self.current_wait] = (
                        (timeout_length - wait_remaining) * clock_resolution
                    ) - input_response_time
                    self.wait_timeout[self.current_wait] = False

                self.logger.info(
                    "Wait %s finished. Length=%.9fs. Timed-out=%s",
                    self.current_wait,
                    self.measured_waits[self.current_wait],
                    self.wait_timeout[self.current_wait],
                )

                # Inform any interested parties that a wait has completed:
                self.wait_completed.post(
                    self.h5_file,
                    data=ensure_str(self.wait_table[self.current_wait]["label"]),
                )

                self.current_wait += 1

                if len(self.wait_table) == self.current_wait:
                    self.logger.info("All waits finished")
                    self.all_waits_finished.post(self.h5_file)

        waits_pending = False
        if self.wait_table is not None:
            if self.current_wait == len(self.wait_table):
                waits_pending = False
            else:
                waits_pending = True

        run_status, clock_status = self.read_status()
        return run_status, clock_status, waits_pending

    # Run status: 0 manual, 1 transitioning to buffered, 2 buffered, 3 abort requested,
    # 4 aborting, 5 last buffered run aborted, 6 transitioning to manual.
    # Clock status: 0 internal clock, 1 external clock.
    def read_status(self):
        """Return the firmware's (run_status, clock_status) codes."""

        response = self.send_command("status", readlines=False)
        match = re.match(r"run-status:(\d) clock-status:(\d)(\r\n)?", response)
        if match:
            return int(match.group(1)), int(match.group(2))
        else:
            response += self._read_full_buffer()
            raise Exception(
                f"PrawnBlaster returned '{response}' instead of 'run-status:<int> clock-status:<int>'. Check the serial connection and that the board runs PrawnBlaster firmware."
            )

    def program_manual(self, front_panel_values):
        for channel, value in front_panel_values.items():
            pin = int(channel.split()[1])
            pseudoclock = self.out_pins.index(pin)
            if value:
                self.send_command_ok(f"go high {pseudoclock}")
            else:
                self.send_command_ok(f"go low {pseudoclock}")

        return front_panel_values

    def transition_to_buffered(self, device_name, h5_file, front_panel_values, fresh):
        if fresh:
            self.smart_cache = {}

        # fmt: off
        self.h5_file = h5_file  # store reference to h5 file for wait monitor
        self.current_wait = 0  # reset wait analysis
        self.started = False   # Prevent status check from detecting previous wait values
        #                        between now and when we actually send the start signal
        # fmt: on

        pulse_programs = []
        with h5py.File(h5_file, "r") as hdf5_file:
            group = hdf5_file[f"devices/{device_name}"]
            for i in range(self.num_pseudoclocks):
                pulse_programs.append(group[f"PULSE_PROGRAM_{i}"][:])
                self.smart_cache.setdefault(i, [])
            self.device_properties = labscript_utils.properties.get(
                hdf5_file, device_name, "device_properties"
            )
            self.is_master_pseudoclock = self.device_properties["is_master_pseudoclock"]

            dataset = hdf5_file["waits"]
            acquisition_device = dataset.attrs["wait_monitor_acquisition_device"]
            timeout_device = dataset.attrs["wait_monitor_timeout_device"]
            if (
                len(dataset) > 0
                and acquisition_device == f"{device_name}_internal_wait_monitor_outputs"
                and timeout_device == f"{device_name}_internal_wait_monitor_outputs"
            ):
                self.wait_table = dataset[:]
                self.measured_waits = numpy.zeros(len(self.wait_table))
                self.wait_timeout = numpy.zeros(len(self.wait_table), dtype=bool)
            else:
                self.wait_table = (
                    None  # This device doesn't need to worry about looking at waits
                )
                self.measured_waits = None
                self.wait_timeout = None

        # Configure clock from device properties
        clock_mode = 0
        if self.device_properties["external_clock_pin"] is not None:
            if self.device_properties["external_clock_pin"] == 20:
                clock_mode = 1
            elif self.device_properties["external_clock_pin"] == 22:
                clock_mode = 2
            else:
                raise RuntimeError(
                    f"Invalid external clock pin {self.device_properties['external_clock_pin']}. Pin must be 20, 22 or None."
                )
        clock_frequency = self.device_properties["clock_frequency"]

        response = self.send_command_ok(f"setclock {clock_mode} {clock_frequency}")

        for pseudoclock, pulse_program in enumerate(pulse_programs):
            total_inst = len(pulse_program)
            # check if it is more efficient to fully refresh
            if not fresh and self.smart_cache[pseudoclock] is not None:
                curr_inst = self.smart_cache[pseudoclock]

                # if arrays aren't of same shape, only compare up to smaller array size
                n_curr = len(curr_inst)
                n_new = len(pulse_program)
                if n_curr > n_new:
                    # technically don't need to reprogram current elements beyond end of new elements
                    new_inst = np.sum(curr_inst[:n_new] != pulse_program)
                elif n_curr < n_new:
                    n_diff = n_new - n_curr
                    val_diffs = np.sum(curr_inst != pulse_program[:n_curr])
                    new_inst = val_diffs + n_diff
                else:
                    new_inst = np.sum(curr_inst != pulse_program)

                if new_inst / total_inst > 0.1:
                    fresh = True

            if (fresh or self.smart_cache[pseudoclock] is None):
                print('binary programming')
                # setb refuses a block that reaches the end of the firmware's table,
                # which a one-pseudoclock program can fill, so its last row goes by set
                table = self.device_properties["max_instructions"] * self.num_pseudoclocks
                binary = pulse_program[: table - 1]
                self.conn.write(b"setb %d %d %d\r\n" % (pseudoclock, 0, len(binary)))
                response = self.conn.readline().decode()
                assert (
                    response == "ready\r\n"
                ), f"PrawnBlaster said '{response}', expected 'ready'"
                program_array = np.array([binary['half_period'],
                                          binary['reps']], dtype='<u4').T
                self.conn.write(program_array.tobytes())
                response = self.conn.readline().decode()
                assert (
                    response == "ok\r\n"
                ), f"PrawnBlaster said '{response}', expected 'ok'"
                for i in range(len(binary), len(pulse_program)):
                    row = pulse_program[i]
                    self.send_command_ok(f"set {pseudoclock} {i} {row['half_period']} {row['reps']}")
                self.smart_cache[pseudoclock] = pulse_program
            else:
                print('incremental programming')
                for i, instruction in enumerate(pulse_program):
                    if i == len(self.smart_cache[pseudoclock]):
                        # Pad the smart cache out to be as long as the program:
                        self.smart_cache[pseudoclock].append(None)

                    # Only program instructions that differ from what's in the smart cache:
                    if self.smart_cache[pseudoclock][i] != instruction:
                        self.conn.write(
                            b"set %d %d %d %d\r\n"
                            % (
                                pseudoclock,
                                i,
                                instruction["half_period"],
                                instruction["reps"],
                            )
                        )
                        response = self.conn.readline().decode()
                        assert (
                            response == "ok\r\n"
                        ), f"PrawnBlaster said '{response}', expected 'ok'"
                        self.smart_cache[pseudoclock][i] = instruction

        if not self.is_master_pseudoclock:
            # Start the Prawnblaster and have it wait for a hardware trigger
            self.wait_for_trigger()

        # All outputs end on 0
        final = {}
        for pin in self.out_pins:
            final[f"GPIO {pin:02d}"] = 0
        return final

    def start_run(self):
        """Start execution in software, for the primary pseudoclock."""

        self.logger.info("sending start")
        self.send_command_ok("start")

        self.started = True

    def wait_for_trigger(self):
        """Arm a secondary pseudoclock to start on its hardware trigger, returning once it waits for it."""

        self.logger.info("sending hwstart")
        self.send_command_ok("hwstart")

        def armed():
            run_status, clock_status = self.read_status()
            # if we are not in TRANSITION_TO_RUNNING, then something has gone wrong
            # and we should raise an exception
            if run_status not in (1, 2):
                raise RuntimeError(
                    f"PrawnBlaster returned run-status {run_status} while arming for its trigger, expected 1 or 2."
                )
            # If we are running, great, the PrawnBlaster is waiting for a trigger
            return run_status == 2

        # The firmware arms in well under a second, so a board still arming after
        # 5 s is stuck
        Deadline(self.device_name, 'arm to wait for its trigger', 5).wait(armed)

        self.started = True

    def shot_finished(self):
        # check_status also reads out each wait as it ends, so the shot is over
        # only once every wait has been read.
        run_status, clock_status, waits_pending = self.check_status()
        if run_status in [3, 4, 5]:
            raise RuntimeError(
                f"PrawnBlaster reported run-status={run_status} during the shot, so the run was aborted."
            )
        return run_status == 0 and not waits_pending

    def transition_to_manual(self):
        # The master's tab has seen it finish already:
        if not self.is_master_pseudoclock:
            self.wait_for_end_of_shot()
        if self.wait_table is not None:
            with h5py.File(self.h5_file, "a") as hdf5_file:
                # Work out how long the waits were, save them, post an event saying so
                dtypes = [
                    ("label", "S256"),
                    ("time", float),
                    ("timeout", float),
                    ("duration", float),
                    ("timed_out", bool),
                ]
                data = numpy.empty(len(self.wait_table), dtype=dtypes)
                data["label"] = self.wait_table["label"]
                data["time"] = self.wait_table["time"]
                data["timeout"] = self.wait_table["timeout"]
                data["duration"] = self.measured_waits
                data["timed_out"] = self.wait_timeout

                self.logger.info('%s', data)

                hdf5_file.create_dataset("/data/waits", data=data)

            self.wait_durations_analysed.post(self.h5_file)

        return True

    def shutdown(self):
        self.conn.close()

    def abort(self):
        """Abort a running buffered execution, or the transition to it."""
        # Only a secondary told to wait for its trigger needs an abort, and the
        # firmware aborts only a board at run status 1 or 2
        if not self.is_master_pseudoclock and self.read_status()[0] in (1, 2):
            self.conn.write(b"abort\r\n")
            assert self.conn.readline().decode() == "ok\r\n"
            self.wait_for_end_of_shot(lambda: self.read_status()[0] == 5)
        return True

    def abort_transition_to_buffered(self):
        return self.abort()

    def abort_buffered(self):
        return self.abort()
