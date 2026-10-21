from labscript_utils.file_utils import warn_legacy_file


class TestDeviceParser:
    """An empty placeholder: runviewer cannot build it from a path and a device."""


# LEGACY TEST_DEVICE CLASS NAME COMPATIBILITY. DEPRECATED CODE, WILL BE REMOVED.
class test_deviceParser(TestDeviceParser):
    def __init__(self, path, device):
        warn_legacy_file(
            path, "names the test device's class test_device, not TestDevice"
        )
        # TestDeviceParser takes no arguments, so this raises TypeError, as runviewer's
        # own build of a TestDeviceParser does.
        super().__init__(path, device)
