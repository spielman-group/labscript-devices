#####################################################################
#                                                                   #
# /labscript_devices/FunctionRunner/utils.py                        #
#                                                                   #
# Copyright 2019, Monash University and contributors                #
#                                                                   #
# This file is part of labscript_devices, in the labscript suite    #
# (see http://labscriptsuite.org), and is licensed under the        #
# Simplified BSD License. See the license.txt file in the root of   #
# the project for the full license.                                 #
#                                                                   #
#####################################################################

import inspect
import textwrap
from types import FunctionType
from labscript_utils import dedent, ensure_str
import labscript_utils.properties as properties


def serialise_function(function, *args, **kwargs):
    """Return a function's name and source, and its extra args and kwargs serialised."""
    signature = inspect.signature(function)
    if not tuple(signature.parameters)[:2] == ('shot_context', 't'):
        msg = """The function's first two parameters must be named shot_context and t,
            as in def func(shot_context, t, ...)."""
        raise ValueError(dedent(msg))
    # Raises TypeError if the arguments do not fit the function's signature.
    _ = signature.bind(None, None, *args, **kwargs)

    if not isinstance(function, FunctionType):
        msg = f"""A callable of type {type(function).__name__} cannot be added. Only a
            function defined with def can, because it is saved by its source code."""
        raise TypeError(dedent(msg))

    source = textwrap.dedent(inspect.getsource(function))
    args = properties.serialise(args)
    kwargs = properties.serialise(kwargs)

    return function.__name__, source, args, kwargs


def deserialise_function(
    name, source, args, kwargs, __name__=None, __file__='<string>'
):
    """Rebuild a function from what `serialise_function` returned."""
    name = ensure_str(name)
    args = properties.deserialise(args)
    kwargs = properties.deserialise(kwargs)
    code = compile(source, '<string>', 'exec', dont_inherit=True,)
    namespace = {'__name__': __name__, '__file__': __file__}
    exec(code, namespace)
    return namespace[name], args, kwargs
