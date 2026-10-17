"""Lags, periods, joins, and uniqueness for an xts series."""

from __future__ import annotations

from xts.clock import endpoints
from xts.ordered import XtsError, isOrdered
from xts.series import Xts, dot_xts

_PERIODS = {
    "seconds": "seconds",
    "secs": "seconds",
    "minutes": "minutes",
    "mins": "minutes",
    "hours": "hours",
    "days": "days",
    "weeks": "weeks",
    "months": "months",
    "quarters": "quarters",
    "years": "years",
}


def _one_column(x: Xts) -> list:
    if x.ncol > 1:
        raise XtsError("single column data only")
    return list(x.columns[0])


def _at_endpoints(x: Xts, index, reduce):
    if x.ncol > 1:
        raise XtsError("single column data only")
    rows = x.nrow
    ep = [int(value) for value in index]
    if not ep or min(ep) < 0 or max(ep) > rows:
        raise XtsError("INDEX must be >= 0 and <= nrow(x)")
    if ep[0] != 0:
        ep = [0, *ep]
    if ep[-1] != rows:
        ep = [*ep, rows]
    values = x.columns[0]
    reduced = []
    stamps = []
    for start, stop in zip(ep[:-1], ep[1:]):
        reduced.append(reduce(values[start:stop]))
        stamps.append(x.index[stop - 1])
    return dot_xts(reduced, stamps, tzone=x.tzone, tclass=x.tclass, check=False)


def period_sum(x, index):
    return _at_endpoints(x, index, lambda values: sum(item for item in values if item is not None))


def period_prod(x, index):
    def prod(values):
        total = 1.0
        for item in values:
            if item is not None:
                total *= item
        return total

    return _at_endpoints(x, index, prod)


def period_min(x, index):
    return _at_endpoints(x, index, lambda values: min(item for item in values if item is not None))


def period_max(x, index):
    return _at_endpoints(x, index, lambda values: max(item for item in values if item is not None))


def period_apply(x, index, fun):
    """Apply ``fun`` to each window. ``index`` is an endpoints vector."""

    def reduce(values):
        return fun(values)

    return _at_endpoints(x, index, reduce)


def _apply_on(x, on: str, fun, k: int = 1):
    return period_apply(x, endpoints(x, on, k), fun)


def apply_daily(x, fun):
    return _apply_on(x, "days", fun)


def apply_weekly(x, fun):
    return _apply_on(x, "weeks", fun)


def apply_monthly(x, fun):
    return _apply_on(x, "months", fun)


def apply_quarterly(x, fun):
    return _apply_on(x, "quarters", fun)


def apply_yearly(x, fun):
    return _apply_on(x, "years", fun)


def lag_xts(x: Xts, k: int = 1, na_pad: bool = True):
    """Shift values by ``k`` observations. Positive ``k`` lags, and the index stays."""
    if isinstance(k, (list, tuple)) and len(k) > 1:
        lagged = [lag_xts(x, int(item), na_pad) for item in k]
        return merge_xts(*lagged)
    k = int(k)
    columns = []
    for column in x.columns:
        if k == 0:
            columns.append(list(column))
            continue
        if k > 0:
            pad = [None] * k
            shifted = pad + list(column[:-k] if k < len(column) else [])
            if not na_pad:
                shifted = list(column[k:]) if False else shifted
            columns.append(shifted[: len(column)] if na_pad else shifted)
        else:
            step = -k
            shifted = list(column[step:]) + [None] * step
            columns.append(shifted[: len(column)])
    if not na_pad and k > 0:
        columns = [column[k:] for column in x.columns]
        return dot_xts(columns, x.index[k:], tzone=x.tzone, tclass=x.tclass, colnames=x.colnames, check=False)
    return dot_xts(columns, x.index, tzone=x.tzone, tclass=x.tclass, colnames=x.colnames, check=False)


