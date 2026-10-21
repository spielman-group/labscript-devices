#####################################################################
#                                                                   #
# /labscript_devices/LightCrafterDMD/blacs_workers.py               #
#                                                                   #
# Copyright 2017, Monash University                                 #
#                                                                   #
# This file is part of labscript_devices, in the labscript suite    #
# (see http://labscriptsuite.org), and is licensed under the        #
# Simplified BSD License. See the license.txt file in the root of   #
# the project for the full license.                                 #
#                                                                   #
#####################################################################

import base64
import time

import labscript_utils.h5_lock, h5py
from blacs.tab_base_classes import Worker

from ..deadline import Deadline
from .labscript_devices import BLANK_BMP


class LightCrafterDMDWorker(Worker):
    command = {
        'version': b'\x01\x00',
        'display_mode': b'\x01\x01',
        'static_image': b'\x01\x05',
        'sequence_setting': b'\x04\x00',
        'pattern_definition': b'\x04\x01',
        'start_pattern_sequence': b'\x04\x02',
        'display_pattern': b'\x04\x05',
        'advance_pattern_sequence': b'\x04\x03',
    }
    send_packet_type = {
        'read': b'\x04',
        'write': b'\x02',
    }
    receive_packet_type = {
        b'\x00': 'System Busy',
        b'\x01': 'Error',
        b'\x03': 'Write response',
        b'\x05': 'Read response',
    }
    flag = {
        'complete': b'\x00',
        'beginning': b'\x01',
        'intermediate': b'\x02',
        'end': b'\x03',
    }
    error_messages = {
        b'\x01': "Command execution failed with unknown error",
        b'\x02': "Invalid command",
        b'\x03': "Invalid parameter",
        b'\x04': "Out of memory resource",
        b'\x05': "Hardware device failure",
        b'\x06': "Hardware busy",
        b'\x07': "Not Initialized (any of the preconditions for the command is not met)",
        b'\x08': (
            "Some object referred by the command is not found. "
            "For example, a solution name was not found"
        ),
        b'\x09': "Checksum error",
        b'\x0A': "Packet format error due to insufficient or larger than expected payload size",
        b'\x0B': "Command continuation error due to incorrect continuation flag",
    }
    display_mode = {
        'static': b'\x00',
        'pattern': b'\x04',
    }

    def init(self):
        global socket; import socket
        global struct; import struct
        self.host, self.port = self.server.split(':')
        self.port = int(self.port)
        self.smart_cache = {'IMAGE_TABLE': ''}
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((self.host, self.port))
        self.send(
            self.send_packet_type['write'],
            self.command['display_mode'],
            self.display_mode['static'],
        )

    # A packet is [packet type (1 byte), command (2), flags (1), payload length (2,
    # little-endian), data (N), checksum (1)]. The checksum is the sum of the other bytes
    # modulo 256.
    def send(self, type, command, data):
        packet = b''.join(
            [type, command, self.flag['complete'], struct.pack('<H', len(data)), data]
        )
        packet += struct.pack('<B', sum(bytearray(packet)) % 256)
        # A busy DMD answers with a System Busy packet and does not run the command
        # (TI's DLPU007, 2.1.1), so the command is sent again every 5 s
        deadline = Deadline(self.device_name, 'run a command', 30)
        while True:
            with deadline.timeout_for(socket.timeout):
                self.sock.settimeout(deadline.remaining())
                self.sock.send(packet)
                recv = self._receive(deadline)
            if recv['type'] != "System Busy":
                return self.receive(recv)
            time.sleep(min(5, deadline.remaining()))

    def _receive(self, deadline):
        # Assumes a fresh packet: nothing is waiting in the buffer. The 6-byte header
        # gives the payload length. Each read takes the time left, so the deadline bounds
        # the whole packet.
        self.sock.settimeout(deadline.remaining())
        header = self.sock.recv(6)
        pkt_type = self.receive_packet_type[header[0:1]]
        command = header[1:3]
        flag = header[3:4]
        length = struct.unpack('<H', header[4:6])[0]
        self.sock.settimeout(deadline.remaining())
        body = self.sock.recv(length + 1)
        checksum = body[-1:]
        body = body[:-1]
        return {
            'header': header,
            'type': pkt_type,
            'command': command,
            'flag': flag,
            'length': length,
            'body': body,
            'checksum': checksum,
        }

    def receive(self, recv):
        if recv['type'] == "Error":
            errors = ""
            for e in recv['body']:
                errors += self.error_messages[bytes([e])] + "\n"

            raise Exception(f"The LightCrafter {self.device_name} reported an error:\n{errors}")

        check = struct.pack('<B', sum(bytearray(recv['header'] + recv['body'])) % 256)

        if check != recv['checksum']:
            raise Exception(
                f"The LightCrafter {self.device_name} sent a packet whose checksum "
                "does not match its contents."
            )

        if recv['flag'] != self.flag['complete']:
            raise Exception(
                f"The LightCrafter {self.device_name} sent a multipart packet, "
                "which is not supported."
            )

        if recv['type'] == 'Write response':
            return True
        else:
            return recv['body']

    def program_manual(self, front_panel_values):
        # One ImageSet, so one region
        (value,) = front_panel_values.values()
        data = base64.b64decode(value)
        # The front panel value is empty until an image is selected; show the black
        # image then.
        if not data:
            data = BLANK_BMP

        if data[0:2] != b"BM":
            raise Exception(
                f"The front panel image is not a bmp: it starts with {data[0:2]!r}, "
                "not b'BM'. Select a 1-bit bmp image."
            )

        self.send(
            self.send_packet_type['write'],
            self.command['display_mode'],
            self.display_mode['static'],
        )
        self.send(self.send_packet_type['write'], self.command['static_image'], data)
        return {}

    def transition_to_buffered(self, device_name, h5_file, front_panel_values, fresh):
        # Every shot the device compiles has an IMAGE_TABLE: it has one ImageSet
        with h5py.File(h5_file, 'r') as hdf5_file:
            table_data = hdf5_file['/devices/' + device_name]['IMAGE_TABLE'][:]

        oldtable = self.smart_cache['IMAGE_TABLE']
        self.send(
            self.send_packet_type['write'],
            self.command['display_mode'],
            self.display_mode['pattern'],
        )
        num_of_patterns = len(table_data)
        # We will pad the images we send up to a multiple of four:
        padded_num_of_patterns = num_of_patterns + (-num_of_patterns % 4)

        # The sequence settings: bit depth, number of patterns, invert patterns?,
        # trigger type, trigger delay (4 bytes), trigger period (4 bytes),
        # exposure time (4 bytes), led select
        self.send(
            self.send_packet_type['write'],
            self.command['sequence_setting'],
            struct.pack('<BBBBiiiB', 1, padded_num_of_patterns, 0, 2, 0, 0, 0, 0),
        )
        # Smart programming: the images are sent only if they differ from those last
        # sent, unless `fresh`.
        if fresh or len(oldtable) != len(table_data) or (oldtable != table_data).any():
            for i in range(padded_num_of_patterns):
                if i < num_of_patterns:
                    im = table_data[i]
                else:
                    # Padding uses the final image:
                    im = table_data[-1]
                self.send(
                    self.send_packet_type['write'],
                    self.command['pattern_definition'],
                    struct.pack('<B', i) + im.tobytes(),
                )

        self.send(
            self.send_packet_type['write'], self.command['display_pattern'], struct.pack('<H', 0)
        )
        self.send(
            self.send_packet_type['write'],
            self.command['start_pattern_sequence'],
            struct.pack('<B', 1),
        )
        self.smart_cache['IMAGE_TABLE'] = table_data

        self.final_value = {"None": base64.b64encode(table_data[-1].tobytes())}

        return self.final_value

    def transition_to_manual(self):
        # Turn off sequence
        self.send(
            self.send_packet_type['write'],
            self.command['start_pattern_sequence'],
            struct.pack('<B', 0),
        )
        # Show the shot's last image as a static image.
        self.program_manual(self.final_value)
        return True

    def abort(self):
        self.send(
            self.send_packet_type['write'],
            self.command['start_pattern_sequence'],
            struct.pack('<B', 0),
        )

        return True

    def abort_buffered(self):
        return self.abort()

    def abort_transition_to_buffered(self):
        return self.abort()

    def shutdown(self):
        self.sock.close()
