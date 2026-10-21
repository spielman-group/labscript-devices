#####################################################################
#                                                                   #
# /labscript_devices/ZaberStageController/utils.py                  #
#                                                                   #
# Copyright 2019, Monash University and contributors                #
#                                                                   #
# This file is part of labscript_devices, in the labscript suite    #
# (see http://labscriptsuite.org), and is licensed under the        #
# Simplified BSD License. See the license.txt file in the root of   #
# the project for the full license.                                 #
#                                                                   #
#####################################################################

from labscript_utils import dedent


def get_device_number(connection_str):
    """Return n from a connection 'device <n>' with n > 0, else raise ValueError."""
    try:
        prefix, num = connection_str.split(' ')
        num = int(num)
        if prefix != 'device' or num <= 0:
            raise ValueError
    except (TypeError, ValueError):
        msg = f"""Connection string '{connection_str}' is not of the form 'device <n>'
            with n > 0. Use a connection such as 'device 1'."""
        raise ValueError(dedent(msg)) from None
    return num