def diff_xts(x: Xts, lag: int = 1, differences: int = 1, na_pad: bool = True):
    """Differences. The first ``lag`` observations are NA."""
    current = x
    for _ in range(differences):
        previous = lag_xts(current, lag, na_pad=True)
        columns = []
        for left, right in zip(current.columns, previous.columns):
            columns.append([None if earlier is None or later is None else later - earlier for later, earlier in zip(left, right)])
        current = dot_xts(columns, current.index, tzone=x.tzone, tclass=x.tclass, check=False)
    if not na_pad:
        return current.take(range(lag * differences, current.nrow))
    return current


def _align(series: list[Xts]):
    stamps = sorted({stamp for item in series for stamp in item.index})
    columns = []
    names = []
    for item in series:
        places = {stamp: row for row, stamp in enumerate(item.index)}
        for column, name in zip(item.columns, item.colnames or [None] * item.ncol):
            columns.append([column[places[stamp]] if stamp in places else None for stamp in stamps])
            names.append(name)
    return stamps, columns, names


def merge_xts(*series, join="outer"):
    """Union of indexes. A series contributes NA where it has no observation."""
    del join
    items = [item for item in series if item is not None]
    if len(items) == 1:
        return items[0].copy()
    stamps, columns, names = _align(items)
    colnames = names if any(name is not None for name in names) else None
    return dot_xts(columns, stamps, tzone=items[0].tzone, tclass=items[0].tclass, colnames=colnames, check=False)


def cbind_xts(*series):
    return merge_xts(*series)


def _stack(series: list[Xts]) -> Xts:
    rows = []
    order = 0
    for item in series:
        for row in range(item.nrow):
            rows.append((item.index[row], order, [column[row] for column in item.columns]))
            order += 1
    rows.sort(key=lambda item: (item[0], item[1]))
    if not rows:
        return series[0].copy()
    width = max(len(item[2]) for item in rows)
    columns = [[row[2][col] if col < len(row[2]) else None for row in rows] for col in range(width)]
    return dot_xts(columns, [row[0] for row in rows], tzone=series[0].tzone, tclass=series[0].tclass, check=False)


def rbind_xts(*series):
    return _stack(list(series))


def c_xts(*series):
    return _stack(list(series))


def _ohlc(x: Xts, on: str, k: int = 1) -> Xts:
    ep = endpoints(x, on, k)
    opens, highs, lows, closes, stamps = [], [], [], [], []
    for start, stop in zip(ep[:-1], ep[1:]):
        window = x.columns[0][start:stop]
        opens.append(window[0])
        highs.append(max(window))
        lows.append(min(window))
        closes.append(window[-1])
        stamps.append(x.index[stop - 1])
    return dot_xts([opens, highs, lows, closes], stamps, tzone=x.tzone, tclass=x.tclass, colnames=["Open", "High", "Low", "Close"], check=False)


def to_period(x, period="months", k: int = 1, index_at=None, name=None, OHLC=True):
    del index_at, name
    if not OHLC:
        return _apply_on(x, _on(period), lambda values: values[-1], k)
    return _ohlc(x, _on(period), k)


def _on(period: str) -> str:
    aliases = {
        "seconds": "seconds",
        "secs": "seconds",
        "minutes": "minutes",
        "mins": "minutes",
        "hours": "hours",
        "days": "days",
        "weeks": "weeks",
        "months": "months",
        "quarters": "quarters",
        "years": "years",
    }
    if period not in aliases:
        raise XtsError(f"'{period}' is not a period")
    return aliases[period]


def to_minutes(x, k: int = 1):
    return _ohlc(x, "minutes", k)


def to_minutes3(x):
    return to_minutes(x, 3)


def to_minutes5(x):
    return to_minutes(x, 5)


def to_minutes10(x):
    return to_minutes(x, 10)


def to_minutes15(x):
    return to_minutes(x, 15)


def to_minutes30(x):
    return to_minutes(x, 30)


def to_hourly(x, k: int = 1):
    return _ohlc(x, "hours", k)


