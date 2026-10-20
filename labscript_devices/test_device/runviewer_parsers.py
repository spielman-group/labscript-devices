from labscript_utils.file_utils import warn_legacy_file


class TestDeviceParser(object):
    pass


# LEGACY TEST_DEVICE CLASS NAME COMPATIBILITY. DEPRECATED CODE, WILL BE REMOVED.
class test_deviceParser(TestDeviceParser):
    def __init__(self, path, device):
        warn_legacy_file(path, "names the test device's class test_device, not TestDevice")
        super().__init__(path, device)
