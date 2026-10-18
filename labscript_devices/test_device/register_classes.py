import labscript_devices

labscript_device_name = 'test_device'
blacs_tab = 'labscript_devices.test_device.blacs_tabs.Tab'
parser = 'labscript_devices.test_device.runviewer_parsers.Parser'

labscript_devices.register_classes(
    labscript_device_name=labscript_device_name,
    BLACS_tab=blacs_tab,
    runviewer_parser=parser,
)
