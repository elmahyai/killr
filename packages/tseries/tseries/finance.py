"""Drawdown, Sharpe, sterling, and the OHLC and sequence plots."""

from __future__ import annotations

import json
import math
import sys
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone

import numpy as np

from tseries._num import match_arg

YAHOO_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
_QUOTE_COLUMNS = ("Open", "High", "Low", "Close", "Volume", "Adjusted")
_INTERVALS = {"daily": "1d", "weekly": "1wk", "monthly": "1mo"}


def _pmatch(values, table):
    """R's pmatch(): an exact match, else one unique partial match. None when absent."""
    found = []
    for value in values:
        if value in table:
            found.append(table.index(value))
            continue
        hits = [i for i, entry in enumerate(table) if value and entry.startswith(value)]
        found.append(hits[0] if len(hits) == 1 else None)
    return found


def _as_date(value):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()


def _yahoo_history(symbol, start, end, interval):
    """Daily bars from the Yahoo chart endpoint. Returns (dates, {column: values})."""
    period1 = int(datetime(start.year, start.month, start.day, tzinfo=timezone.utc).timestamp())
    stop = end + timedelta(days=1)
    period2 = int(datetime(stop.year, stop.month, stop.day, tzinfo=timezone.utc).timestamp())
    query = urllib.parse.urlencode({
        "period1": period1,
        "period2": period2,
        "interval": interval,
        "events": "history",
        "includeAdjustedClose": "true",
    })
    url = YAHOO_CHART_URL.format(symbol=urllib.parse.quote(symbol, safe="")) + "?" + query
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8"))
    chart = payload.get("chart") or {}
    if chart.get("error"):
        raise RuntimeError(f"Yahoo chart error: {chart['error']}")
    result = chart["result"][0]
    offset = int(result.get("meta", {}).get("gmtoffset", 0))
    indicators = result["indicators"]
    quote = indicators["quote"][0]
    adjclose = (indicators.get("adjclose") or [{}])[0].get("adjclose")
    timestamps = result.get("timestamp") or []
    dates, columns = [], {name: [] for name in _QUOTE_COLUMNS}
    for i, stamp in enumerate(timestamps):
        day = datetime.fromtimestamp(stamp + offset, tz=timezone.utc).date()
        if day < start or day > end:
            continue
        dates.append(day)
        for name, key in (("Open", "open"), ("High", "high"), ("Low", "low"), ("Close", "close"), ("Volume", "volume")):
            value = (quote.get(key) or [None] * len(timestamps))[i]
            columns[name].append(math.nan if value is None else float(value))
        value = adjclose[i] if adjclose else None
        columns["Adjusted"].append(math.nan if value is None else float(value))
    return dates, columns


def get_hist_quote(
    instrument="^gdax",
    start=None,
    end=None,
    quote=("Open", "High", "Low", "Close"),
    provider="yahoo",
    method=None,
    origin="1899-12-30",
    compression="d",
    retclass="zoo",
    quiet=False,
    drop=False,
):
    """Historical prices of one instrument. Downloads through the Yahoo chart endpoint.

    The R function calls quantmod::getSymbols. This port fetches the same quotes with urllib
    and applies the tseries steps: the quote-name matching, the duplicate-date removal, the
    start and end messages, and the zoo or ts result.
    """
    if start is None:
        start = "1991-01-02"
    if end is None:
        end = date.today() - timedelta(days=1)
    provider = match_arg(provider, ("yahoo",))
    retclass = match_arg(retclass, ("zoo", "ts"))
    periodicity = match_arg(compression, ("daily", "weekly", "monthly"))

    quote = list(quote)
    for i, name in enumerate(quote):
        if name and "AdjClose".startswith(name):
            quote[i] = "Adjusted"

    start = _as_date(start)
    end = _as_date(end)
    dates, columns = _yahoo_history(instrument, start, end, _INTERVALS[periodicity])
    if not dates:
        raise ValueError("no quotes returned")

    nser = _pmatch(quote, list(_QUOTE_COLUMNS))
    if any(index is None for index in nser):
        raise ValueError("this quote is not available")

    keep, seen = [], set()
    for i, day in enumerate(dates):
        if day not in seen:
            seen.add(day)
            keep.append(i)
    dates = [dates[i] for i in keep]
    matrix = np.column_stack([np.asarray([columns[_QUOTE_COLUMNS[j]][i] for i in keep], dtype=float) for j in nser])
    if drop and matrix.shape[1] == 1:
        matrix = matrix[:, 0]
    names = [_QUOTE_COLUMNS[j] for j in nser]
    n = len(dates)

    if not quiet and dates[0] != start:
        sys.stdout.write(f"time series starts {dates[0]:%Y-%m-%d}\n")
    if not quiet and dates[n - 1] != end:
        sys.stdout.write(f"time series ends   {dates[n - 1]:%Y-%m-%d}\n")

    if retclass == "ts":
        origin_date = _as_date(origin)
        julian = np.asarray([(day - origin_date).days for day in dates], dtype=float)
        ind = (julian - julian[0]).astype(int)
        values = np.full((int(ind.max()) + 1, len(nser)), math.nan)
        values[ind, :] = matrix.reshape(n, len(nser))
        if drop and len(nser) == 1:
            values = values[:, 0]
        return values, float(julian[0]), float(julian[-1]), names

    from zoo.as_date import RDate
    from zoo.as_zoo import zoo_create

    days = RDate([(day - date(1970, 1, 1)).days for day in dates])
    out = zoo_create(matrix, order_by=days)
    out.colnames = names
    return out


