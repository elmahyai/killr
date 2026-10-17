"""Regular zoo series.

A supplied frequency freezes deltat as its reciprocal before a near-integer
frequency is rounded. The index keeps that original step, then
floor(frequency * time + .0001) / frequency pulls it back onto the grid.
Frequency 4 or 12 with calendar becomes yearqtr or yearmon.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np

from zoo.series import Zoo

MISSING = object()

_BAD_DATA = "\u201cdata\u201d : attempt to define invalid zoo object"
_MONTHS = (
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
)


class Yearmon(np.ndarray):
    def __array_finalize__(self, obj: Any) -> None:
        return None


class Yearqtr(np.ndarray):
    def __array_finalize__(self, obj: Any) -> None:
        return None


def yearmon(x: Any) -> Yearmon:
    values = np.asarray(x, dtype=np.float64)
    out = np.floor(12.0 * values + 0.0001) / 12.0
    return np.array(out, dtype=np.float64).view(Yearmon)


def yearqtr(x: Any) -> Yearqtr:
    values = np.asarray(x, dtype=np.float64)
    out = np.floor(4.0 * values + 0.001) / 4.0
    return np.array(out, dtype=np.float64).view(Yearqtr)


def as_yearmon(x: Any) -> Yearmon:
    """Integer input keeps its values. Numeric input snaps onto the grid."""
    if isinstance(x, np.ndarray) and np.issubdtype(x.dtype, np.integer):
        return np.array(x, dtype=np.float64).view(Yearmon)
    return yearmon(x)


def as_yearqtr(x: Any) -> Yearqtr:
    if isinstance(x, np.ndarray) and np.issubdtype(x.dtype, np.integer):
        return np.array(x, dtype=np.float64).view(Yearqtr)
    return yearqtr(x)


def format_yearmon(value: Any) -> str:
    number = float(value)
    if math.isnan(number):
        return "NA"
    year = math.floor(number + 0.001)
    month = math.floor(12.0 * (number - year) + 1.5 + 0.001)
    month = min(12, max(1, int(month)))
    return f"{_MONTHS[month - 1]} {int(year)}"


def format_yearqtr(value: Any) -> str:
    number = float(value)
    if math.isnan(number):
        return "NA"
    year = math.floor(number + 0.001)
    quarter = math.floor(4.0 * (number - year) + 1.5 + 0.001)
    quarter = min(4, max(1, int(quarter)))
    return f"{int(year)} Q{int(quarter)}"


def _yearmon_numeric(x: Any) -> np.ndarray:
    if isinstance(x, np.ndarray) and np.issubdtype(x.dtype, np.integer):
        if type(x).__name__ not in {"Yearmon", "Yearqtr", "RDate"}:
            return np.array(x, dtype=np.float64)
    return np.floor(12.0 * np.asarray(x, dtype=np.float64) + 0.0001) / 12.0


def _yearqtr_numeric(x: Any) -> np.ndarray:
    if isinstance(x, np.ndarray) and np.issubdtype(x.dtype, np.integer):
        if type(x).__name__ not in {"Yearmon", "Yearqtr", "RDate"}:
            return np.array(x, dtype=np.float64)
    return np.floor(4.0 * np.asarray(x, dtype=np.float64) + 0.001) / 4.0


def _is_time_class(x: Any) -> str | None:
    name = type(x).__name__
    if name in {"RDate", "Yearmon", "Yearqtr"}:
        return name
    if isinstance(x, np.ndarray) and x.shape == ():
        return None
    return None


def _num_or_int(x: Any) -> bool:
    if x is None or type(x).__name__ in {"RDate", "Yearmon", "Yearqtr"}:
        return False
    import datetime as _dt

    if isinstance(x, _dt.date):
        return False
    if isinstance(x, (bool, np.bool_)):
        return False
    if isinstance(x, (int, float, np.integer, np.floating)):
        return True
    if isinstance(x, np.ndarray) and x.dtype != object:
        if np.issubdtype(x.dtype, np.integer) or np.issubdtype(x.dtype, np.floating):
            return True
    return False


def _as_float_time(x: Any) -> float:
    if isinstance(x, (int, float, np.integer, np.floating)) and not isinstance(x, (bool, np.bool_)):
        return float(x)
    arr = np.asarray(x, dtype=np.float64).reshape(-1)
    if arr.size != 1:
        raise ValueError("time value does not have length 1")
    return float(arr[0])


def _add_index(base: Any, delta: Any) -> Any:
    name = type(base).__name__
    delta = np.asarray(delta, dtype=np.float64)
    if name == "RDate":
        from zoo.as_date import RDate

        return RDate(np.asarray(base, dtype=np.float64).reshape(-1)[0] + delta)
    if name == "Yearmon":
        return yearmon(_yearmon_numeric(base) + _yearmon_numeric(delta))
    if name == "Yearqtr":
        return yearqtr(_yearqtr_numeric(base) + _yearqtr_numeric(delta))
    import datetime as _dt

    if isinstance(base, _dt.datetime):
        raise TypeError("POSIXct indexes are not available in this translation")
    if isinstance(base, _dt.date):
        from zoo.as_date import RDate

        origin = base.toordinal() - 719163
        return RDate(origin + delta)
    return np.asarray(base, dtype=np.float64) + delta


def _length(x: Any) -> int:
    if isinstance(x, (int, float, np.integer, np.floating, bool, np.bool_)):
        return 1
    if isinstance(x, np.ndarray) and x.shape == ():
        return 1
    return int(np.asarray(x).reshape(-1).size)


def _is_r_integer(x: Any) -> bool:
    if isinstance(x, bool) or type(x).__name__ in {"RDate", "Yearmon", "Yearqtr"}:
        return False
    if isinstance(x, np.integer):
        return True
    if isinstance(x, np.ndarray) and np.issubdtype(x.dtype, np.integer):
        return type(x).__name__ not in {"RDate", "Yearmon", "Yearqtr"}
    return False


def _collapse_time(value: Any, frequency: float) -> Any:
    """c(year, period) becomes year + (period - 1) / frequency. Dates stay dates."""
    if type(value).__name__ in {"RDate", "Yearmon", "Yearqtr"}:
        return value
    import datetime as _dt

    if isinstance(value, _dt.date):
        return value
    if isinstance(value, (int, float, np.integer, np.floating)) and not isinstance(value, (bool, np.bool_)):
        return value
    arr = np.asarray(value)
    if arr.dtype == object:
        return value
    flat = np.asarray(arr, dtype=np.float64).reshape(-1)
    if flat.size > 1:
        return float(flat[0] + (flat[1] - 1.0) / frequency)
    if flat.size == 1:
        if isinstance(value, np.ndarray) and np.issubdtype(value.dtype, np.integer):
            return np.array(value.reshape(-1)[:1], dtype=np.int32)
        return float(flat[0])
    return flat


def _resolve_frequency(frequency: Any, deltat: Any, ts_eps: float) -> tuple[float, float]:
    if frequency is MISSING:
        deltat = 1.0 if deltat is MISSING else float(deltat)
        frequency = 1.0 / deltat
    elif deltat is MISSING:
        frequency = float(frequency)
        deltat = 1.0 / frequency
    else:
        frequency = float(frequency)
        deltat = float(deltat)
    if frequency > 1 and abs(frequency - round(frequency)) < ts_eps:
        frequency = float(round(frequency))
    return frequency, deltat


def _acceptable(data: Any) -> bool:
    if isinstance(data, (list, tuple, np.ndarray, str, bytes, dict)):
        return True
    if isinstance(data, (int, float, bool, np.integer, np.floating, np.bool_, np.complexfloating)):
        return True
    name = type(data).__name__
    return name in {"DataFrame", "Ts", "RArray"}


def zooreg(
    data: Any = MISSING,
    start: Any = MISSING,
    end: Any = MISSING,
    frequency: Any = MISSING,
    deltat: Any = MISSING,
    ts_eps: float = 1e-5,
    order_by: Any = None,
    calendar: bool = True,
) -> Zoo:
    """Regular series. order.by selects zoo(); otherwise the index is a grid."""
    from zoo.as_zoo import BAD_X, ingest, zoo_create

    if not (data is MISSING or data is None or _acceptable(data)):
        raise ValueError(_BAD_DATA)

    frequency, deltat = _resolve_frequency(frequency, deltat, float(ts_eps))

    # intgr is decided after missing arguments take their defaults, but
    # missing() itself is unchanged by that evaluation.
    start_for_intgr = 1 if start is MISSING else start
    end_for_intgr = np.array([], dtype=np.float64) if end is MISSING else end
    intgr = (_length(start_for_intgr) < 1 or _is_r_integer(start_for_intgr)) and (
        _length(end_for_intgr) < 1 or _is_r_integer(end_for_intgr)
    )

    if data is MISSING or data is None:
        from zoo.as_zoo import logical_na

        data_arr = logical_na()
    elif type(data).__name__ == "Ts":
        data_arr = ingest(data.data)
    else:
        try:
            data_arr = ingest(data)
        except ValueError as exc:
            if str(exc) == BAD_X:
                raise ValueError(_BAD_DATA) from None
            raise

    # zoo() is called with its own calendar default, not this argument.
    if order_by is not None:
        return zoo_create(data_arr, order_by=order_by, frequency=frequency, calendar=True)

    ndata = int(data_arr.shape[0])
    if end is MISSING:
        ostart = 1 if start is MISSING else _collapse_time(start, frequency)
        oend = None
        start_num = _as_float_time(ostart)
        end_num = start_num + (ndata - 1) / frequency
    elif start is MISSING:
        ostart = None
        oend = _collapse_time(end, frequency)
        end_num = _as_float_time(oend)
        start_num = end_num - (ndata - 1) / frequency
    else:
        ostart = _collapse_time(start, frequency)
        oend = None
        start_num = _as_float_time(ostart)
        end_num = _as_float_time(_collapse_time(end, frequency))

    if not (start_num <= end_num):
        if math.isnan(start_num) or math.isnan(end_num):
            raise ValueError("missing value where TRUE/FALSE needed")
        raise ValueError("start cannot be after end")

    index = start_num + np.arange(ndata, dtype=np.float64) * deltat
    from zoo.as_zoo import r_all_equal

    if r_all_equal(start_num * frequency, round(start_num * frequency), tolerance=ts_eps**2):
        index = np.floor(frequency * index + 0.0001) / frequency

    if ostart is not None and not _num_or_int(ostart):
        index = _add_index(ostart, index - start_num)
    elif oend is not None and not _num_or_int(oend):
        index = _add_index(oend, index - end_num)

    kind_numeric = isinstance(index, np.ndarray) and (
        np.issubdtype(np.asarray(index).dtype, np.floating)
        or np.issubdtype(np.asarray(index).dtype, np.integer)
    )
    kind_numeric = kind_numeric and type(index).__name__ not in {"RDate", "Yearmon", "Yearqtr"}
    if calendar and frequency in (4, 12) and kind_numeric:
        index = as_yearqtr(index) if frequency == 4 else as_yearmon(index)
    elif intgr and type(index).__name__ not in {"RDate", "Yearmon", "Yearqtr"}:
        if r_all_equal(index, np.round(np.asarray(index, dtype=float)), tolerance=ts_eps**2):
            from zoo.as_zoo import as_r_integer

            index = as_r_integer(np.round(np.asarray(index, dtype=float)))

    return Zoo(data_arr, index, frequency=frequency, regular=True)
