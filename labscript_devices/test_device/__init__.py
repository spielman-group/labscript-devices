from labscript_devices.common.deprecation import deprecated_names

# LEGACY DEVICE MODULE IMPORT PATH COMPATIBILITY. DEPRECATED CODE, WILL BE REMOVED.
__getattr__ = deprecated_names(
    __name__,
    {
        'labscript_devices': [
            'test_device',
        ],
    },
)
