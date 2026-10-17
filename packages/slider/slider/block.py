"""Break a vector into period blocks via warp::warp_boundary."""

from __future__ import annotations

from typing import Any

import numpy as np

from slider.errors import SliderError
from warp import Date, POSIXct, POSIXlt, warp_boundary
from warp.time import as_datetime_seconds


def _is_datelike(i) -> bool:
    return isinstance(i, (Date, POSIXct, POSIXlt))


def _index_values(i) -> list:
    if isinstance(i, Date):
        return list(i.days)
    if isinstance(i, (POSIXct, POSIXlt)):
        return list(as_datetime_seconds(i))
    raise SliderError(
        f"`i` must be a Date, POSIXct, or POSIXlt, not {type(i).__name__}."
    )


def _check_index_incompatible_type(i, i_arg: str = "i") -> None:
    if _is_datelike(i):
        return
    raise SliderError(
        f"`{i_arg}` must be a Date, POSIXct, or POSIXlt, not {type(i).__name__}."
    )


def _check_index_cannot_be_na(i, i_arg: str = "i") -> None:
    values = _index_values(i)
    locations = [pos + 1 for pos, value in enumerate(values) if value is None]
    if not locations:
        return
    loc_text = ", ".join(str(loc) for loc in locations)
    raise SliderError(
        f"In locations: {loc_text}\n`{i_arg}` can't be `NA`."
    )


def _check_index_must_be_ascending(i, i_arg: str = "i") -> None:
    values = _index_values(i)
    locations = [
        pos + 1
        for pos in range(len(values) - 1)
        if values[pos + 1] is not None
        and values[pos] is not None
        and values[pos + 1] < values[pos]
    ]
    if not locations:
        return
    loc_text = ", ".join(str(loc) for loc in locations)
    raise SliderError(
        f"In locations: {loc_text}\n`{i_arg}` must be in ascending order."
    )


def _vec_size(x) -> int:
    if isinstance(x, (Date, POSIXct, POSIXlt)):
        return len(x)
    if isinstance(x, np.ndarray):
        if x.ndim != 1:
            raise SliderError("`x` must be a vector.")
        return int(x.shape[0])
    if isinstance(x, (str, bytes)):
        raise SliderError("`x` must be a vector.")
    if isinstance(x, dict):
        sizes = {len(values) for values in x.values()}
        if len(sizes) != 1:
            raise SliderError("Each column of `x` must have the same size.")
        return next(iter(sizes)) if sizes else 0
    if isinstance(x, (list, tuple)):
        return len(x)
    raise SliderError("`x` must be a vector.")


def _vec_assert(x) -> None:
    _vec_size(x)


def _chop_piece(x, start: int, stop: int):
    lo = start - 1
    hi = stop
    if isinstance(x, Date):
        return Date(x.days[lo:hi])
    if isinstance(x, POSIXct):
        return POSIXct(x.seconds[lo:hi], x.tz)
    if isinstance(x, POSIXlt):
        return POSIXlt(
            x.year[lo:hi],
            x.mon[lo:hi],
            x.mday[lo:hi],
            x.hour[lo:hi],
            x.minute[lo:hi],
            x.second[lo:hi],
            yday=x.yday[lo:hi],
            tz=x.tz,
            isdst=x.isdst[lo:hi],
        )
    if isinstance(x, np.ndarray):
        return x[lo:hi]
    if isinstance(x, dict):
        return {name: values[lo:hi] for name, values in x.items()}
    if isinstance(x, (list, tuple)):
        return list(x[lo:hi])
    raise SliderError("`x` must be a vector.")


def _slider_block(x, starts: np.ndarray, stops: np.ndarray) -> list:
    out: list[Any] = []
    for start, stop in zip(starts, stops):
        start_i = int(start)
        stop_i = int(stop)
        if stop_i < start_i:
            out.append(_empty_piece(x))
            continue
        out.append(_chop_piece(x, start_i, stop_i))
    return out


def _empty_piece(x):
    if isinstance(x, Date):
        return Date([])
    if isinstance(x, POSIXct):
        return POSIXct([], x.tz)
    if isinstance(x, POSIXlt):
        return POSIXlt([], [], [], tz=x.tz)
    if isinstance(x, np.ndarray):
        return x[:0]
    if isinstance(x, dict):
        return {name: [] for name in x}
    return []


def block(x, i, period, every=1, origin=None):
    """Break ``x`` into non-overlapping blocks along a datelike index ``i``."""
    _vec_assert(x)

    _check_index_incompatible_type(i, "i")
    _check_index_cannot_be_na(i, "i")
    _check_index_must_be_ascending(i, "i")

    x_size = _vec_size(x)
    i_size = len(_index_values(i))
    if x_size != i_size:
        raise SliderError(f"`i` must have size {x_size}, not {i_size}.")

    boundaries = warp_boundary(i, period, every=every, origin=origin)
    return _slider_block(x, boundaries.start, boundaries.stop)
