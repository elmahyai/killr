"""Non-destructively construct a .Last function (gtools 3.9.5 ``lastAdd``)."""

from __future__ import annotations

from typing import Any

# Stand-in for R's ``.GlobalEnv``. ``lastAdd`` reads ``.Last`` only from here.
global_env: dict[str, Any] = {}

__all__ = ["global_env", "lastAdd"]


def _is_function(value: Any) -> bool:
    """R ``is.function``: a callable, not a class."""
    if isinstance(value, type):
        return False
    return callable(value)


def lastAdd(fun):
    """Return ``fun``, or a function that calls ``fun`` then the current ``.Last``.

    A missing ``.Last``, or a ``.Last`` that is not a function, yields ``fun``
    itself. Otherwise the previous ``.Last`` is stored in the wrapper, and a
    later assignment does not change that stored function. The wrapper accepts
    extra arguments and ignores them. ``fun`` runs first; its value is
    discarded. The wrapper returns whatever the stored ``.Last`` returns.
    """
    if not _is_function(fun):
        raise ValueError("fun must be a function")

    last = global_env.get(".Last")
    if not _is_function(last):
        return fun

    def newfun(*_args, **_kwargs):
        fun()
        return last()

    return newfun
