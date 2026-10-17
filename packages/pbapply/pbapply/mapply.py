"""R-style mapply and pb.mapply helpers."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping, Sequence
from typing import Any

from pbapply.closepb import closepb
from pbapply.setpb import setpb
from pbapply.startpb import startpb


def _r_length(x: Any) -> int:
    if x is None:
        return 0
    if isinstance(x, (str, bytes)):
        return 1
    if isinstance(x, Mapping):
        return len(x)
    try:
        return len(x)
    except TypeError:
        return 1


def _recycle(x: Any, n: int) -> list[Any]:
    if n == 0:
        return []
    length = _r_length(x)
    if length == 0:
        return [x] * n
    if isinstance(x, Mapping):
        keys = list(x.keys())
        recycled_keys = _recycle(keys, n)
        return [x[k] for k in recycled_keys]
    if isinstance(x, (str, bytes)) or not isinstance(x, Sequence):
        return [x] * n
    if length >= n:
        return list(x[:n])
    reps = (n + length - 1) // length
    expanded = list(x) * reps
    return expanded[:n]


def _simplify(results: list[Any], *, use_names: bool, names_from: Any) -> Any:
    if not results:
        return results
    if not all(_r_length(r) == 1 for r in results):
        return results
    flat = [r[0] if _r_length(r) == 1 and isinstance(r, (list, tuple)) else r for r in results]
    if all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in flat):
        out: list[float] = [float(v) for v in flat]
        if use_names:
            names = _names_from_arg(names_from, len(out))
            if names is not None:
                return _NamedVector(out, names)
        return out
    if all(isinstance(v, str) for v in flat):
        if use_names:
            names = _names_from_arg(names_from, len(flat))
            if names is not None:
                return _NamedVector(flat, names)
        return flat
    return results


class _NamedVector(list):
    __slots__ = ("names",)

    def __init__(self, values: Sequence[Any], names: Sequence[str]) -> None:
        super().__init__(values)
        self.names = list(names)


def _names_from_arg(arg: Any, n: int) -> list[str] | None:
    if isinstance(arg, Mapping):
        keys = list(arg.keys())
        if len(keys) == n:
            return [str(k) for k in keys]
        return None
    names = getattr(arg, "names", None)
    if names is not None and len(names) == n:
        return [str(x) for x in names]
    return None


def mapply(
    FUN: Callable[..., Any],
    *args: Any,
    MoreArgs: Mapping[str, Any] | None = None,
    SIMPLIFY: bool = True,
    USE_NAMES: bool = True,
) -> Any:
    """Vectorize FUN over recycled arguments like base::mapply."""
    n = max((_r_length(a) for a in args), default=0)
    if n == 0:
        return []
    recycled = [_recycle(a, n) for a in args]
    more = dict(MoreArgs or {})
    results: list[Any] = []
    for i in range(n):
        call_args = [row[i] for row in recycled]
        results.append(FUN(*call_args, **more))
    if not SIMPLIFY:
        return results
    return _simplify(results, use_names=USE_NAMES, names_from=args[0] if args else None)


def pb_mapply(
    FUN: Callable[..., Any],
    dots: Sequence[Any],
    MoreArgs: Mapping[str, Any] | None = None,
) -> Any:
    """Internal pb.mapply: mapply with a progress bar on each FUN call."""
    dots_list = list(dots)
    max_len = max((_r_length(d) for d in dots_list), default=0)
    pb = startpb(0, max_len)
    value = 0

    def traced(*a: Any, **kw: Any) -> Any:
        nonlocal value
        value += 1
        setpb(pb, value)
        return FUN(*a, **kw)

    try:
        return mapply(traced, *dots_list, MoreArgs=MoreArgs, SIMPLIFY=True, USE_NAMES=True)
    finally:
        closepb(pb)
