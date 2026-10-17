"""The slice of rlang 1.3.0 that httr2, lifecycle, and vctrs call."""

from __future__ import annotations

import importlib.util
import os
import sys
import warnings
from pathlib import Path


class RLangError(Exception):
    pass


class Zap:
    """The rlang zap sentinel."""


class Splice(list):
    """A list that list2 splices. This is the Python form of !!!."""


class Named(list):
    def __init__(self, values, names):
        super().__init__(values)
        self.names = ["" if name is None else str(name) for name in names]


def null_or(left, right):
    """The operator %||%."""
    return right if left is None else left


def abort(message, **_kwargs):
    raise RLangError(str(message))


def warn(message, **_kwargs):
    warnings.warn(str(message), stacklevel=2)


def inform(message, **_kwargs):
    print(message)


def _partial(arg, values):
    if arg in values:
        return arg
    matches = [item for item in values if item.startswith(arg)]
    if len(matches) == 1:
        return matches[0]
    if not matches:
        raise RLangError(f"{arg!r} must be one of {', '.join(repr(v) for v in values)}")
    raise RLangError(f"{arg!r} matches multiple values")


def arg_match0(arg, values, *, error_call=None):
    return _partial(arg, list(values))


def arg_match(arg, values=None, *, values_arg="values", error_arg=None, error_call=None):
    choices = values if values is not None else []
    return _partial(arg, list(choices))


def seq2(from_, to):
    start = int(from_)
    stop = int(to)
    if start > stop:
        return []
    return list(range(start, stop + 1))


def set_names(x, names):
    values = list(x)
    return Named(values, list(names))


def names2(x):
    names = getattr(x, "names", None)
    if names is None:
        return [""] * len(list(x))
    return ["" if name is None else str(name) for name in names]


def is_null(x):
    return x is None


def is_character(x):
    if isinstance(x, str):
        return True
    return isinstance(x, (list, tuple)) and all(isinstance(item, str) for item in x)


def is_logical(x):
    if isinstance(x, bool):
        return True
    return isinstance(x, (list, tuple)) and all(isinstance(item, bool) for item in x)


def is_integer(x):
    if isinstance(x, bool):
        return False
    if isinstance(x, int):
        return True
    return isinstance(x, (list, tuple)) and all(isinstance(item, int) and not isinstance(item, bool) for item in x)


def is_double(x):
    if isinstance(x, bool) or isinstance(x, int):
        return False
    if isinstance(x, float):
        return True
    return isinstance(x, (list, tuple)) and all(isinstance(item, float) for item in x)


def is_atomic(x):
    if isinstance(x, (list, tuple)):
        return False
    return x is None or isinstance(x, (bool, int, float, str, bytes, bytearray))


def is_list(x):
    return isinstance(x, list) and not is_character(x)


def is_function(x):
    return callable(x) and not isinstance(x, type)


def _scalar(x, pred):
    if pred(x) and not isinstance(x, (list, tuple)):
        return True
    return isinstance(x, (list, tuple)) and len(x) == 1 and pred(x[0])


def is_scalar_character(x):
    return isinstance(x, str) or (isinstance(x, (list, tuple)) and len(x) == 1 and isinstance(x[0], str))


def is_scalar_logical(x):
    return isinstance(x, bool) or (isinstance(x, (list, tuple)) and len(x) == 1 and isinstance(x[0], bool))


def is_scalar_integer(x):
    return (isinstance(x, int) and not isinstance(x, bool)) or (
        isinstance(x, (list, tuple)) and len(x) == 1 and isinstance(x[0], int) and not isinstance(x[0], bool)
    )


def is_scalar_double(x):
    return isinstance(x, float) or (isinstance(x, (list, tuple)) and len(x) == 1 and isinstance(x[0], float))


def is_true(x):
    return x is True


def is_false(x):
    return x is False


def is_empty(x):
    if x is None:
        return True
    try:
        return len(x) == 0
    except TypeError:
        return False


def has_length(x, n):
    if x is None:
        return n == 0
    try:
        return len(x) == n
    except TypeError:
        return n == 1


