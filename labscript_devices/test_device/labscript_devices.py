from labscript import Device, LabscriptError, set_passed_properties


class TestDevice(Device):
    """A device that does nothing, for testing labscript's infrastructure."""

    description = 'test device'

    @set_passed_properties(
        property_names={
            "connection_table_properties": ["name"],
            "device_properties": ["DoSomething"],
        }
    )
    def __init__(self, name, DoSomething=False, **kwargs):
        """
        Parameters
        ----------
        name : str
            Python variable name of the device.
        DoSomething : bool, optional
            Must be ``False``, the default: the device does nothing, and any other
            value raises ``LabscriptError``.
        **kwargs
            Passed to :class:`~labscript.Device`, which is given no parent device
            and no connection.
        """
        if DoSomething is not False:
            raise LabscriptError(
                "TestDevice does nothing: DoSomething must be False, "
                f"not {DoSomething!r}."
            )

        Device.__init__(self, name, None, None, **kwargs)


def __getattr__(name):
    if name == 'test_device':
        raise ImportError("test_device is TestDevice: import and use TestDevice.")
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
