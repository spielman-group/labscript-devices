#####################################################################
#                                                                   #
# /labscript_devices/common/triggerable_camera/labscript_devices.py #
#                                                                   #
# Copyright 2019, Monash University and contributors                #
#                                                                   #
# This file is part of labscript_devices, in the labscript suite    #
# (see http://labscriptsuite.org), and is licensed under the        #
# Simplified BSD License. See the license.txt file in the root of   #
# the project for the full license.                                 #
#                                                                   #
#####################################################################
import sys
import warnings
from labscript_utils import dedent
from labscript import LabscriptError, TriggerableDevice, set_passed_properties
import numpy as np
import labscript_utils.h5_lock
import h5py


class TriggerableCamera(TriggerableDevice):
    """A camera exposed by a digital trigger pulse, independent of any camera API."""

    description = 'Triggerable Camera'
    # Whether this class's serial numbers were hex by convention, so an unprefixed
    # string, now read as decimal, may once have been meant as hex.
    hex_serial_numbers = False

    @set_passed_properties(
        property_names={
            "connection_table_properties": [
                "serial_number",
                "orientation",
                "pixel_size",
                "magnification",
                "manual_mode_camera_attributes",
            ],
            "device_properties": [
                "camera_attributes",
                "stop_acquisition_timeout",
                "exception_on_failed_shot",
                "saved_attribute_visibility_level"
            ],
        }
    )
    def __init__(
        self,
        name,
        parent_device,
        connection,
        serial_number,
        orientation=None,
        pixel_size=[1.0, 1.0],
        magnification=1.0,
        trigger_edge_type='rising',
        trigger_duration=None,
        minimum_recovery_time=0.0,
        camera_attributes=None,
        manual_mode_camera_attributes=None,
        stop_acquisition_timeout=5.0,
        exception_on_failed_shot=True,
        saved_attribute_visibility_level='intermediate',
        **kwargs
    ):
        """
        Parameters
        ----------
        name : str
            Python variable name of the device.
        parent_device : IntermediateDevice or Trigger
            The device whose digital output triggers the camera.
        connection : str
            Name of the digital output port on the parent device; ``'trigger'`` if the
            parent is a `Trigger`.
        serial_number : str or int
            The camera's serial number, which identifies it: an int, which may be a
            hex literal such as ``0x1F``, or a string, read as hexadecimal if it
            starts with ``'0x'`` and as decimal otherwise.
        orientation : str, optional
            The camera's location or orientation. The images are saved under
            ``images/<orientation>`` in the shot file, or under ``images/<name>`` if
            `None`, the default.
        pixel_size : list of float, optional
            The x and y size of the pixels in micrometers; ``[1.0, 1.0]`` by default.
            Saved in the shot file with the device's connection table properties.
        magnification : float, optional
            Magnification of the imaging system; 1.0 by default. Saved like
            `pixel_size`.
        trigger_edge_type : str, optional
            ``'rising'``, the default, or ``'falling'``: the edge generated on the
            parent device's digital output to trigger the camera. If `parent_device`
            is a `Trigger`, it must have this edge type. This does not program the
            camera to expect the edge; set the camera's own trigger attributes in
            `camera_attributes` for that.
        trigger_duration : float, optional
            Duration in seconds of the trigger pulse the parent device generates, for
            each `expose` that gives none; `None` by default.
        minimum_recovery_time : float, optional
            Minimum time in seconds between one trigger pulse and the next; 0.0 by
            default. Closer triggers raise an error when the shot compiles.
        camera_attributes : dict, optional
            Camera attribute names and values to program into the camera, whose
            meaning depends on the camera model; empty by default. They are programmed
            in the order given, which matters where one cannot be set until another
            has been; PylonCamera orders its ROI attributes itself. Once the device is
            in the connection table, the Attributes dialog of its BLACS tab shows the
            camera's attributes in this form, to copy and edit.
        manual_mode_camera_attributes : dict, optional
            Attributes whose values in manual mode differ from those in
            `camera_attributes`, in which each must also be present; empty by default.
            For example, software triggering in manual mode, to acquire frames from
            the BLACS tab, and hardware triggering in buffered mode.
        stop_acquisition_timeout : float, optional
            Seconds to wait, at the end of a shot, for the images to be acquired
            before giving up; 5.0 by default. All the triggers have been sent by
            then, so this allows for slow image download.
        exception_on_failed_shot : bool, optional
            Whether acquisition not completing within `stop_acquisition_timeout`
            raises an exception, as it does by default. If False, a warning goes to
            stderr (shown in the BLACS tab's terminal output pane) instead, the images
            acquired so far are saved, and the shot continues. A shot that acquired
            fewer images than it had exposures sets the ``failed_shot`` attribute of
            ``images/<orientation>`` (``images/<name>`` if `orientation` is `None`) to
            True; any other shot with exposures sets it to False. In lyse's dataframe
            it is the column ``(<orientation or name>, 'failed_shot')``.
        saved_attribute_visibility_level : str or None, optional
            The detail level of the camera attributes saved, at the end of each shot,
            as attributes of ``images/<orientation>``: ``'simple'``,
            ``'intermediate'`` (the default) or ``'advanced'``. `None` saves none.
            FlyCapture2 has no such levels, so a FlyCapture2Camera saves every
            attribute at any of them.
        **kwargs
            Passed to :class:`~labscript.TriggerableDevice`.
        """
        self.trigger_edge_type = trigger_edge_type
        self.minimum_recovery_time = minimum_recovery_time
        self.trigger_duration = trigger_duration
        self.orientation = orientation
        self.pixel_size = pixel_size
        self.magnification = magnification
        self._set_serial_number(serial_number)
        if camera_attributes is None:
            camera_attributes = {}
        if manual_mode_camera_attributes is None:
            manual_mode_camera_attributes = {}
        for attr_name in manual_mode_camera_attributes:
            if attr_name not in camera_attributes:
                msg = f"""The camera {name} gives manual_mode_camera_attributes an
                    attribute {attr_name!r} that is not in camera_attributes. Add it
                    to camera_attributes, with its value for buffered mode."""
                raise ValueError(dedent(msg))
        valid_attr_levels = ('simple', 'intermediate', 'advanced', None)
        if saved_attribute_visibility_level not in valid_attr_levels:
            msg = f"saved_attribute_visibility_level must be one of {valid_attr_levels}."
            raise ValueError(msg)
        self.camera_attributes = camera_attributes
        self.manual_mode_camera_attributes = manual_mode_camera_attributes
        self.exposures = []
        TriggerableDevice.__init__(self, name, parent_device, connection, **kwargs)

    def _set_serial_number(self, serial_number):
        """Set `serial_number` and `BLACS_connection` from the serial number given to
        `__init__`. A camera with another serial number format overrides this."""
        if isinstance(serial_number, bytes):
            serial_number = serial_number.decode()
        if isinstance(serial_number, str):
            if serial_number.lower().startswith('0x'):
                serial_number = int(serial_number, 16)
            else:
                if not serial_number.isdigit():
                    raise LabscriptError(
                        f"The serial_number {serial_number!r} is not a decimal number. "
                        f"If it is hex, write '0x{serial_number}'."
                    )
                # LEGACY HEX SERIAL NUMBER WARNING. DEPRECATED CODE, WILL BE REMOVED.
                if self.hex_serial_numbers:
                    warnings.warn(
                        f"The serial_number {serial_number!r} is now read as decimal. "
                        f"If it is hex, write '0x{serial_number}'.",
                        FutureWarning,
                        stacklevel=4,
                    )
                serial_number = int(serial_number)
        self.serial_number = serial_number
        self.BLACS_connection = hex(self.serial_number)[2:].upper()

    def expose(self, t, name, frametype='frame', trigger_duration=None):
        """Request an exposure at time `t` by triggering the camera.

        Parameters
        ----------
        t : float
            Time in seconds of the trigger edge.
        name : str
            What the image shows, such as ``'insitu_absorption'`` or
            ``'fluorescence'``. With `frametype` it sets where the image is stored in
            the shot file, under ``images/<orientation>/<name>/<frametype>``.
        frametype : str, optional
            The type of frame, for imaging methods that take several. An absorption
            image might have three, ``'probe'``, ``'atoms'`` and ``'background'``, by
            calling `expose` three times with one `name`. ``'frame'`` by default.
        trigger_duration : float, optional
            Duration in seconds of the trigger pulse, greater than 0; the device's
            `trigger_duration` by default.

        Returns
        -------
        float
            The trigger duration used.
        """
        # Backward compatibility with scripts that call expose(name, t):
        if isinstance(t, str) and isinstance(name, (int, float)):
            msg = """expose() takes `t` first and `name` second, but was called with a
                string first and a number second. It swaps them and goes on; call
                expose(t, name) in that order."""
            print(dedent(msg), file=sys.stderr)
            t, name = name, t
        if trigger_duration is None:
            trigger_duration = self.trigger_duration
        if trigger_duration is None:
            msg = f"""{self.description} {self.name} has no trigger_duration, and none
                was given for this exposure. Pass trigger_duration to expose() or when
                creating the device."""
            raise ValueError(dedent(msg))
        if not trigger_duration > 0:
            msg = f"trigger_duration must be > 0, not {trigger_duration}"
            raise ValueError(msg)
        self.trigger(t, trigger_duration)
        self.exposures.append((t, name, frametype, trigger_duration))
        return trigger_duration

    def generate_code(self, hdf5_file):
        """Write the exposures to an EXPOSURES dataset, if there are any."""
        self.do_checks()
        vlenstr = h5py.special_dtype(vlen=str)
        table_dtypes = [
            ('t', float),
            ('name', vlenstr),
            ('frametype', vlenstr),
            ('trigger_duration', float),
        ]
        data = np.array(self.exposures, dtype=table_dtypes)
        group = self.init_device_group(hdf5_file)
        if self.exposures:
            group.create_dataset('EXPOSURES', data=data)