def is_string(x, string=None):
    if not isinstance(x, str):
        return False
    if string is None:
        return True
    return x == string


def is_interactive():
    if os.environ.get("rlib_interactive") == "false":
        return False
    return hasattr(sys, "ps1")


def is_installed(pkg):
    if importlib.util.find_spec(pkg) is not None:
        return True
    roots = [Path.home() / "R" / "library", Path("/usr/lib/R/site-library"), Path("/usr/lib/R/library")]
    return any((root / pkg).is_dir() for root in roots)


def check_installed(pkg, reason=None):
    if not is_installed(pkg):
        extra = f" {reason}" if reason else ""
        raise RLangError(f'The package "{pkg}" is required.')
    return True


def list2(*args, **kwargs):
    out = []
    for item in args:
        if isinstance(item, Splice):
            out.extend(item)
        else:
            out.append(item)
    if kwargs:
        return {**{str(index): value for index, value in enumerate(out)}, **kwargs}
    return out


def exec(fn, *args, **kwargs):
    return fn(*args, **kwargs)


def try_fetch(fn, *handlers):
    try:
        return fn()
    except Exception as exc:
        for kind, handler in handlers:
            if isinstance(exc, kind):
                return handler(exc)
        raise


def inject(fn, *args, **kwargs):
    return fn(*args, **kwargs)


def zap():
    return Zap()


def as_function(x):
    if callable(x):
        return x
    raise RLangError("x must be a function")


class Env(dict):
    pass


def env(**kwargs):
    return Env(kwargs)


def new_environment(parent=None, size=None):
    return Env()


def env_get(env, name, default=None, inherit=False):
    if name in env:
        return env[name]
    if default is not None or name in env:
        return default
    raise RLangError(f"Can't find `{name}` in environment.")


def env_poke(env, name, value, inherit=False, create=True):
    env[name] = value
    return env


def env_has(env, name, inherit=False):
    return name in env


def env_names(env):
    return list(env)


def env_unbind(env, *names):
    for name in names:
        env.pop(name, None)
    return env


def env_cache(env, name, default):
    if name not in env:
        env[name] = default() if callable(default) else default
    return env[name]


def env_get_list(env, names, default=None):
    return [env[name] if name in env else default for name in names]


def caller_env(n=1):
    return sys._getframe(n + 1).f_globals


def caller_arg(arg):
    frame = sys._getframe(1)
    for name, value in frame.f_locals.items():
        if value is arg:
            return name
    return ""


def args_dots_empty(*_args, **_kwargs):
    return None


def args_error_context(*_args, **_kwargs):
    return None


def format_error_bullets(bullets):
    if isinstance(bullets, dict):
        items = bullets.items()
    else:
        items = getattr(bullets, "names", None)
        if items is None:
            items = [(None, item) for item in bullets]
        else:
            items = zip(bullets.names, bullets)
    lines = []
    for name, text in items:
        if name in (None, "", "*"):
            lines.append(f"\u2022 {text}")
        elif name == "x":
            lines.append(f"\u2716 {text}")
        elif name == "i":
            lines.append(f"\u2139 {text}")
        else:
            lines.append(str(text))
    return "\n".join(lines)
from rlang.null_and import null_and
from rlang.na_or import na_or
from rlang.slot import slot
from rlang.slot import slot_replace
from rlang.colon_equals import colon_equals
from rlang.are_na import are_na
from rlang.eager_pipe import eager_pipe
from rlang.as_box import as_box
from rlang.as_string import as_string
from rlang.is_formula import is_formula
from rlang.as_label import as_label
from rlang.env_bind import env_bind
from rlang.as_name import as_name
from rlang.is_symbol import is_symbol
from rlang.is_call import is_call
from rlang.is_quosure import is_quosure
from rlang.sym import sym
from rlang.as_bytes import as_bytes
from rlang.obj_address import obj_address
from rlang.check_bool import check_bool
from rlang.eval_bare import eval_bare
from rlang.hash import hash
from rlang.check_string import check_string
from rlang.parse_expr import parse_expr
from rlang.check_data_frame import check_data_frame
from rlang.duplicate import duplicate
