from labscript_utils.file_utils import warn_legacy_file


class TestDeviceTab:
    """An empty placeholder: BLACS cannot build a tab from it."""


# LEGACY TEST_DEVICE CLASS NAME COMPATIBILITY. DEPRECATED CODE, WILL BE REMOVED.
class test_deviceTab(TestDeviceTab):
    def __init__(self, notebook, settings):
        warn_legacy_file(
            settings['connection_table'].filepath,
            "names the test device's class test_device, not TestDevice",
        )
        # TestDeviceTab takes no arguments, so this raises TypeError, as BLACS's own
        # build of a TestDeviceTab does.
        super().__init__(notebook, settings)
