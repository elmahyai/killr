"""Progress-bar tapply."""

from __future__ import annotations

import math
from collections.abc import Callable, Sequence
from typing import Any

from pbapply.mapply import _r_length
from pbapply.pblapply import pblapply


class _Factor:
    __slots__ = ("codes", "levels")

    def __init__(self, codes: list[int], levels: list[str]) -> None:
        self.codes = codes
        self.levels = levels


class _Array:
    """Column-major array with dimnames for proof flattening."""

    __slots__ = ("data", "dim", "dimnames")

    def __init__(self, data: list[Any], dim: list[int], dimnames: list[list[str]]) -> None:
        self.data = data
        self.dim = dim
        self.dimnames = dimnames


def _as_factor(x: Sequence[Any]) -> _Factor:
    if isinstance(x, _Factor):
        return x
    values = list(x)
    levels = sorted({str(v) for v in values})
    level_index = {level: i + 1 for i, level in enumerate(levels)}
    codes = [level_index[str(v)] for v in values]
    return _Factor(codes, levels)


def _match_fun(FUN: Any) -> Callable[..., Any] | None:
    if FUN is None:
        return None
    if isinstance(FUN, str):
        import builtins

        found = getattr(builtins, FUN, None)
        if found is None or not callable(found):
            raise ValueError(f"could not find function {FUN!r}")
        return found
    if not callable(FUN):
        raise TypeError("FUN must be callable")
    return FUN


def pbtapply(
    X: Sequence[Any],
    INDEX: Any,
    FUN: Callable[..., Any] | None = None,
    *args: Any,
    default: Any = float("nan"),
    simplify: bool = True,
    cl: Any = None,
    **kwargs: Any,
) -> Any:
    """Apply FUN to ragged array X grouped by INDEX, with pblapply over groups."""
    FUN = _match_fun(FUN) if FUN is not None else None
    if not isinstance(INDEX, list):
        INDEX = [INDEX]
    index_list = [_as_factor(idx) for idx in INDEX]
    n_i = len(index_list)
    if n_i == 0:
        raise ValueError("'INDEX' is of length zero")
    x_len = len(X)
    if any(len(idx.codes) != x_len for idx in index_list):
        raise ValueError("arguments must have same length")

    namelist = [idx.levels for idx in index_list]
    extent = [len(levels) for levels in namelist]
    cumextent: list[int] = []
    running = 1
    for ext in extent:
        running *= ext
        cumextent.append(running)
    if cumextent[-1] > 2**31 - 1:
        raise ValueError("total number of levels >= 2^31")

    ngroup = cumextent[-1]
    group = list(index_list[0].codes)
    for i in range(1, n_i):
        factor = index_list[i]
        step = cumextent[i - 1]
        for j in range(x_len):
            group[j] = group[j] + step * (factor.codes[j] - 1)

    if FUN is None:
        return group

    buckets: list[list[Any]] = [[] for _ in range(ngroup)]
    for pos, g in enumerate(group):
        buckets[g - 1].append(X[pos])

    index_mask = [len(bucket) > 0 for bucket in buckets]
    to_apply = [bucket for bucket, keep in zip(buckets, index_mask, strict=True) if keep]
    applied = pblapply(to_apply, FUN, *args, cl=cl, **kwargs)

    simplify_ok = bool(
        simplify
        and applied
        and all(_r_length(item) == 1 for item in applied)
    )
    if simplify_ok:
        unlisted = [
            item[0] if isinstance(item, (list, tuple)) else item for item in applied
        ]
        if unlisted and all(
            isinstance(v, (int, float)) and not isinstance(v, bool) for v in unlisted
        ):
            if default is None or (
                isinstance(default, float) and math.isnan(default)
            ):
                fill: Any = 0.0
            else:
                fill = default
        else:
            fill = default
    else:
        fill = default

    ansmat = [fill] * ngroup
    ai = 0
    for gi, keep in enumerate(index_mask):
        if keep:
            val = applied[ai]
            if simplify_ok and _r_length(val) == 1 and isinstance(val, (list, tuple)):
                val = val[0]
            ansmat[gi] = val
            ai += 1

    return _Array(ansmat, extent, namelist)
