"""Progress-bar replicate."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from pbapply.pbsapply import pbsapply


def pbreplicate(
    n: int,
    expr: Callable[[], Any],
    *args: Any,
    simplify: bool | str = True,
    cl: Any = None,
    **kwargs: Any,
) -> Any:
    """Evaluate expr n times with a progress bar."""
    if not callable(expr):
        raise TypeError("expr must be callable")
    indices = [0] * int(n)

    def runner(_ignored: int) -> Any:
        return expr()

    return pbsapply(indices, runner, *args, simplify=simplify, cl=cl, **kwargs)
