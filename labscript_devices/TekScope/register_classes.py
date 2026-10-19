from labscript_devices import register_classes

register_classes(
    'TekScope',
    BLACS_tab='labscript_devices.TekScope.blacs_tabs.TekScopeTab',
    runviewer_parser=None,
)
