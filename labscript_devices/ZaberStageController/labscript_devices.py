#####################################################################
#                                                                   #
# /labscript_devices/ZaberStageController/labscript_devices.py      #
#                                                                   #
# Copyright 2019, Monash University and contributors                #
#                                                                   #
# This file is part of labscript_devices, in the labscript suite    #
# (see http://labscriptsuite.org), and is licensed under the        #
# Simplified BSD License. See the license.txt file in the root of   #
# the project for the full license.                                 #
#                                                                   #
#####################################################################

from labscript import StaticAnalogQuantity, IntermediateDevice, set_passed_properties
import numpy as np

from .utils import get_device_number


class ZaberStage(StaticAnalogQuantity):
    """A static analog output that sets the position of a Zaber stage, in steps."""

    limits = (0, np.inf)
    description = "Zaber Stage"

    @set_passed_properties(
        property_names={"connection_table_properties": ["limits"]}
    )
    def __init__(self, *args, limits=None, **kwargs):
        """
        Parameters
        ----------
        *args
            The `name`, `parent_device` and `connection` of
            :class:`~labscript.StaticAnalogQuantity`. The parent is a
            `ZaberStageController`, and the connection is ``'device <n>'``, with n > 0
            the number of the Zaber device.
        limits : tuple, optional
            The minimum and maximum position, in steps, that the stage may be sent to
            from the experiment or the BLACS front panel. If `None`, the default, the
            class attribute `limits` is used: the maximal positions of the stage for
            the model-specific subclasses in this module, and ``(0, inf)`` otherwise.
            Give `limits` to restrict the range further.
        **kwargs
            Passed to :class:`~labscript.StaticAnalogQuantity`.
        """
        if limits is None:
            limits = self.limits
        StaticAnalogQuantity.__init__(self, *args, limits=limits, **kwargs)


# Child classes for specific models of stages, which have knowledge of their valid
# ranges:
class ZaberStageTLSR150D(ZaberStage):
    """A Zaber T-LSR150D stage, limited by default to its maximal positions."""

    limits = (0, 76346)
    description = 'Zaber Stage T-LSR150D'


class ZaberStageTLSR300D(ZaberStage):
    """A Zaber T-LSR300D stage, limited by default to its maximal positions."""

    limits = (0, 151937)
    description = 'Zaber Stage T-LSR300D'


class ZaberStageTLS28M(ZaberStage):
    """A Zaber T-LS28-M stage, limited by default to its maximal positions."""

    limits = (0, 282879)
    description = 'Zaber Stage T-LS28-M'


class ZaberStageTLSR300B(ZaberStage):
    """A Zaber T-LSR300B stage, limited by default to its maximal positions."""

    limits = (0, 607740)
    description = 'Zaber Stage T-LSR300B'


class ZaberStageController(IntermediateDevice):
    """Controls Zaber stages on one serial port, added as child `ZaberStage` devices."""

    allowed_children = [ZaberStage]

    @set_passed_properties(
        property_names={"connection_table_properties": ["com_port", "mock"]}
    )
    def __init__(self, name, com_port="COM1", mock=False, **kwargs):
        """
        Parameters
        ----------
        name : str
            Python variable name of the device.
        com_port : str, optional
            Serial port the stages are connected to: ``'COM1'`` etc. on Windows, or
            ``'/dev/USBtty0'`` or similar on unix. ``'COM1'`` by default.
        mock : bool, optional
            If `True`, BLACS simulates the stages instead of communicating with
            hardware, for testing; `False` by default.
        **kwargs
            Passed to :class:`~labscript.IntermediateDevice`.
        """
        IntermediateDevice.__init__(self, name, None, **kwargs)
        self.BLACS_connection = com_port

    def add_device(self, device):
        # Raises ValueError, before the device is added, if the connection is not
        # 'device <n>' with n > 0.
        _ = get_device_number(device.connection)
        IntermediateDevice.add_device(self, device)

    def generate_code(self, hdf5_file):
        IntermediateDevice.generate_code(self, hdf5_file)
        stages = {stage.connection: stage for stage in self.child_devices}
        connections = sorted(stages, key=get_device_number)
        # One field per stage, named by its connection, in device-number order; the
        # worker reads them by name.
        dtypes = [(connection, int) for connection in connections]
        static_value_table = np.empty(1, dtype=dtypes)
        for connection, stage in stages.items():
            static_value_table[connection][0] = stage.static_value
        grp = self.init_device_group(hdf5_file)
        grp.create_dataset('static_values', data=static_value_table)
