#####################################################################
#                                                                   #
# /labscript_devices/ZaberStageController/blacs_workers.py          #
#                                                                   #
# Copyright 2019, Monash University and contributors                #
#                                                                   #
# This file is part of labscript_devices, in the labscript suite    #
# (see http://labscriptsuite.org), and is licensed under the        #
# Simplified BSD License. See the license.txt file in the root of   #
# the project for the full license.                                 #
#                                                                   #
#####################################################################

from blacs.tab_base_classes import Worker
from time import monotonic
from labscript_utils import dedent
import labscript_utils.h5_lock, h5py

from .utils import get_device_number


# ZaberInterface sets this to the zaber.serial module, so that the mock needs no
# Zaber library.
zaber = None

# Seconds a stage has to reach the position it was sent to.
TIMEOUT = 60


class MockZaberInterface:
    """Stands in for the stages, keeping the positions it is sent in memory."""

    def __init__(self, com_port):
        from collections import defaultdict
        self.positions = defaultdict(int)

    def move(self, device_number, position):
        print(f"Mock move device {device_number} to position {position}")
        self.positions[device_number] = position

    def get_position(self, device_number):
        return self.positions[device_number]

    def close(self):
        print(f"mock close")


class ZaberInterface:
    """The stages on one serial port, through the zaber.serial library."""

    def __init__(self, com_port):
        global zaber
        try:
            import zaber.serial as zaber
        except ImportError:
            msg = """Could not import zaber.serial. Install it with
                'pip install zaber.serial'."""
            raise ImportError(dedent(msg))

        self.port = zaber.BinarySerial(com_port)

    def move(self, device_number, position):
        device = zaber.BinaryDevice(self.port, device_number)
        device.move_abs(position)
        deadline = monotonic() + TIMEOUT
        while device.get_position() != position:
            if monotonic() > deadline:
                msg = (
                    f"Zaber device {device_number} did not reach position {position} "
                    f"within {TIMEOUT} s. Check that nothing blocks the stage."
                )
                raise TimeoutError(msg)

    def get_position(self, device_number):
        device = zaber.BinaryDevice(self.port, device_number)
        return device.get_position()

    def close(self):
        self.port.close()


class ZaberStageControllerWorker(Worker):
    def init(self):
        if self.mock:
            self.controller = MockZaberInterface(self.com_port)
        else:
            self.controller = ZaberInterface(self.com_port)

    def check_remote_values(self):
        remote_values = {}
        for connection in self.child_connections:
            device_number = get_device_number(connection)
            remote_values[connection] = self.controller.get_position(device_number)
        return remote_values

    def program_manual(self, front_panel_values):
        for connection, value in front_panel_values.items():
            device_number = get_device_number(connection)
            self.controller.move(device_number, int(round(value)))
        return self.check_remote_values()

    def transition_to_buffered(self, device_name, h5_file, front_panel_values, fresh):
        with h5py.File(h5_file, 'r') as hdf5_file:
            group = hdf5_file['/devices/' + device_name]
            # ZaberStageController.generate_code writes static_values.
            if 'static_values' in group:
                data = group['static_values']
                values = {name: data[0][name] for name in data.dtype.names}
            else:
                values = {}
        return self.program_manual(values)

    def transition_to_manual(self):
        return True

    def abort(self):
        return True

    def abort_buffered(self):
        return self.abort()

    def abort_transition_to_buffered(self):
        return self.abort()

    def shutdown(self):
        self.controller.close()
