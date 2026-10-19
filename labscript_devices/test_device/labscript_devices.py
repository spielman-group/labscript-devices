import warnings

from labscript import Device, LabscriptError, set_passed_properties

class TestDevice(Device):
    description = 'test device'
    
    @set_passed_properties(
        property_names = {
                 "connection_table_properties": ["name"],
                 "device_properties": ["DoSomething"]}
        )
    def __init__(self, name, DoSomething = False, **kwargs):
        if DoSomething is not False:
            raise LabscriptError('TestDevice does nothing, but kwarg DoSomething was not passed False')


        Device.__init__(self, name, None, None, **kwargs)


# LEGACY TEST_DEVICE CLASS NAME COMPATIBILITY. DEPRECATED CODE, WILL BE REMOVED.
class test_device(TestDevice):
    def __init__(self, *args, **kwargs):
        warnings.warn("test_device will be removed; use TestDevice.", FutureWarning, stacklevel=2)
        super().__init__(*args, **kwargs)
