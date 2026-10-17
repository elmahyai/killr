"""Progress-bar walk over a list."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from pbapply.pblapply import pblapply


def _match_fun(FUN: Any) -> Callable[..., Any]:
    if isinstance(FUN, str):
        import builtins

        found = getattr(builtins, FUN, None)
        if found is None or not callable(found):
            raise ValueError(f"could not find function {FUN!r}")
        return found
    if not callable(FUN):
        raise TypeError("FUN must be callable")
    return FUN


def _call_like_r(FUN: Callable[..., Any], *a: Any, **kw: Any) -> Any:
    if FUN is sum and len(a) == 1 and not isinstance(a[0], (list, tuple, dict)):
        return a[0]
    return FUN(*a, **kw)


def pbwalk(
    X: Any,
    FUN: Callable[..., Any],
    *args: Any,
    cl: Any = None,
    **kwargs: Any,
) -> Any:
    """Apply FUN to each element for side effects; return X invisibly."""
    FUN = _match_fun(FUN)

    def FUN2(*a: Any, **kw: Any) -> None:
        _call_like_r(FUN, *a, **kw)

    pblapply(X, FUN2, *args, cl=cl, **kwargs)
    return X
