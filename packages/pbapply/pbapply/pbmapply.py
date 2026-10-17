"""Progress-bar mapply."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from pbapply.closepb import closepb
from pbapply.mapply import mapply
from pbapply.setpb import setpb
from pbapply.startpb import startpb


def pbmapply(
    FUN: Callable[..., Any],
    *args: Any,
    MoreArgs: Mapping[str, Any] | None = None,
    SIMPLIFY: bool = True,
    USE_NAMES: bool = True,
) -> Any:
    """Call mapply with a progress bar tick after each evaluation of FUN."""
    from pbapply.mapply import _r_length

    max_len = max((_r_length(a) for a in args), default=0)
    pb = startpb(0, max_len)
    value = 0

    def traced(*a: Any, **kw: Any) -> Any:
        nonlocal value
        value += 1
        setpb(pb, value)
        return FUN(*a, **kw)

    try:
        return mapply(
            traced,
            *args,
            MoreArgs=MoreArgs,
            SIMPLIFY=SIMPLIFY,
            USE_NAMES=USE_NAMES,
        )
    finally:
        closepb(pb)
