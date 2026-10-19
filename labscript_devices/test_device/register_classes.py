from labscript_devices import register_classes

register_classes(
    'test_device',
    BLACS_tab='labscript_devices.test_device.blacs_tabs.test_deviceTab',
    runviewer_parser='labscript_devices.test_device.runviewer_parsers.test_deviceParser',
)
