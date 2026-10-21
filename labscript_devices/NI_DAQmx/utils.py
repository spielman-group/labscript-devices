#####################################################################
#                                                                   #
# /NI_DAQmx/utils.py                                                #
#                                                                   #
# Copyright 2018, Monash University, JQI, Christopher Billington    #
#                                                                   #
# This file is part of the module labscript_devices, in the         #
# labscript suite (see http://labscriptsuite.org), and is           #
# licensed under the Simplified BSD License. See the license.txt    #
# file in the root of the project for the full license.             #
#                                                                   #
#####################################################################
from labscript_utils import dedent


def split_conn_DO(connection):
    """Return (port, line) from 'port<N>/line<M>', which a ' (PFI<K>)' may follow."""
    try:
        port_line = connection
        if len(connection.split()) == 2:
            # Just raise a ValueError if the second bit isn't of the form ('PFI<n>')
            port_line, PFI_bit = connection.split()
            if not (PFI_bit.startswith('(') and PFI_bit.endswith(')')):
                raise ValueError
            split_conn_PFI(PFI_bit[1:-1])
        port, line = [int(n) for n in port_line.split('port', 1)[1].split('/line')]
    except (ValueError, IndexError):
        msg = f"""Digital output connection string {connection!r} does not match
            'port<N>/line<M>' for integers N, M, optionally followed by ' (PFI<K>)'
            for an integer K."""
        raise ValueError(dedent(msg))
    return port, line


def split_conn_AO(connection):
    """Return N from 'ao<N>'."""
    try:
        return int(connection.split('ao', 1)[1])
    except (ValueError, IndexError):
        msg = f"""Analog output connection string {connection!r} does not match
            'ao<N>' for an integer N."""
        raise ValueError(dedent(msg))


def split_conn_AI(connection):
    """Return N from 'ai<N>'."""
    try:
        return int(connection.split('ai', 1)[1])
    except (ValueError, IndexError):
        msg = f"""Analog input connection string {connection!r} does not match
            'ai<N>' for an integer N."""
        raise ValueError(dedent(msg))


def split_conn_PFI(connection):
    """Return N from 'PFI<N>'."""
    try:
        return int(connection.split('PFI', 1)[1])
    except (ValueError, IndexError):
        msg = f"PFI connection string {connection!r} does not match 'PFI<N>' for integer N."
        raise ValueError(msg)


def split_conn_port(connection):
    """Return N from 'port<N>'."""
    try:
        return int(connection.split('port', 1)[1])
    except (ValueError, IndexError):
        msg = f"port string {connection!r} does not match 'port<N>' for an integer N."
        raise ValueError(msg)