def _drop_time(x: Xts) -> Xts:
    """Remove the clock time. A POSIXct index becomes a Date at UTC midnight."""
    from datetime import datetime, timezone

    out = x.copy()
    if any(name in {"POSIXt", "POSIXct", "POSIXlt"} for name in out.tclass):
        days = []
        for stamp in out.index:
            if out.tzone in {"UTC", "GMT"}:
                moment = datetime.fromtimestamp(stamp, timezone.utc)
            else:
                moment = datetime.fromtimestamp(stamp)
            days.append(datetime(moment.year, moment.month, moment.day, tzinfo=timezone.utc).timestamp())
        out.index = days
        out.tclass = ["Date"]
        out.tzone = "UTC"
    return out


def _start_of(x: Xts, step: int) -> Xts:
    """Move each endpoint to the first instant of its month or quarter, in UTC."""
    from datetime import datetime, timezone

    from xts.clock import firstof

    out = x.copy()
    stamps = []
    for stamp in out.index:
        moment = datetime.fromtimestamp(stamp, timezone.utc)
        month = ((moment.month - 1) // step) * step + 1
        stamps.append(float(firstof(moment.year, month, 1, tz="UTC")))
    out.index = stamps
    out.tclass = ["yearmon" if step == 1 else "yearqtr"]
    out.tzone = "UTC"
    return out


def to_daily(x, k: int = 1, drop_time: bool = True):
    out = _ohlc(x, "days", k)
    return _drop_time(out) if drop_time else out


def to_weekly(x, k: int = 1, drop_time: bool = True):
    out = _ohlc(x, "weeks", k)
    return _drop_time(out) if drop_time else out


def to_monthly(x, k: int = 1, drop_time: bool = True):
    del drop_time
    return _start_of(_ohlc(x, "months", k), 1)


def to_quarterly(x, k: int = 1, drop_time: bool = True):
    del drop_time
    return _start_of(_ohlc(x, "quarters", k), 3)


def to_yearly(x, k: int = 1, drop_time: bool = True):
    out = _ohlc(x, "years", k)
    return _drop_time(out) if drop_time else out


def periodicity(x: Xts) -> dict:
    """The median spacing of the index, named as a scale."""
    count = x.nrow
    if count < 2:
        return {"difftime": 0, "frequency": 0, "units": "secs", "scale": "seconds", "label": "second"}
    gaps = sorted(right - left for left, right in zip(x.index[:-1], x.index[1:]))
    mid = gaps[len(gaps) // 2] if len(gaps) % 2 else (gaps[len(gaps) // 2 - 1] + gaps[len(gaps) // 2]) / 2
    # R median of an even count averages the two middle values. For an odd count it is the middle.
    period = mid
    if period < 60:
        units, scale, label = "secs", "seconds", "second"
    elif period < 3600:
        units, scale, label = "mins", "minute", "minute"
        period = period / 60
    elif period < 86400:
        units, scale, label = "hours", "hourly", "hour"
    elif period == 86400:
        units, scale, label = "days", "daily", "day"
    elif period <= 604800:
        units, scale, label = "days", "weekly", "week"
    elif period <= 2678400:
        units, scale, label = "days", "monthly", "month"
    elif period <= 7948800:
        units, scale, label = "days", "quarterly", "quarter"
    else:
        units, scale, label = "days", "yearly", "year"
    return {"difftime": period, "frequency": period, "units": units, "scale": scale, "label": label}


def make_index_unique(x: Xts, eps: float = 1e-6) -> Xts:
    """Separate duplicate timestamps by ``eps`` seconds."""
    out = x.copy()
    if not out.index:
        return out
    stamps = list(out.index)
    for row in range(1, len(stamps)):
        if stamps[row] <= stamps[row - 1]:
            stamps[row] = stamps[row - 1] + float(eps)
    out.index = stamps
    return out


def make_time_unique(x: Xts, eps: float = 1e-6) -> Xts:
    return make_index_unique(x, eps)


def is_time_unique(x: Xts) -> bool:
    return bool(isOrdered(x.index, increasing=True, strictly=True)) if x.index else True


def is_index_unique(x: Xts) -> bool:
    return is_time_unique(x)


def shift_time(x: Xts, n: float = 60) -> Xts:
    """Add ``n`` seconds to every index value."""
    out = x.copy()
    out.index = [value + float(n) for value in out.index]
    return out


def adj_time(x, **parts):
    """Adjust POSIXlt fields. xts 0.14.3 then builds a broken POSIXlt."""
    if not parts:
        return x
    raise XtsError("a valid \"POSIXlt\" object has element 5 with name 'month' which should be 'mon'")


def split_xts(x: Xts, f: str = "months") -> list[Xts]:
    ep = endpoints(x, f)
    return [x.take(range(start, stop)) for start, stop in zip(ep[:-1], ep[1:])]


def ax_ticks_by_time(x: Xts, ticks_on: str = "auto", k: int = 1, labels: bool = True, ends: bool = True, gt: int = 2, lt: int = 30):
    """Tick locations, 1-based, along an xts index."""
    del labels
    options = ["years", "quarters", "months", "weeks", "days", "hours", "minutes", "seconds"]
    if ticks_on in {"secs", "mins"}:
        ticks_on = ticks_on[:3]
    if ticks_on == "auto":
        steps = [10, 5, 2, 1, 3, 6, 1, 1, 1, 4, 2, 1, 30, 15, 1, 1]
        units = []
        for name, count in zip(options, [4, 1, 2, 1, 1, 3, 3, 1]):
            units.extend([name] * count)
        counts = []
        chosen = None
        chosen_k = None
        for name, step in zip(units, steps):
            count = len(endpoints(x, name, int(step))) - 1
            counts.append(count)
            if count > lt:
                break
        for loc in range(len(counts) - 1, -1, -1):
            if gt < counts[loc] < lt:
                chosen = units[loc]
                chosen_k = int(steps[loc])
                break
        if chosen is None:
            ep = [0, x.nrow]
        else:
            ep = endpoints(x, chosen, chosen_k)
    else:
        if ticks_on not in options and ticks_on not in {"sec", "min"}:
            raise XtsError(f"'{ticks_on}' is not a valid tick")
        ep = endpoints(x, ticks_on if ticks_on not in {"sec", "min"} else {"sec": "seconds", "min": "minutes"}[ticks_on], k)
    if ends:
        ep = [value + 1 for value in ep[:-1]] + [ep[-1]]
    return ep


def first_last_xts(x: Xts, n, keep: bool, from_end: bool) -> Xts:
    """``first.xts`` / ``last.xts``. A character ``n`` counts periods."""
    del keep
    if x.nrow == 0:
        return x.copy()
    if isinstance(n, str):
        parts = n.split(" ")
        if len(parts) not in (1, 2):
            raise XtsError("incorrectly specified ‘n’")
        count = float(parts[0]) if len(parts) == 2 else 1.0
        unit = parts[-1]
        if not unit.endswith("s"):
            unit = unit + "s"
        scale = periodicity(x)
        if unit == scale["units"]:
            n = int(count)
        else:
            if unit not in _PERIODS:
                raise XtsError("n must be numeric or use seconds,secs,minutes,mins,hours,days,weeks,months,quarters,years")
            ep = endpoints(x, _PERIODS[unit])
            count = int(count)
            if count > len(ep) - 1:
                count = len(ep) - 1
            if from_end:
                start = ep[-count] if count else x.nrow
                return x.take(range(start, x.nrow))
            stop = ep[count]
            return x.take(range(stop))
    n = int(n)
    if from_end:
        if n > 0:
            return x.take(range(max(x.nrow - n, 0), x.nrow))
        if n < 0:
            return x.take(range(max(x.nrow + n, 0)))
        return x.take([])
    if n > 0:
        return x.take(range(min(n, x.nrow)))
    if n < 0:
        return x.take(range(x.nrow - max(x.nrow + n, 0), x.nrow))
    return x.take([])
