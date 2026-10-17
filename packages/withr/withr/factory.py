"""The constructors for with_* and local_* functions (R's with_() and local_()).

``with_(set, reset, get)`` returns ``with_fn(new, code, **kwargs)``: it sets
the state, calls ``code()`` and resets the state in a ``finally``.

``local_(set, reset, get)`` returns ``local_fn(new, _local_envir=None, **kwargs)``:
it sets the state and registers the reset on the frame. ``_local_envir``
defaults to the innermost ``scope()``.

Extra keyword arguments go to ``set`` (and ``get``) by name. With ``dots=True``
the names that ``set`` does not take are merged into ``new``, as R's ``...``.
"""

from __future__ import annotations

import inspect

from ._scope import current, force


def _accepted(fn) -> set[str]:
    try:
        return set(inspect.signature(fn).parameters)
    except (TypeError, ValueError):
        return set()


def with_(set_fn, reset_fn=None, get_fn=None, *, new: bool = True):
    reset = reset_fn if reset_fn is not None else set_fn

    def run(call_args, kwargs, code):
        if get_fn is None:
            old = set_fn(*call_args, **kwargs)
            try:
                return force(code)
            finally:
                reset(old)
        old = get_fn(*call_args, **kwargs)
        try:
            set_fn(*call_args, **kwargs)
            return force(code)
        finally:
            reset(old)

    if new:

        def with_fn(new, code, **kwargs):
            return run((new,), kwargs, code)

    else:

        def with_fn(code, **kwargs):
            return run((), kwargs, code)

    return with_fn


def local_(set_fn, reset_fn=None, get_fn=None, *, new: bool = True, dots: bool = False):
    reset = reset_fn if reset_fn is not None else set_fn

    def apply(call_args, kwargs, local_envir):
        if get_fn is None:
            old = set_fn(*call_args, **kwargs)
            current(local_envir).add(lambda: reset(old))
        else:
            old = get_fn(*call_args, **kwargs)
            current(local_envir).add(lambda: reset(old))
            set_fn(*call_args, **kwargs)
        return old

    if not new:

        def local_fn(*args, _local_envir=None, **kwargs):
            return apply(args, kwargs, _local_envir)

        return local_fn

    if dots:
        accepted = _accepted(set_fn)

        def local_fn(new=None, *, _local_envir=None, **kwargs):
            known = {k: v for k, v in kwargs.items() if k in accepted}
            extra = {k: v for k, v in kwargs.items() if k not in accepted}
            merged = dict(new or {})
            merged.update(extra)
            return apply((merged,), known, _local_envir)

        return local_fn

    def local_fn(new, *, _local_envir=None, **kwargs):
        return apply((new,), kwargs, _local_envir)

    return local_fn
