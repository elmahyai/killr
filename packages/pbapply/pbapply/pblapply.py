"""Progress-bar lapply (sequential path)."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from typing import Any

from pbapply.closepb import closepb
from pbapply.dopb import dopb
from pbapply.setpb import setpb
from pbapply.splitpb import splitpb
from pbapply.startpb import _pboptions, startpb


def _as_list(X: Any) -> tuple[list[Any], list[str] | None]:
    if isinstance(X, Mapping):
        keys = list(X.keys())
        return [X[k] for k in keys], [str(k) for k in keys]
    if isinstance(X, (str, bytes)):
        return [X], None
    if isinstance(X, Sequence):
        names = getattr(X, "names", None)
        if names is not None:
            return list(X), [str(n) for n in names]
        return list(X), None
    return [X], None


def pblapply(
    X: Any,
    FUN: Callable[..., Any],
    *args: Any,
    cl: Any = None,
    **kwargs: Any,
) -> list[Any]:
    """Apply FUN to each element of X with a progress bar when dopb() is true."""
    if cl is not None:
        raise NotImplementedError("parallel cl= is not translated yet")

    items, names = _as_list(X)
    if not items:
        return []

    if not dopb():
        out = [FUN(x, *args, **kwargs) for x in items]
    else:
        nout = int(_pboptions.get("nout", 100))
        splits = splitpb(len(items), 1, nout=nout)
        pb = startpb(0, len(splits))
        out = []
        try:
            for i, split in enumerate(splits, start=1):
                chunk = [items[j - 1] for j in split]
                out.extend(FUN(x, *args, **kwargs) for x in chunk)
                setpb(pb, i)
        finally:
            closepb(pb)

    if names is not None and len(names) == len(out):
        return _NamedList(out, names)
    return out


class _NamedList(list):
    __slots__ = ("names",)

    def __init__(self, values: Sequence[Any], names: Sequence[str]) -> None:
        super().__init__(values)
        self.names = list(names)
