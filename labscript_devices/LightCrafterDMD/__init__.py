#####################################################################
#                                                                   #
# /labscript_devices/LightCrafterDMD/__init__.py                    #
#                                                                   #
# Copyright 2017, Monash University                                 #
#                                                                   #
# This file is part of labscript_devices, in the labscript suite    #
# (see http://labscriptsuite.org), and is licensed under the        #
# Simplified BSD License. See the license.txt file in the root of   #
# the project for the full license.                                 #
#                                                                   #
#####################################################################

from labscript_devices import lazy_attributes
from .labscript_devices import ImageSet, LightCrafterDMD, arr_to_bmp, BLANK_BMP, HEIGHT, WIDTH

__getattr__ = lazy_attributes(
    __name__,
    {
        'blacs_tabs': ['LightCrafterTab'],
        'blacs_workers': ['LightCrafterWorker'],
    },
)
