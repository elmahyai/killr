"""first and last. An xts object stops because xts is not installed."""

from __future__ import annotations

from datatable._util import DataTableError, as_sequence, is_xts

_MISSING = object()


def _head(values, n: int):
    if n >= 0:
        return list(values[:n])
    drop = min(len(values), -n)
    return list(values[: len(values) - drop])


def _tail(values, n: int):
    if n >= 0:
        if n == 0:
            return []
        return list(values[-n:])
    drop = min(len(values), -n)
    return list(values[drop:])


def _xts_stop(which: str):
    raise DataTableError(
        f"'xts' class passed to data.table::{which} function but 'xts' is not available, "
        "you should have 'xts' installed already"
    )


def first(x, n=_MISSING, *args, **kwargs):
    """First element, or utils::head when n is supplied. xts is not available."""
    if is_xts(x):
        _xts_stop("first")
    extra = n is not _MISSING or bool(args) or bool(kwargs)
    if not extra:
        values = as_sequence(x)
        if getattr(values, "ndim", 1) > 1:
            return values[:1]
        if len(values) == 0:
            return values
        return values[0]
    count = 1 if n is _MISSING else int(n)
    values = as_sequence(x)
    if getattr(values, "ndim", 1) > 1:
        return values[:count]
    return _head(values, count)


def last(x, n=_MISSING, *args, **kwargs):
    """Last element, or utils::tail when n is supplied. xts is not available."""
    if is_xts(x):
        _xts_stop("last")
    extra = n is not _MISSING or bool(args) or bool(kwargs)
    if not extra:
        values = as_sequence(x)
        if getattr(values, "ndim", 1) > 1:
            return values[-1:]
        if len(values) == 0:
            return values
        return values[-1]
    count = 1 if n is _MISSING else int(n)
    values = as_sequence(x)
    if getattr(values, "ndim", 1) > 1:
        return values[-count:]
    return _tail(values, count)
