"""Progress-bar sapply."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import numpy as np

from pbapply._simplify import simplify2array
from pbapply.pblapply import pblapply


def pbsapply(
    X: Any,
    FUN: Callable[..., Any],
    *args: Any,
    simplify: bool | str = True,
    USE_NAMES: bool = True,
    cl: Any = None,
    **kwargs: Any,
) -> Any:
    """Apply FUN to each element of X and simplify when possible."""
    answer = pblapply(X, FUN, *args, cl=cl, **kwargs)
    x_names = _names(X)
    if USE_NAMES and _is_character_named(x_names) and _answer_names(answer) is None:
        _set_names(answer, x_names)
    if simplify is not False and len(answer):
        higher = simplify == "array"
        return simplify2array(answer, higher=higher)
    return answer


def _names(x: Any) -> list[str | None] | None:
    names = getattr(x, "names", None)
    if names is not None:
        return list(names)
    if isinstance(x, dict):
        return [str(key) for key in x]
    return None


def _is_character_named(names: list[str | None] | None) -> bool:
    return names is not None and len(names) > 0 and all(isinstance(n, str) for n in names)


def _answer_names(answer: Any) -> list[str | None] | None:
    names = getattr(answer, "names", None)
    if names is None:
        return None
    return list(names)


def _set_names(answer: list[Any], names: list[str | None]) -> None:
    if len(names) != len(answer):
        return
    try:
        answer.names = list(names)  # type: ignore[attr-defined]
    except AttributeError:
        pass
