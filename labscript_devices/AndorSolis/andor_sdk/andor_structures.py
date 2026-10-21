# Wrapped structures found in the header file and the SDK docs.

import sys
import ctypes


class ColorDemosaicInfo(ctypes.Structure):
    """The SDK's options for demosaicing an image taken with a CYMG CCD."""

    # The input red, green and blue arrays have iX * iY elements. iAlgorithm is 0 for a
    # 2 x 2 matrix demosaic algorithm or 1 for a 3 x 3 one. iBackground is removed from
    # every pixel in the input image before demosaicing is done.
    _fields_ = [
        ('iX', ctypes.c_int),  # Number of X pixels, >2
        ('iY', ctypes.c_int),  # Number of Y pixels, >2
        ('iAlgorithm', ctypes.c_int),
        # iXPhase and iYPhase store what color is in the bottom left pixel (cyan, or
        # yellow, magenta or green).
        ('iXPhase', ctypes.c_int),
        ('iYPhase', ctypes.c_int),
        ('iBackground', ctypes.c_int),
    ]


class AndorCapabilities(ctypes.Structure):
    """The SDK's capabilities structure; ulSize must be set to the structure's size."""

    _fields_ = [
        ('ulSize', ctypes.c_ulong),
        ('ulAcqModes', ctypes.c_ulong),
        ('ulReadModes', ctypes.c_ulong),
        ('ulTriggerModes', ctypes.c_ulong),
        ('ulCameraType', ctypes.c_ulong),
        ('ulPixelMode', ctypes.c_ulong),
        ('ulSetFunctions', ctypes.c_ulong),
        ('ulGetFunctions', ctypes.c_ulong),
        ('ulFeatures', ctypes.c_ulong),
        ('ulPCICard', ctypes.c_ulong),
        ('ulEMGainCapability', ctypes.c_ulong),
        ('ulFTReadModes', ctypes.c_ulong),
    ]

    def __init__(self):
        self.ulSize = sys.getsizeof(self)
