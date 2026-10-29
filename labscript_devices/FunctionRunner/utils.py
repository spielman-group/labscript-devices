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

# Each source file's lines as linecache last gave them, and the source of each
# function in it, by line number:
_source_cache = {}


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
    if function.__name__ == '<lambda>':
        msg = """A lambda cannot be added. Define the function with def, because the
            worker finds it by its name in its source code."""
        raise TypeError(dedent(msg))

    # inspect.getsource scans the file for the function's block on every call, which is
    # slow for a shot of many functions; each block is found once per version of a file.
    lines, lnum = inspect.findsource(inspect.unwrap(function))
    cached_lines, sources = _source_cache.get(function.__code__.co_filename, (None, None))
    if cached_lines is not lines:
        sources = {}
        _source_cache[function.__code__.co_filename] = (lines, sources)
    if lnum not in sources:
        sources[lnum] = ''.join(inspect.getblock(lines[lnum:]))
    source = textwrap.dedent(sources[lnum])
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
