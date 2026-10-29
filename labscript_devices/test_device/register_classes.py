from labscript_devices import register_classes

register_classes(
    'TestDevice',
    BLACS_tab='labscript_devices.test_device.blacs_tabs.TestDeviceTab',
    runviewer_parser='labscript_devices.test_device.runviewer_parsers.TestDeviceParser',
)
