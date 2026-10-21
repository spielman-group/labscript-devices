#####################################################################
#                                                                   #
# /labscript_devices/PrawnDO/register_classes.py                    #
#                                                                   #
# Copyright 2023, Philip Starkey, Carter Turnbaugh, Patrick Miller  #
#                                                                   #
# This file is part of labscript_devices, in the labscript suite    #
# (see http://labscriptsuite.org), and is licensed under the        #
# Simplified BSD License. See the license.txt file in the root of   #
# the project for the full license.                                 #
#                                                                   #
#####################################################################
from labscript_devices import register_classes

register_classes(
    'PrawnDO',
    BLACS_tab='labscript_devices.PrawnDO.blacs_tabs.PrawnDOTab',
    runviewer_parser='labscript_devices.PrawnDO.runviewer_parsers.PrawnDOParser',
)

# Runviewer needs a parser for the internal intermediate device, which hands the
# clock line's clock on to the trigger that starts the PrawnDO.
register_classes(
    '_PrawnDOIntermediateDevice',
    BLACS_tab=None,
    runviewer_parser='labscript_devices.PrawnDO.runviewer_parsers._PrawnDOIntermediateParser',
)
