import labscript_devices

labscript_device_name = 'test_device'
blacs_tab = 'labscript_devices.test_device.blacs_tabs.test_deviceTab'
parser = 'labscript_devices.test_device.runviewer_parsers.test_deviceParser'

labscript_devices.register_classes(
    labscript_device_name=labscript_device_name,
    BLACS_tab=blacs_tab,
    runviewer_parser=parser,
)
