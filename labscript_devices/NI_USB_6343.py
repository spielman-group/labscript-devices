#####################################################################
#                                                                   #
# /NI_USB_6343.py                                                   #
#                                                                   #
# Copyright 2013, Monash University                                 #
#                                                                   #
# This file is part of labscript_devices, in the labscript suite    #
# (see http://labscriptsuite.org), and is licensed under the        #
# Simplified BSD License. See the license.txt file in the root of   #
# the project for the full license.                                 #
#                                                                   #
#####################################################################
from labscript_devices import lazy_attributes

# LEGACY NI_DAQMX IMPORT PATH COMPATIBILITY. DEPRECATED CODE, WILL BE REMOVED.
__getattr__ = lazy_attributes(
    __name__, {'labscript_devices.NI_DAQmx.labscript_devices': ['NI_USB_6343']}, legacy=True
)
__all__ = ['NI_USB_6343']
