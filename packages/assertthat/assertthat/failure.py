"""on_failure and on_failure<-."""

from __future__ import annotations

import inspect
from typing import Any, Callable


def _parameter_names(fn: Callable[..., Any]) -> list[str]:
    recorded = getattr(fn, "r_formals", None)
    if recorded is not None:
        return list(recorded)
    return [
        param.name
        for param in inspect.signature(fn).parameters.values()
        if param.kind
        not in (
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        )
    ]


def on_failure(x: Any, value: Callable[..., Any] | None = None) -> Any:
    """Read or set the failure message.

    ``on_failure(fn)`` returns the handler. ``on_failure(fn, value)`` is R's
    ``on_failure(fn) <- value``. The handler's formals must be ``call`` and
    ``env``, in that order.
    """
    if value is None:
        return getattr(x, "fail", None)
    if not callable(x):
        raise TypeError("on_failure replacement expects a function")
    if not callable(value):
        raise TypeError("on_failure value must be a function")
    if _parameter_names(value) != ["call", "env"]:
        raise ValueError("failure handler formals must be call, env")
    x.fail = value
    return x


def set_on_failure(x: Any, value: Callable[..., Any]) -> Any:
    """R's ``on_failure(x) <- value``."""
    return on_failure(x, value)
