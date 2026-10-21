import warnings

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


# LEGACY TEST_DEVICE CLASS NAME COMPATIBILITY. DEPRECATED CODE, WILL BE REMOVED.
class test_device(TestDevice):
    """The old name of :class:`TestDevice`: creating one gives a FutureWarning."""

    def __init__(self, *args, **kwargs):
        warnings.warn(
            "test_device will be removed; use TestDevice.", FutureWarning, stacklevel=2
        )
        super().__init__(*args, **kwargs)