def _series(x):
    values = np.asarray(x, dtype=float)
    if values.ndim == 2 and values.shape[1] == 1:
        values = values.reshape(-1)
    if values.ndim != 1:
        raise ValueError("x is not a vector or univariate time series")
    if np.isnan(values).any():
        raise ValueError("NAs in x")
    return values


def maxdrawdown(x):
    values = _series(x)
    running = np.maximum.accumulate(values)
    depth = running - values
    deepest = float(depth.max())
    to = np.flatnonzero(depth == deepest) + 1
    starts = []
    for stop in to:
        zeros = np.flatnonzero(depth[: int(stop)] == 0) + 1
        starts.append(int(zeros.max()))
    return {"maxdrawdown": deepest, "from": starts, "to": [int(item) for item in to]}


def sharpe(x, r=0, scale=None):
    if scale is None:
        scale = math.sqrt(250)
    values = _series(x)
    if len(values) == 1:
        return math.nan
    changes = np.diff(values)
    return float(scale * (changes.mean() - r) / changes.std(ddof=1))


def portfolio_optim(x, pm=None, riskless=False, shorts=False, rf=0.0, reslow=None, reshigh=None, covmat=None):
    """Mean-variance weights. The quadratic program is quadprog.solve_qp."""
    from quadprog.solve import solve_qp

    values = np.asarray(x, dtype=float)
    if values.ndim != 2 or values.shape[1] <= 1:
        raise ValueError("x is not a matrix")
    if np.isnan(values).any():
        raise ValueError("NAs in x")
    k = values.shape[1]
    if pm is None:
        pm = float(values.mean())
    if covmat is None:
        covmat = np.cov(values, rowvar=False)
    covmat = np.asarray(covmat, dtype=float)
    if covmat.shape != (k, k):
        raise ValueError("covmat has not the right dimension")
    big = 1e100
    if reslow is not None and reshigh is None:
        reshigh = np.repeat(big, k)
    if reslow is None and reshigh is not None:
        reslow = -np.repeat(big, k)
    if reslow is not None and len(np.asarray(reslow).reshape(-1)) != k:
        raise ValueError("reslow has not the right dimension")
    if reshigh is not None and len(np.asarray(reshigh).reshape(-1)) != k:
        raise ValueError("reshigh has not the right dimension")
    if riskless:
        a1 = values.mean(axis=0) - rf
        if shorts:
            rows = [a1]
            bounds = [pm - rf]
        else:
            rows = [a1, np.eye(k)]
            bounds = [pm - rf, np.zeros(k)]
        if reslow is not None:
            eye = np.eye(k)
            rows.extend([eye, -eye])
            bounds.extend([np.asarray(reslow, dtype=float), -np.asarray(reshigh, dtype=float)])
        meq = 1
    else:
        a1 = np.ones(k)
        a2 = values.mean(axis=0)
        if shorts:
            rows = [a1, a2]
            bounds = [1.0, pm]
        else:
            rows = [a1, a2, np.eye(k)]
            bounds = [1.0, pm, np.zeros(k)]
        if reslow is not None:
            eye = np.eye(k)
            if shorts:
                rows.extend([eye, -eye])
                bounds.extend([np.asarray(reslow, dtype=float), -np.asarray(reshigh, dtype=float)])
            else:
                rows.extend([eye, -eye])
                bounds.extend([np.asarray(reslow, dtype=float), -np.asarray(reshigh, dtype=float)])
        meq = 2
    amat = np.vstack(rows).T
    bvec = np.concatenate([np.atleast_1d(np.asarray(item, dtype=float)) for item in bounds])
    solved = solve_qp(covmat, np.zeros(k), amat, bvec=bvec, meq=meq)
    weights = np.asarray(solved["solution"], dtype=float)
    returns = values @ weights
    return {
        "pw": weights,
        "px": returns,
        "pm": float(returns.mean()),
        "ps": float(returns.std(ddof=1)),
    }


