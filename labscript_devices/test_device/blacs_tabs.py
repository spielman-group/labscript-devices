from labscript_utils.file_utils import warn_legacy_file


class TestDeviceTab(object):
    pass


# LEGACY TEST_DEVICE CLASS NAME COMPATIBILITY. DEPRECATED CODE, WILL BE REMOVED.
class test_deviceTab(TestDeviceTab):
    def __init__(self, notebook, settings):
        warn_legacy_file(
            settings['connection_table'].filepath,
            "names the test device's class test_device, not TestDevice",
        )
        super().__init__(notebook, settings)
