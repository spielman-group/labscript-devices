import numpy as np
from labscript import Device
from labscript_utils import dedent
import labscript_utils.h5_lock, h5py
from .utils import serialise_function


class FunctionRunner(Device):
    """A labscript device that runs functions in software time, in BLACS, before the
    start or after the end of a shot."""

    def __init__(self, name, **kwargs):
        """
        Parameters
        ----------
        name : str
            Python variable name of the device.
        **kwargs
            Passed to :class:`~labscript.Device`; `parent_device` and `connection` are
            fixed at `None`, so cannot be given. `start_order` and `stop_order`, 0 by
            default, set when this device's functions run: BLACS transitions the
            devices to buffered mode in ascending `start_order`, running the start
            functions in this device's turn, and to manual mode in ascending
            `stop_order`, running the stop functions.
        """
        Device.__init__(self, name=name, parent_device=None, connection=None, **kwargs)
        self.functions = []
        self.BLACS_connection = name

    def add_function(self, t, function, *args, **kwargs):
        """Add a function for BLACS to run at the start or the end of the shot.

        Functions with the same `t` run in the order they were added. The device's
        `start_order` and `stop_order` set when they run relative to other devices.

        Parameters
        ----------
        t : {'start', 'stop'}
            ``'start'`` runs the function before the shot begins, and ``'stop'``
            after it has completed. Any other value is refused, a number with
            `NotImplementedError`, since running a function during the shot is not
            implemented.
        function : function
            Defined as ``def func(shot_context, t, ...)``, so its first two
            parameters must be named ``shot_context`` and ``t``. It is saved in the
            shot file as source code and run from that, so it must be
            self-contained, with any imports it needs inside it.
        *args, **kwargs
            The arguments the function is called with after `shot_context` and `t`.
            They are saved in the shot file by
            `labscript_utils.properties.serialise`, so a tuple becomes a list.

        Raises
        ------
        ValueError
            If the first two parameters of `function` are not ``shot_context`` and
            ``t``, or `t` is a string other than ``'start'`` and ``'stop'``.
        TypeError
            If `function` is not a function defined with ``def``, or `args` and
            `kwargs` do not fit its signature or cannot be serialised.
        NotImplementedError
            If `t` is a number.

        Notes
        -----
        BLACS calls ``function(shot_context, t, *args, **kwargs)``, where `t` is
        ``'start'`` or ``'stop'`` as given here. `shot_context` is the same object for
        every call in one shot, but a new one for the next shot, so a function can
        keep state for the shot in it, as a method does in ``self``. For example, a
        ``'start'`` function can set ``shot_context.serial`` to an open serial
        connection that the later functions use. `shot_context` has the attributes:

        - ``globals``: the shot's globals.
        - ``h5_file``: the path of the shot's HDF5 file.
        - ``device_name``: the name of this FunctionRunner.

        Examples
        --------
        A ``'stop'`` function saves raw data in the group ``data/<device_name>`` of
        the shot file::

            import h5py
            with h5py.File(shot_context.h5_file, 'r+') as f:
                data_group = f['data'].create_group(shot_context.device_name)
                # Save datasets and attributes within this group.

        This device was made to update runmanager's globals right after a shot, from
        measurement data, so that the shots compiled after it use the new values. A
        ``'stop'`` function calls the runmanager remote API::

            import runmanager.remote
            runmanager.remote.set_values({'x': 7})
        """
        name, source, args, kwargs = serialise_function(function, *args, **kwargs)
        if t == 'start':
            t = -np.inf
        elif t == 'stop':
            t = np.inf
        elif isinstance(t, str):
            raise ValueError(f"{self.name}: t is {t!r}. Give t as 'start' or 'stop'.")
        else:
            t = float(t)
            msg = f"""{self.name}: running functions during the shot is not implemented.
                Give t as 'start' or 'stop'."""
            raise NotImplementedError(dedent(msg))
        self.functions.append((t, name, source, args, kwargs))

    def generate_code(self, hdf5_file):
        # The sort is stable, so functions at the same time stay in the order added.
        self.functions.sort(key=lambda item: item[0])
        vlenstr = h5py.special_dtype(vlen=str)
        table_dtypes = [
            ('t', float),
            ('name', vlenstr),
            ('source', vlenstr),
            ('args', vlenstr),
            ('kwargs', vlenstr),
        ]
        function_table = np.array(self.functions, dtype=table_dtypes)
        group = self.init_device_group(hdf5_file)
        if self.functions:
            group.create_dataset('FUNCTION_TABLE', data=function_table)