def sterling(x):
    values = _series(x)
    if len(values) == 1:
        return math.nan
    depth = maxdrawdown(values)["maxdrawdown"]
    return float((values[-1] - values[0]) / depth)


def _ts_time(n, start, frequency):
    return float(start) + np.arange(n, dtype=float) / float(frequency)


def _fmt(value):
    return format(float(value), ".17g")


def plot_ohlc(x, start=1, frequency=1, date="calendar", origin="1899-12-30", fmt="%Y-%m-%d"):
    """Draw an open-high-low-close chart and return the segment coordinates."""
    import matplotlib

    matplotlib.use("Agg", force=False)
    import matplotlib.pyplot as plt

    values = np.asarray(x, dtype=float)
    if values.ndim != 2 or values.shape[1] != 4:
        raise ValueError("x is not a open/high/low/close time series")
    date = match_arg(date, ("calendar", "julian"))
    n = values.shape[0]
    time = _ts_time(n, start, frequency)
    dt = float(np.diff(time).min()) / 3.0
    high = values[:, 1]
    low = values[:, 2]
    open_ = values[:, 0]
    close = values[:, 3]
    figure, axes = plt.subplots()
    axes.vlines(time, low, high)
    axes.hlines(open_, time - dt, time)
    axes.hlines(close, time, time + dt)
    axes.set_xlim(float(time.min()), float(time.max()))
    finite = values[np.isfinite(values)]
    axes.set_ylim(float(finite.min()), float(finite.max()))
    if date == "calendar":
        labels = []
        index = np.round(np.linspace(1, n, 5)).astype(int)
        origin_dt = datetime(1899, 12, 30, tzinfo=timezone.utc)
        if origin != "1899-12-30":
            origin_dt = datetime.strptime(origin, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        for item in index:
            stamp = origin_dt + timedelta(seconds=float(time[item - 1]) * 86400)
            labels.append(stamp.strftime(fmt))
            axes.plot(time[item - 1], close[item - 1], marker="|", color="none")
        axes.set_xticks(time[index - 1])
        axes.set_xticklabels(labels)
    else:
        labels = []
    figure.tight_layout()
    plt.close(figure)
    rows = []
    for i in range(n):
        rows.append(
            ",".join(
                [
                    _fmt(time[i]),
                    _fmt(high[i]),
                    _fmt(low[i]),
                    _fmt(time[i] - dt),
                    _fmt(open_[i]),
                    _fmt(close[i]),
                    _fmt(time[i] + dt),
                ]
            )
        )
    return "|".join(rows) + "#" + ",".join(labels)


def seqplot_ts(x, y, start=1, frequency=1, start_y=None, frequency_y=None):
    """Draw two series on one set of axes and return the axis limits."""
    import matplotlib

    matplotlib.use("Agg", force=False)
    import matplotlib.pyplot as plt

    left = np.asarray(x, dtype=float)
    right = np.asarray(y, dtype=float)
    if start_y is None:
        start_y = start
    if frequency_y is None:
        frequency_y = frequency
    if abs(float(frequency) - float(frequency_y)) > 1e-5:
        raise ValueError("x and y do not have the same frequency")
    if left.ndim == 1:
        left = left.reshape(-1, 1)
    if right.ndim == 1:
        right = right.reshape(-1, 1)
    if left.shape[1] != right.shape[1]:
        raise ValueError("x and y do not have consistent dimensions")
    if left.shape[1] > 10:
        raise ValueError("cannot plot more than 10 series")
    time_x = _ts_time(left.shape[0], start, frequency)
    time_y = _ts_time(right.shape[0], start_y, frequency_y)
    figure, axes = plt.subplots()
    limits = []
    for col in range(left.shape[1]):
        xlim = (float(min(time_x.min(), time_y.min())), float(max(time_x.max(), time_y.max())))
        finite = np.concatenate([left[:, col], right[:, col]])
        finite = finite[np.isfinite(finite)]
        ylim = (float(finite.min()), float(finite.max()))
        axes.plot(time_x, left[:, col], color="black")
        axes.plot(time_y, right[:, col], color="red")
        limits.append(f"{_fmt(xlim[0])},{_fmt(xlim[1])},{_fmt(ylim[0])},{_fmt(ylim[1])}")
    figure.tight_layout()
    plt.close(figure)
    return "|".join(limits)
