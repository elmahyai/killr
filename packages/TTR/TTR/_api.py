"""Technical trading rules. Numeric inputs follow TTR's matrix path."""

from __future__ import annotations

import csv
import math
import tempfile
import warnings
from pathlib import Path

import numpy as np

from TTR import _core as C

NA = C.NA


class Frame:
    """A numeric matrix with column names, in the order TTR's cbind uses."""

    def __init__(self, data, columns: list[str]):
        values = np.asarray(data, dtype=float)
        if values.ndim == 1:
            values = values.reshape(-1, 1)
        self.values = values
        self.columns = list(columns)

    def __getitem__(self, key):
        if isinstance(key, str):
            return self.values[:, self.columns.index(key)]
        if isinstance(key, int):
            return self.values[:, key]
        return self.values[key]

    def __len__(self) -> int:
        return self.values.shape[0]

    def __str__(self) -> str:
        if not len(self):
            return ""
        last = self.values[-1]
        parts = [f"{name}={_show(value)}" for name, value in zip(self.columns, last)]
        return " ".join(parts)


def _show(value) -> str:
    if value is None or (isinstance(value, float) and not math.isfinite(value)):
        return "NA"
    if isinstance(value, float) and value == int(value) and abs(value) < 1e15:
        return str(int(value))
    return f"{float(value):.6g}"


def _check_n(n: int, count: int) -> int:
    n = int(n)
    if n < 1 or n > count:
        raise C.TTRError(f"n = {n} is outside valid range: [1, {count}]")
    return n


def _uni(x, label: str = "x") -> np.ndarray:
    values = C.as_float(x)
    if values.ndim == 2 and values.shape[1] > 1:
        raise C.TTRError(f"ncol({label}) > 1. this series only supports univariate '{label}'")
    return values.reshape(-1)


def match_arg(arg, choices: list[str], several: bool = False):
    options = list(choices)
    items = list(arg) if isinstance(arg, (list, tuple)) else [arg]
    if several and items == options:
        return options
    if not several and items == options:
        return options[0]
    if not several:
        items = items[:1]
    found = []
    for item in items:
        name = str(item)
        exact = [choice for choice in options if choice == name]
        if exact:
            found.append(exact[0])
            continue
        prefix = [choice for choice in options if choice.startswith(name)]
        if len(prefix) != 1:
            raise C.TTRError(f"{name!r} does not match one of {options}")
        found.append(prefix[0])
    return found if several else found[0]


def r_ifelse(test, yes, no) -> np.ndarray:
    test = np.asarray(test, dtype=float)
    yes = np.asarray(yes, dtype=float)
    no = np.asarray(no, dtype=float)
    test, yes, no = np.broadcast_arrays(test, yes, no)
    out = np.where(test == 1.0, yes, no).astype(float)
    out[np.isnan(test)] = NA
    return out


def _mask(left, right, op) -> np.ndarray:
    left = np.asarray(left, dtype=float)
    right = np.asarray(right, dtype=float)
    left, right = np.broadcast_arrays(left, right)
    out = np.full(left.shape, NA)
    ok = np.isfinite(left) & np.isfinite(right)
    out[ok] = op(left[ok], right[ok]).astype(float)
    return out


def r_eq(left, right) -> np.ndarray:
    return _mask(left, right, np.equal)


def r_lt(left, right) -> np.ndarray:
    return _mask(left, right, np.less)


def r_gt(left, right) -> np.ndarray:
    return _mask(left, right, np.greater)


def r_or(left, right) -> np.ndarray:
    left = np.asarray(left, dtype=float)
    right = np.asarray(right, dtype=float)
    left, right = np.broadcast_arrays(left, right)
    out = np.full(left.shape, NA)
    out[(left == 1.0) | (right == 1.0)] = 1.0
    out[(left == 0.0) & (right == 0.0)] = 0.0
    return out


def r_and(left, right) -> np.ndarray:
    left = np.asarray(left, dtype=float)
    right = np.asarray(right, dtype=float)
    left, right = np.broadcast_arrays(left, right)
    out = np.full(left.shape, NA)
    out[(left == 1.0) & (right == 1.0)] = 1.0
    out[(left == 0.0) | (right == 0.0)] = 0.0
    return out


def pmax(left, right) -> np.ndarray:
    return np.maximum(np.asarray(left, dtype=float), np.asarray(right, dtype=float))


def pmin(left, right) -> np.ndarray:
    return np.minimum(np.asarray(left, dtype=float), np.asarray(right, dtype=float))


def lead(x, k) -> np.ndarray:
    """lag.xts(x, -k): the value k places ahead, with NA at the end."""
    values = C.column(x)
    shift = int(k)
    out = np.full(len(values), NA)
    if shift >= 0:
        if shift < len(values):
            out[: len(values) - shift] = values[shift:]
    else:
        back = -shift
        out[back:] = values[: len(values) - back]
    return out


def na_approx(x) -> np.ndarray:
    values = C.column(x).copy()
    known = np.flatnonzero(np.isfinite(values))
    if len(known) < 2:
        return values
    span = np.arange(known[0], known[-1] + 1)
    values[span] = np.interp(span, known, values[known])
    return values


def naCheck(x, n: int = 0) -> dict:
    values = C.as_float(x)
    if values.ndim == 1 or values.shape[1] == 1:
        flat = values.reshape(-1)
        missing = int(np.sum(~np.isfinite(flat)))
        if missing and not np.isfinite(flat[missing:]).all():
            raise C.TTRError("Series contains non-leading NAs")
    else:
        rows = np.any(~np.isfinite(values), axis=1)
        missing = int(np.sum(rows))
        if missing and np.any(~np.isfinite(values[missing:])):
            raise C.TTRError("Series contains non-leading NAs")
    return {"NAs": missing, "nonNA": slice(missing, None), "beg": n + missing}


def _call_ma(ma_type, series, n=None, extra=None):
    extra = dict(extra or {})
    if isinstance(ma_type, (list, tuple)) and ma_type and isinstance(ma_type[0], (list, tuple)):
        raise C.TTRError("pass one moving average, or a list of (name, kwargs) pairs")
    if isinstance(ma_type, (list, tuple)):
        name = ma_type[0]
        kwargs = dict(ma_type[1] if len(ma_type) > 1 else {})
        if n is not None and "n" not in kwargs:
            kwargs["n"] = n
        kwargs.update(extra)
        return _MA[match_arg(name, list(_MA))](series, **kwargs)
    name = "SMA" if ma_type is None else ma_type
    kwargs = dict(extra)
    if n is not None:
        kwargs["n"] = n
    return _MA[match_arg(str(name), list(_MA))](series, **kwargs)


def runSum(x, n: int = 10, cumulative: bool = False) -> np.ndarray:
    values = _uni(x, "x")
    n = _check_n(n, len(values))
    if cumulative:
        missing = int(np.sum(~np.isfinite(values)))
        if missing:
            if not np.isfinite(values[missing:]).all():
                raise C.TTRError("Series contains non-leading NAs")
            if missing + n > len(values):
                raise C.TTRError("not enough non-NA values")
        result = np.full(len(values), NA)
        result[missing:] = np.cumsum(values[missing:])
        result[: n - 1 + missing] = NA
        return result
    return C.run_sum(values, n)


def runMin(x, n: int = 10, cumulative: bool = False) -> np.ndarray:
    values = _uni(x, "x")
    n = _check_n(n, len(values))
    if cumulative:
        missing = int(np.sum(~np.isfinite(values)))
        if missing:
            if not np.isfinite(values[missing:]).all():
                raise C.TTRError("Series contains non-leading NAs")
            if missing + n > len(values):
                raise C.TTRError("not enough non-NA values")
        result = np.full(len(values), NA)
        result[missing:] = np.minimum.accumulate(values[missing:])
        result[: n - 1 + missing] = NA
        return result
    return C.run_min(values, n)


def runMax(x, n: int = 10, cumulative: bool = False) -> np.ndarray:
    values = _uni(x, "x")
    n = _check_n(n, len(values))
    if cumulative:
        missing = int(np.sum(~np.isfinite(values)))
        if missing:
            if not np.isfinite(values[missing:]).all():
                raise C.TTRError("Series contains non-leading NAs")
            if missing + n > len(values):
                raise C.TTRError("not enough non-NA values")
        result = np.full(len(values), NA)
        result[missing:] = np.maximum.accumulate(values[missing:])
        result[: n - 1 + missing] = NA
        return result
    return C.run_max(values, n)


def runMean(x, n: int = 10, cumulative: bool = False) -> np.ndarray:
    if cumulative:
        values = C.column(x)
        missing = int(np.sum(~np.isfinite(values)))
        denom = np.concatenate([np.full(missing, NA), np.arange(1, len(values) - missing + 1)])
        return runSum(x, n, True) / denom
    return runSum(x, n) / n


def runMedian(x, n: int = 10, non_unique: str = "mean", cumulative: bool = False) -> np.ndarray:
    values = _uni(x, "x")
    n = _check_n(n, len(values))
    which = match_arg(non_unique, ["mean", "max", "min"])
    tie = {"mean": 0, "max": 1, "min": -1}[which]
    return C.run_median(values, n, tie, cumulative)


def runCov(x, y, n: int = 10, use: str = "all.obs", sample: bool = True, cumulative: bool = False) -> np.ndarray:
    left = _uni(x, "x")
    right = _uni(y, "y")
    n = _check_n(n, len(left))
    match_arg(use, ["all.obs", "complete.obs", "pairwise.complete.obs"])
    return C.run_cov(left, right, n, sample, cumulative)


def runCor(x, y, n: int = 10, use: str = "all.obs", sample: bool = True, cumulative: bool = False) -> np.ndarray:
    return runCov(x, y, n, use, sample, cumulative) / (
        runSD(x, n, sample, cumulative) * runSD(y, n, sample, cumulative)
    )


def runVar(x, y=None, n: int = 10, sample: bool = True, cumulative: bool = False) -> np.ndarray:
    if y is None:
        y = x
    return runCov(x, y, n, "all.obs", sample, cumulative)


def runSD(x, n: int = 10, sample: bool = True, cumulative: bool = False) -> np.ndarray:
    return np.sqrt(runCov(x, x, n, "all.obs", sample, cumulative))


def runMAD(
    x,
    n: int = 10,
    center=None,
    stat: str = "median",
    constant: float = 1.4826,
    non_unique: str = "mean",
    cumulative: bool = False,
) -> np.ndarray:
    values = _uni(x, "x")
    n = _check_n(n, len(values))
    if center is None:
        center = runMedian(values, n, non_unique, cumulative)
    median = match_arg(stat, ["mean", "median"]) == "median"
    which = {"mean": 0, "max": 1, "min": -1}[match_arg(non_unique, ["mean", "max", "min"])]
    result = C.run_mad(values, center, n, median, which, cumulative)
    if median:
        result = result * constant
    return result


def wilderSum(x, n: int = 10) -> np.ndarray:
    values = _uni(x, "x")
    n = _check_n(n, len(values))
    naCheck(values, n)
    return C.wilder_sum(values, n)


def runPercentRank(x, n: int = 260, cumulative: bool = False, exact_multiplier: float = 0.5) -> np.ndarray:
    values = C.column(x)
    n = _check_n(n, len(values))
    if exact_multiplier < 0 or exact_multiplier > 1:
        raise C.TTRError(
            f"exact.multiplier = {exact_multiplier} is outside valid range: [0, 1]"
        )
    missing = int(np.sum(~np.isfinite(values)))
    if missing and not np.isfinite(values[missing:]).all():
        raise C.TTRError("Series contains non-leading NAs")
    if not cumulative and int(n) == 1:
        return np.full(len(values), exact_multiplier)
    return C.percent_rank(values, n, bool(cumulative), float(exact_multiplier))


def SMA(x, n: int = 10, **kwargs) -> np.ndarray:
    return runMean(x, n)


def EMA(x, n: int = 10, wilder: bool = False, ratio=None, **kwargs) -> np.ndarray:
    values = _uni(x, "x")
    if ratio is None and (n < 1 or n > len(values)):
        raise C.TTRError(f"n = {n} is outside valid range: [1, {len(values)}]")
    period = None if ratio is not None and n is None else n
    return C.ema_c(values, period, ratio, bool(wilder))


def DEMA(x, n: int = 10, v: float = 1, wilder: bool = False, ratio=None) -> np.ndarray:
    values = _uni(x, "x")
    if n < 1 or n > len(values):
        raise C.TTRError(f"n = {n} is outside valid range: [1, {len(values)}]")
    if v < 0 or v > 1:
        raise C.TTRError("Please ensure 0 <= v <= 1")
    period = None if ratio is not None and n is None else n
    first = C.ema_c(values, period, ratio, bool(wilder))
    second = C.ema_c(first, period, ratio, bool(wilder))
    return (1 + v) * first - second * v


def WMA(x, n: int = 10, wts=None, **kwargs) -> np.ndarray:
    values = _uni(x, "x")
    n = _check_n(n, len(values))
    if wts is None:
        weights = np.arange(1, n + 1, dtype=float)
    else:
        weights = C.column(wts)
    if len(weights) not in (len(values), n):
        raise C.TTRError("Length of 'wts' must equal the length of 'x' or 'n'")
    if len(weights) == n:
        if not np.isfinite(weights).all():
            raise C.TTRError("'wts' vector of length 'n' cannot have NA values")
        ma = C.wma_c(values, weights, n)
    else:
        ma = runSum(values * weights, n) / runSum(weights, n)
    ma = ma.copy()
    ma[: n - 1] = NA
    return ma


def EVWMA(price, volume, n: int = 10, **kwargs) -> np.ndarray:
    prices = _uni(price, "price")
    volumes = C.column(volume)
    if len(volumes) not in (len(prices), 1):
        raise C.TTRError("Length of 'volume' must equal 1 or the length of 'price'")
    n = _check_n(n, len(prices))
    if len(volumes) == 1:
        volumes = np.full(len(prices), volumes[0])
    finite = np.column_stack([np.isfinite(prices), np.isfinite(volumes)]).sum(axis=0)
    if np.any(n > finite):
        which = ["price", "volume"][int(np.flatnonzero(n > finite)[0])]
        raise C.TTRError(f"n > number of non-NA values in {which}")
    return C.evwma_c(prices, volumes, n)


def ZLEMA(x, n: int = 10, ratio=None, **kwargs) -> np.ndarray:
    values = _uni(x, "x")
    period = None if ratio is not None and n is None else n
    return C.zlema_c(values, period, ratio)


def VWAP(price, volume, n: int = 10, **kwargs) -> np.ndarray:
    return WMA(price, n=n, wts=volume)


VWMA = VWAP


def HMA(x, n: int = 20, **kwargs) -> np.ndarray:
    diff = 2 * WMA(x, n=int(n // 2), **kwargs) - WMA(x, n=n, **kwargs)
    return WMA(diff, n=int(math.trunc(math.sqrt(n))), **kwargs)


def ALMA(x, n: int = 9, offset: float = 0.85, sigma: float = 6, **kwargs) -> np.ndarray:
    values = C.as_float(x)
    if values.ndim == 1:
        values = values.reshape(-1, 1)
    if offset < 0 or offset > 1:
        raise C.TTRError("Please ensure 0 <= offset <= 1")
    if sigma <= 0:
        raise C.TTRError("sigma must be > 0")
    m = math.floor(offset * (n - 1))
    s = n / sigma
    slots = np.arange(n, dtype=float)
    weights = np.exp(-((slots - m) ** 2) / (2 * s * s))
    total = float(weights.sum())
    if total != 0:
        weights = weights / total
    out = np.empty_like(values)
    for i in range(values.shape[1]):
        out[:, i] = WMA(values[:, i], n, weights)
    return out[:, 0] if out.shape[1] == 1 else out


_MA = {
    "SMA": SMA,
    "EMA": EMA,
    "WMA": WMA,
    "DEMA": DEMA,
    "EVWMA": EVWMA,
    "ZLEMA": ZLEMA,
    "VWAP": VWAP,
    "VWMA": VWMA,
    "HMA": HMA,
    "ALMA": ALMA,
}


def ROC(x, n: int = 1, type: str = "continuous", na_pad: bool = True) -> np.ndarray:
    values = C.column(x)
    kind = match_arg(type, ["continuous", "discrete"])
    pad = np.full(n, NA) if na_pad else np.array([])
    if kind == "discrete":
        change = values[n:] / values[: len(values) - n] - 1
    else:
        change = np.log(values[n:]) - np.log(values[: len(values) - n])
    return np.concatenate([pad, change])


def momentum(x, n: int = 1, na_pad: bool = True) -> np.ndarray:
    values = C.column(x)
    pad = np.full(n, NA) if na_pad else np.array([])
    change = values[n:] - values[: len(values) - n]
    return np.concatenate([pad, change])


def TR(HLC) -> Frame:
    prices = C.as_float(HLC)
    if prices.ndim == 1:
        prices = prices.reshape(-1, 1)
    close_lag = np.concatenate([[NA], prices[:-1, 2]])
    true_high = pmax(prices[:, 0], close_lag)
    true_low = pmin(prices[:, 1], close_lag)
    tr = true_high - true_low
    return Frame(np.column_stack([tr, true_high, true_low]), ["tr", "trueHigh", "trueLow"])


def ATR(HLC, n: int = 14, maType=None, **kwargs) -> Frame:
    tr = TR(HLC)
    extra = dict(kwargs)
    if maType is None:
        maType = "EMA"
        extra.setdefault("wilder", True)
    atr = _call_ma(maType, tr["tr"], n, extra)
    return Frame(np.column_stack([tr["tr"], atr, tr["trueHigh"], tr["trueLow"]]), ["tr", "atr", "trueHigh", "trueLow"])


def ADX(HLC, n: int = 14, maType=None, **kwargs) -> Frame:
    prices = C.as_float(HLC)
    dh = momentum(prices[:, 0])
    dl = -momentum(prices[:, 1])
    neither = r_or(r_eq(dh, dl), r_and(r_lt(dh, 0), r_lt(dl, 0)))
    dm_plus = r_ifelse(neither, 0, r_ifelse(r_gt(dh, dl), dh, 0))
    dm_minus = r_ifelse(neither, 0, r_ifelse(r_lt(dh, dl), dl, 0))
    tr_sum = wilderSum(TR(prices)["tr"], n)
    dip = 100 * wilderSum(dm_plus, n) / tr_sum
    din = 100 * wilderSum(dm_minus, n) / tr_sum
    dx = 100 * (np.abs(dip - din) / (dip + din))
    extra = dict(kwargs)
    if maType is None:
        maType = "EMA"
        extra.setdefault("wilder", True)
    adx = _call_ma(maType, dx, n, extra)
    return Frame(np.column_stack([dip, din, dx, adx]), ["DIp", "DIn", "DX", "ADX"])


def aroon(HL, n: int = 20) -> Frame:
    prices = C.as_float(HL)
    if prices.ndim == 1 or prices.shape[1] == 1:
        high = low = C.column(prices)
    elif prices.shape[1] == 2:
        high, low = prices[:, 0], prices[:, 1]
    else:
        raise C.TTRError("Price series must be either High-Low, or Close")
    up = C.aroon_max(high, n)
    down = C.aroon_max(-low, n)
    return Frame(np.column_stack([up, down, up - down]), ["aroonUp", "aroonDn", "oscillator"])


def BBands(HLC, n: int = 20, maType=None, sd: float = 2, **kwargs) -> Frame:
    prices = _typical(HLC)
    if maType is None:
        maType = "SMA"
    average = _call_ma(maType, prices, n, kwargs)
    sdev = runSD(prices, n, sample=False)
    up = average + sd * sdev
    down = average - sd * sdev
    pct_b = (prices - down) / (up - down)
    return Frame(np.column_stack([down, average, up, pct_b]), ["dn", "mavg", "up", "pctB"])


def _typical(HLC) -> np.ndarray:
    prices = C.as_float(HLC)
    if prices.ndim == 1 or prices.shape[1] == 1:
        return C.column(prices)
    if prices.shape[1] == 3:
        # R's apply(..., mean) sums in long double, then divides.
        wide = prices.astype(np.longdouble)
        return (wide.sum(axis=1) / np.longdouble(prices.shape[1])).astype(np.float64)
    raise C.TTRError("Price series must be either High-Low-Close, or Close/univariate.")


def CCI(HLC, n: int = 20, maType=None, c: float = 0.015, **kwargs) -> np.ndarray:
    prices = _typical(HLC)
    if maType is None:
        maType = "SMA"
    average = _call_ma(maType, prices, n, kwargs)
    mean_dev = runMAD(prices, n, center=average, stat="mean")
    return (prices - average) / (c * mean_dev)


def CLV(HLC) -> np.ndarray:
    prices = C.as_float(HLC)
    clv = ((prices[:, 2] - prices[:, 1]) - (prices[:, 0] - prices[:, 2])) / (prices[:, 0] - prices[:, 1])
    clv[~np.isfinite(clv)] = 0
    return clv


def CMF(HLC, volume, n: int = 20) -> np.ndarray:
    clv = CLV(HLC)
    vol = C.column(volume)
    return runSum(clv * vol, n) / runSum(vol, n)


def CMO(x, n: int = 14) -> np.ndarray:
    up = momentum(x, 1)
    down = r_ifelse(r_lt(up, 0), np.abs(up), 0)
    up = r_ifelse(r_gt(up, 0), up, 0)
    up = runSum(up, n)
    down = runSum(down, n)
    return 100 * (up - down) / (up + down)


def _spearman(window: np.ndarray) -> float:
    left = window[:, 0]
    right = window[:, 1]
    if not np.isfinite(left).all() or not np.isfinite(right).all():
        return NA
    return float(np.corrcoef(_rank(left), _rank(right))[0, 1])


def _rank(values: np.ndarray) -> np.ndarray:
    order = np.argsort(values, kind="mergesort")
    ranks = np.empty(len(values), dtype=float)
    sorted_values = values[order]
    start = 0
    while start < len(values):
        end = start + 1
        while end < len(values) and sorted_values[end] == sorted_values[start]:
            end += 1
        average = (start + 1 + end) / 2.0
        ranks[order[start:end]] = average
        start = end
    return ranks


def CTI(price, n: int = 20, slope: float = 1) -> np.ndarray:
    values = C.column(price)
    line = slope * np.arange(1, len(values) + 1, dtype=float)
    paired = np.column_stack([values, line])
    out = np.full(len(values), NA)
    for i in range(n - 1, len(values)):
        out[i] = _spearman(paired[i - n + 1 : i + 1])
    return out


def DonchianChannel(HL, n: int = 10, include_lag: bool = False) -> Frame:
    prices = C.as_float(HL)
    if prices.ndim == 1 or prices.shape[1] == 1:
        high = low = C.column(prices)
    elif prices.shape[1] == 2:
        high, low = prices[:, 0], prices[:, 1]
    else:
        raise C.TTRError("Price series must be either High-Low, or Close/univariate.")
    upper = runMax(high, n)
    lower = runMin(low, n)
    mid = (upper + lower) / 2
    result = np.column_stack([upper, mid, lower])
    if include_lag:
        result = np.vstack([np.full(3, NA), result[:-1]])
    return Frame(result, ["high", "mid", "low"])


def DPO(x, n: int = 10, maType=None, shift=None, percent: bool = False, **kwargs) -> np.ndarray:
    values = C.column(x)
    if shift is None:
        shift = n / 2 + 1
    if maType is None:
        maType = "SMA"
    average = lead(_call_ma(maType, values, n, kwargs), shift)
    if percent:
        return 100 * (values / average - 1)
    return values - average


def DVI(
    price,
    n: int = 252,
    wts=(0.8, 0.2),
    smooth: int = 3,
    magnitude=(5, 100, 5),
    stretch=(10, 100, 2),
    exact_multiplier: float = 1,
) -> Frame:
    values = C.column(price)
    weights = np.asarray(wts, dtype=float)
    weights = weights / weights.sum()
    returns = values / SMA(values, smooth) - 1
    mag = SMA((SMA(returns, magnitude[0]) + SMA(returns, magnitude[1]) / 10) / 2, magnitude[2])
    sign = r_ifelse(r_gt(values, lead(values, -1)), 1, -1)
    stretched = SMA((runSum(sign, stretch[0]) + runSum(sign, stretch[1]) / 10) / 2, stretch[2])
    dvi_mag = runPercentRank(mag, n, False, exact_multiplier)
    dvi_str = runPercentRank(stretched, n, False, exact_multiplier)
    dvi = weights[0] * dvi_mag + weights[1] * dvi_str
    return Frame(np.column_stack([dvi_mag, dvi_str, dvi]), ["dvi.mag", "dvi.str", "dvi"])


def EMV(HL, volume, n: int = 9, maType=None, vol_divisor: float = 10000, **kwargs) -> Frame:
    if HL is None or volume is None:
        raise C.TTRError("High-Low matrix (HL) and volume vector must be specified.")
    prices = C.as_float(HL)
    vol = C.column(volume) / vol_divisor
    mid = (prices[:, 0] + prices[:, 1]) / 2
    emv = momentum(mid, 1) / (vol / (prices[:, 0] - prices[:, 1]))
    if maType is None:
        maType = "SMA"
    smooth = _call_ma(maType, emv, n, kwargs)
    return Frame(np.column_stack([emv, smooth]), ["emv", "maEMV"])


def GMMA(x, short=(3, 5, 8, 10, 12, 15), long=(30, 35, 40, 45, 50, 60), maType=None) -> Frame:
    if maType is None:
        maType = "EMA"
    groups = list(short) + list(long)
    columns = [_call_ma(maType, x, g) for g in groups]
    names = [f"short lag {g}" for g in short] + [f"long lag {g}" for g in long]
    return Frame(np.column_stack(columns), names)


def KST(price, n=(10, 10, 10, 15), nROC=(10, 15, 20, 30), nSig: int = 9, maType=None, wts=None, **kwargs) -> Frame:
    periods = list(n)
    rocs = list(nROC)
    weights = list(range(1, len(periods) + 1)) if wts is None else list(wts)
    if not (len(periods) == len(weights) == len(rocs)):
        raise C.TTRError("'n', 'nROC', and 'wts' must be the same length.")
    if maType is None:
        maType = "SMA"
    pieces = []
    for period, look, weight in zip(periods, rocs, weights):
        change = ROC(price, look, na_pad=True)
        pieces.append(_call_ma(maType, change, period, kwargs) * weight)
    stacked = np.column_stack(pieces)
    kst = 100 * np.sum(stacked, axis=1)
    signal = _call_ma(maType, kst, nSig, kwargs)
    return Frame(np.column_stack([kst, signal]), ["kst", "signal"])


def MACD(x, nFast: int = 12, nSlow: int = 26, nSig: int = 9, maType=None, percent: bool = True, **kwargs) -> Frame:
    if maType is None:
        maType = "EMA"
    fast = _call_ma(maType, x, nFast, kwargs)
    slow = _call_ma(maType, x, nSlow, kwargs)
    macd = 100 * (fast / slow - 1) if percent else fast - slow
    signal = _call_ma(maType, macd, nSig, kwargs)
    return Frame(np.column_stack([macd, signal]), ["macd", "signal"])


def MFI(HLC, volume, n: int = 14) -> np.ndarray:
    prices = _typical(HLC)
    vol = C.column(volume)
    lagged = np.concatenate([[NA], prices[:-1]])
    flow = prices * vol
    positive = r_ifelse(r_gt(prices, lagged), flow, 0)
    negative = r_ifelse(r_lt(prices, lagged), flow, 0)
    num = runSum(positive, n)
    den = runSum(negative, n)
    ratio = num / den
    mfi = 100 - (100 / (1 + ratio))
    mfi[den == 0] = 100
    mfi[(den == 0) & (num == 0)] = 50
    return mfi


def OBV(price, volume) -> np.ndarray:
    prices = C.column(price)
    vol = C.column(volume)
    change = ROC(prices)
    signed = np.where(change > 0, vol, -vol)
    signed = signed.astype(float)
    signed[0] = vol[0]
    signed[np.abs(change) < math.sqrt(np.finfo(float).eps)] = 0
    return np.cumsum(signed)


def RSI(price, n: int = 14, maType=None, **kwargs) -> np.ndarray:
    up = momentum(price, 1, True)
    down = up * 0
    falling = up < 0
    falling = falling & np.isfinite(up)
    down = down.astype(float)
    down[falling] = -up[falling]
    up = up.copy()
    up[falling] = 0
    extra = dict(kwargs)
    if maType is None:
        maType = "EMA"
        extra.setdefault("wilder", True)
    up_ma = _call_ma(maType, up, n, extra)
    down_ma = _call_ma(maType, down, n, extra)
    return 100 * up_ma / (up_ma + down_ma)


def SAR(HL, accel=(0.02, 0.2)) -> np.ndarray:
    prices = C.as_float(HL)
    naCheck(prices, 0)
    gap = float(np.nanstd(prices[:, 0] - prices[:, 1], ddof=1))
    return C.sar_c(prices[:, 0], prices[:, 1], accel, gap)


def SNR(HLC, n, **kwargs) -> np.ndarray:
    prices = C.as_float(HLC)
    moved = np.abs(prices[:, 2] - lead(prices[:, 2], -n))
    return moved / ATR(prices, n, **kwargs)["atr"]


def TDI(price, n: int = 20, multiple: int = 2) -> Frame:
    mom = momentum(price, n, True)
    mom = mom.copy()
    mom[~np.isfinite(mom)] = 0
    di = runSum(mom, n)
    tdi = np.abs(di) - (runSum(np.abs(mom), n * multiple) - runSum(np.abs(mom), n))
    return Frame(np.column_stack([tdi, di]), ["tdi", "di"])


def TRIX(price, n: int = 20, nSig: int = 9, maType=None, percent: bool = True, **kwargs) -> Frame:
    if maType is None:
        maType = "EMA"
    first = _call_ma(maType, price, n, kwargs)
    second = _call_ma(maType, first, n, kwargs)
    third = _call_ma(maType, second, n, kwargs)
    trix = ROC(third, 1, "discrete", True) * (100 if percent else 1)
    if not percent:
        trix = momentum(third, 1, True)
    signal = _call_ma(maType, trix, nSig, kwargs)
    return Frame(np.column_stack([trix, signal]), ["TRIX", "signal"])


def VHF(price, n: int = 28) -> np.ndarray:
    prices = C.as_float(price)
    if prices.ndim == 1 or prices.shape[1] == 1:
        high = low = close = C.column(prices)
    elif prices.shape[1] == 3:
        high, low, close = prices[:, 0], prices[:, 1], prices[:, 2]
    else:
        raise C.TTRError("Price series must be either Close, or High-Low-Close")
    denom = np.abs(momentum(close, 1, True))
    return (runMax(high, n) - runMin(low, n)) / runSum(denom, n)


def WPR(HLC, n: int = 14) -> np.ndarray:
    prices = C.as_float(HLC)
    if prices.ndim == 1 or prices.shape[1] == 1:
        high = low = close = C.column(prices)
    elif prices.shape[1] == 3:
        high, low, close = prices[:, 0], prices[:, 1], prices[:, 2]
    else:
        raise C.TTRError("Price series must be either High-Low-Close, or Close")
    highest = runMax(high, n)
    lowest = runMin(low, n)
    pct = (highest - close) / (highest - lowest)
    pct[np.isnan(pct) & np.isfinite(highest) & np.isfinite(close)] = 0.5
    return pct


def stoch(HLC, nFastK: int = 14, nFastD: int = 3, nSlowD: int = 3, maType=None, bounded: bool = True, smooth: int = 1, **kwargs) -> Frame:
    prices = C.as_float(HLC)
    if prices.ndim == 1 or prices.shape[1] == 1:
        high = low = close = C.column(prices)
    elif prices.shape[1] == 3:
        high, low, close = prices[:, 0], prices[:, 1], prices[:, 2]
    else:
        raise C.TTRError("Price series must be either High-Low-Close, or Close")
    if bounded:
        highest = runMax(high, nFastK)
        lowest = runMin(low, nFastK)
    else:
        highest = runMax(np.concatenate([[high[0]], high[:-1]]), nFastK)
        lowest = runMin(np.concatenate([[low[0]], low[:-1]]), nFastK)
    num = close - lowest
    den = highest - lowest
    if maType is None:
        maType = "SMA"
    num_ma = _call_ma(maType, num, smooth)
    den_ma = _call_ma(maType, den, smooth)
    fast_k = num_ma / den_ma
    fast_k = np.array(fast_k, dtype=float, copy=True)
    fast_k[np.isinf(fast_k)] = 0.5
    fast_d = _call_ma(maType, fast_k, nFastD, kwargs)
    slow_d = _call_ma(maType, fast_d, nSlowD, kwargs)
    return Frame(np.column_stack([fast_k, fast_d, slow_d]), ["fastK", "fastD", "slowD"])


def SMI(HLC, n: int = 13, nFast: int = 2, nSlow: int = 25, nSig: int = 9, maType=None, bounded: bool = True, **kwargs) -> Frame:
    prices = C.as_float(HLC)
    if prices.ndim == 1 or prices.shape[1] == 1:
        high = low = close = C.column(prices)
    elif prices.shape[1] == 3:
        high, low, close = prices[:, 0], prices[:, 1], prices[:, 2]
    else:
        raise C.TTRError("Price series must be either High-Low-Close, or Close")
    if bounded:
        highest = runMax(high, n)
        lowest = runMin(low, n)
    else:
        highest = runMax(np.concatenate([[high[0]], high[:-1]]), n)
        lowest = runMax(np.concatenate([[low[0]], low[:-1]]), n)
    highest = np.where(np.isnan(highest), high, highest)
    lowest = np.where(np.isnan(lowest), low, lowest)
    span = highest - lowest
    center = close - (highest + lowest) / 2
    if maType is None:
        maType = "EMA"
    num1 = _call_ma(maType, center, nSlow, kwargs)
    den1 = _call_ma(maType, span, nSlow, kwargs)
    num2 = _call_ma(maType, num1, nFast, kwargs)
    den2 = _call_ma(maType, den1, nFast, kwargs)
    smi = 100 * (num2 / (den2 / 2))
    signal = _call_ma(maType, smi, nSig, kwargs)
    return Frame(np.column_stack([smi, signal]), ["SMI", "signal"])


def ultimateOscillator(HLC, n=(7, 14, 28), wts=(4, 2, 1)) -> np.ndarray:
    if len(n) != 3 or len(wts) != 3:
        raise C.TTRError("length(n) and length(wts) must both be 3")
    prices = C.as_float(HLC)
    atr = ATR(prices, n=1)
    pressure = prices[:, 2] - atr["trueLow"]
    osc = np.zeros(len(prices))
    for periods, weight in zip(n, wts):
        osc = osc + weight * (runSum(pressure, periods) / runSum(atr["tr"], periods))
    return 100.0 * osc / sum(wts)


def volatility(OHLC, n: int = 10, calc: str = "close", N: int = 260, mean0: bool = False, **kwargs) -> np.ndarray:
    prices = C.as_float(OHLC)
    kind = match_arg(calc, ["close", "garman.klass", "parkinson", "rogers.satchell", "gk.yz", "yang.zhang"])
    if kind == "close":
        column_index = 0 if prices.ndim == 1 or prices.shape[1] == 1 else 3
        returns = ROC(C.column(prices) if column_index == 0 else prices[:, column_index], 1, **_roc_kwargs(kwargs))
        if mean0:
            return math.sqrt(N) * np.sqrt(runSum(returns**2, n - 1) / (n - 2))
        return math.sqrt(N) * runSD(returns, n - 1)
    if kind == "garman.klass":
        term = 0.5 * np.log(prices[:, 1] / prices[:, 2]) ** 2 - (2 * math.log(2) - 1) * np.log(prices[:, 3] / prices[:, 0]) ** 2
        return np.sqrt(N / n * runSum(term, n))
    if kind == "parkinson":
        return np.sqrt(N / (4 * n * math.log(2)) * runSum(np.log(prices[:, 1] / prices[:, 2]) ** 2, n))
    if kind == "rogers.satchell":
        term = np.log(prices[:, 1] / prices[:, 3]) * np.log(prices[:, 1] / prices[:, 0]) + np.log(prices[:, 2] / prices[:, 3]) * np.log(prices[:, 2] / prices[:, 0])
        return np.sqrt(N / n * runSum(term, n))
    close_lag = np.concatenate([[NA], prices[:-1, 3]])
    if kind == "gk.yz":
        term = np.log(prices[:, 0] / close_lag) ** 2 + 0.5 * np.log(prices[:, 1] / prices[:, 2]) ** 2 - (2 * math.log(2) - 1) * np.log(prices[:, 3] / prices[:, 0]) ** 2
        return np.sqrt(N / n * runSum(term, n))
    alpha = kwargs.get("alpha", 1.34)
    k = kwargs.get("k")
    if k is None:
        k = (alpha - 1) / (alpha + (n + 1) / (n - 1))
    open_var = N * runVar(np.log(prices[:, 0] / close_lag), n=n)
    close_var = N * runVar(np.log(prices[:, 3] / prices[:, 0]), n=n)
    rs = volatility(prices, n=n, calc="rogers.satchell", N=N)
    return np.sqrt(open_var + k * close_var + (1 - k) * (rs**2))


def _roc_kwargs(kwargs: dict) -> dict:
    keep = {}
    for name in ("type", "na_pad"):
        if name in kwargs:
            keep[name] = kwargs[name]
    return keep


def williamsAD(HLC) -> np.ndarray:
    prices = C.as_float(HLC)
    change = momentum(prices[:, 2], 1)
    atr = ATR(prices)
    ad = prices[:, 2] - r_ifelse(r_gt(change, 0), atr["trueLow"], atr["trueHigh"])
    ad = ad.copy()
    ad[change == 0] = 0
    info = naCheck(ad)
    filled = np.concatenate([np.full(info["NAs"], NA), np.cumsum(ad[info["nonNA"]])])
    return filled


def chaikinAD(HLC, volume) -> np.ndarray:
    ad = CLV(HLC) * C.column(volume)
    info = naCheck(ad)
    return np.concatenate([np.full(info["NAs"], NA), np.cumsum(ad[info["nonNA"]])])


def chaikinVolatility(HL, n: int = 10, maType=None, **kwargs) -> np.ndarray:
    prices = C.as_float(HL)
    if maType is None:
        maType = "EMA"
    average = _call_ma(maType, prices[:, 0] - prices[:, 1], n, kwargs)
    return ROC(average, n, type="discrete")


def keltnerChannels(HLC, n: int = 20, maType=None, atr: float = 2, **kwargs) -> Frame:
    prices = _typical(HLC)
    if maType is None:
        maType = "EMA"
    average = _call_ma(maType, prices, n, kwargs)
    width = ATR(HLC, n=n)["atr"]
    up = average + atr * width
    down = average - atr * width
    return Frame(np.column_stack([down, average, up]), ["dn", "mavg", "up"])


def PBands(prices, n: int = 20, maType="SMA", sd: float = 2, fastn: int = 2, centered: bool = False, lavg: bool = False, **kwargs) -> Frame:
    values = C.as_float(prices)
    if values.ndim == 2 and values.shape[1] > 1:
        raise C.TTRError("prices should be a univariate series, maybe use lapply(prices,PBands) instead?")
    values = C.column(values)
    if maType is None:
        maType = "SMA"
    average = _call_ma(maType, values, n, kwargs)
    fast = _call_ma(maType, values, fastn, kwargs)
    sdev = runSD(average - fast, n=n, sample=False)
    if not centered:
        center = average
    else:
        centerrun = (average - fast) / sdev
        center_n = n * 2 if lavg else n
        center = average + _call_ma(maType, centerrun, center_n, kwargs)
    up = center + sd * sdev
    down = center - sd * sdev
    return Frame(np.column_stack([down, center, up]), ["dn", "center", "up"])


def rollSFM(Ra, Rb, n: int = 60) -> Frame:
    beta = runCov(Ra, Rb, n) / runVar(Rb, n=n)
    alpha = runMean(Ra, n) - beta * runMean(Rb, n)
    se_resid = (1 / (n * (n - 2))) * (
        n * runSum(np.asarray(Ra, dtype=float) ** 2, n)
        - runSum(Ra, n) ** 2
        - beta**2 * (n * runSum(np.asarray(Rb, dtype=float) ** 2, n) - runSum(Rb, n) ** 2)
    )
    se_ra = runVar(Ra, n=n) * (n - 1) / (n - 2)
    r_squared = 1 - se_resid / se_ra
    return Frame(np.column_stack([alpha, beta, r_squared]), ["alpha", "beta", "r.squared"])


def ZigZag(HL, change: float = 10, percent: bool = True, retrace: bool = False, lastExtreme: bool = True) -> np.ndarray:
    prices = C.as_float(HL)
    info = naCheck(prices, 0)
    body = prices[info["nonNA"]]
    if body.ndim == 1 or body.shape[1] == 1:
        high = low = C.column(body)
    elif body.shape[1] == 2:
        high, low = body[:, 0], body[:, 1]
    else:
        raise C.TTRError("Price series must be either High-Low, or Univariate")
    zz = na_approx(C.zigzag_c(high, low, change, percent, retrace, lastExtreme))
    return np.concatenate([np.full(info["NAs"], NA), zz])


def lags(x, n: int = 1) -> Frame:
    values = C.as_float(x)
    if values.ndim == 1:
        values = values.reshape(-1, 1)
        names = ["V1"]
    else:
        names = [f"V{i}" for i in range(1, values.shape[1] + 1)]
    flat = values.ravel(order="F")
    width = n + 1
    rows = len(flat) - width + 1
    out = np.column_stack([flat[width - 1 - j : len(flat) - j] for j in range(width)])
    if rows != out.shape[0]:
        out = out[:rows]
    if n == 1:
        lag_names = [1]
    elif values.shape[1] == 1:
        lag_names = list(range(1, n + 1))
    else:
        lag_names = list(range(1, n + 1)) * values.shape[1]
    colnames = names + [f"{name}.{lag}" for name, lag in zip(names * ((len(lag_names) + len(names) - 1) // len(names)), sorted(lag_names))]
    # Match embed column names: original columns, then name.lag in the order R builds.
    extra = []
    if n == 1:
        extra = [f"{name}.1" for name in names]
    elif values.shape[1] == 1:
        extra = [f"{names[0]}.{lag}" for lag in range(1, n + 1)]
    else:
        ordered = sorted(list(range(1, n + 1)) * values.shape[1])
        extra = [f"{names[i % len(names)]}.{lag}" for i, lag in enumerate(ordered)]
    return Frame(out, names + extra[: out.shape[1] - len(names)])


def growth(price, signals=None, **kwargs) -> np.ndarray:
    values = C.column(price)
    if signals is None:
        signals = np.ones(len(values))
    else:
        signals = np.asarray(signals, dtype=float).reshape(-1)
    return np.cumprod(1 + ROC(values, **kwargs) * signals)


def adjRatios(splits=None, dividends=None, close=None) -> Frame:
    if dividends is not None and close is None:
        raise C.TTRError('"close" must be specified to adjust dividends')
    if close is None or (np.ndim(close) and C.n_row(close) == 0):
        close_values = np.array([NA])
    else:
        close_values = C.column(close)
    if splits is None:
        split_values = np.full(len(close_values), NA)
    else:
        split_values = C.column(splits)
    if dividends is None:
        div_values = np.full(len(close_values), NA)
    else:
        div_values = C.column(dividends)
    count = max(len(close_values), len(split_values), len(div_values))
    if len(close_values) == 1 and not np.isfinite(close_values[0]):
        close_values = np.full(count, NA)
    if len(split_values) == 1 and not np.isfinite(split_values[0]):
        split_values = np.full(count, NA)
    if len(div_values) == 1 and not np.isfinite(div_values[0]):
        div_values = np.full(count, NA)
    if not (len(close_values) == len(split_values) == len(div_values)):
        raise C.TTRError("close, splits, and dividends must be the same length")
    if np.isfinite(close_values).any():
        keep = np.isfinite(close_values)
        close_values = close_values[keep]
        split_values = split_values[keep]
        div_values = div_values[keep]
    split_ratio, div_ratio = C.adj_ratios_c(split_values, div_values, close_values)
    return Frame(np.column_stack([split_ratio, div_ratio]), ["Split", "Div"])


def ttrc() -> dict:
    path = Path(__file__).resolve().parent / "data" / "ttrc.csv"
    columns: dict[str, list] = {}
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        for name in reader.fieldnames or []:
            columns[name] = []
        for row in reader:
            for name, value in row.items():
                columns[name].append(value)
    out = {"Date": np.array(columns["Date"], dtype=object)}
    for name, values in columns.items():
        if name == "Date":
            continue
        out[name] = np.asarray(values, dtype=float)
    return out


_SYMBOL_COLUMNS = [
    "Symbol",
    "Name",
    "LastSale",
    "MarketCap",
    "IPOyear",
    "Sector",
    "Industry",
    "Exchange",
    "Test.Issue",
    "Round.Lot.Size",
    "ETF",
    "Market.Category",
    "Financial.Status",
    "Next.Shares",
    "ACT.Symbol",
    "CQS.Symbol",
]
_MARKET = {
    "Q": "NASDAQ Global Select MarketSM",
    "G": "NASDAQ Global MarketSM",
    "S": "NASDAQ Capital Market",
}
_EXCHANGE = {"A": "AMEX", "N": "NYSE", "P": "ARCA", "Z": "BATS", "V": "IEX"}
_STATUS = {
    "D": "Deficient",
    "E": "Delinquent",
    "Q": "Bankrupt",
    "N": "Normal (Default)",
    "G": "Deficient and Bankrupt",
    "H": "Deficient and Delinquent",
    "J": "Delinquent and Bankrupt",
    "K": "Deficient, Delinquent, and Bankrupt",
}


def _read_pipe(path: Path) -> list[dict]:
    rows = []
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle, delimiter="|")
        for row in reader:
            if row.get("Symbol") in (None, "Symbol") or "File Creation Time" in (row.get("Symbol") or ""):
                continue
            if any(value and "File Creation Time" in str(value) for value in row.values()):
                continue
            rows.append(row)
    return rows


def _make_names(name: str) -> str:
    text = name.replace(" ", ".")
    text = "".join(ch if ch.isalnum() or ch == "." else "." for ch in text)
    return text


def _blank(value):
    if value is None:
        return ""
    return str(value)


def _lookup(table: dict, code):
    if code is None or code == "":
        return None
    return table.get(code)


def _as_lot(value):
    text = _blank(value)
    if text == "":
        return None
    return int(text)


def _yes(value):
    # R compares with "Y" == column. An empty field is FALSE. A missing field is NA.
    if value is None:
        return None
    return value == "Y"


def _symbol_row(named: dict, *, nasdaq: bool) -> dict:
    item = {column: None for column in _SYMBOL_COLUMNS}
    item["Name"] = _blank(named.get("Security.Name"))
    if nasdaq:
        item["Symbol"] = _blank(named.get("Symbol"))
        item["Exchange"] = "NASDAQ"
        item["Market.Category"] = _lookup(_MARKET, named.get("Market.Category"))
        item["Financial.Status"] = _lookup(_STATUS, named.get("Financial.Status"))
    else:
        item["Symbol"] = _blank(named.get("NASDAQ.Symbol"))
        item["Exchange"] = _lookup(_EXCHANGE, named.get("Exchange"))
        item["ACT.Symbol"] = _blank(named.get("ACT.Symbol")) or None
        item["CQS.Symbol"] = _blank(named.get("CQS.Symbol")) or None
    item["Round.Lot.Size"] = _as_lot(named.get("Round.Lot.Size"))
    item["ETF"] = _yes(named.get("ETF"))
    item["Test.Issue"] = _yes(named.get("Test.Issue"))
    return item


def _read_listed(path: Path, drop_last: bool) -> list[dict]:
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle, delimiter="|")
        rows = []
        for row in reader:
            named = {_make_names(key): value for key, value in row.items() if key}
            rows.append(named)
    if drop_last and rows:
        rows = rows[:-1]
    return rows


def stockSymbols(exchange=None, sort_by=None, quiet: bool = False):
    import urllib.request

    choices = ["AMEX", "NASDAQ", "NYSE", "ARCA", "BATS", "IEX"]
    if exchange is None:
        exchange = choices
    exchange = match_arg(exchange, choices, several=True)
    if sort_by is None:
        sort_by = ["Exchange", "Symbol"]
    sort_by = match_arg(sort_by, _SYMBOL_COLUMNS, several=True)
    base = "ftp://ftp.nasdaqtrader.com/SymbolDirectory/"
    nasdaq_rows = []
    other_rows = []
    if "NASDAQ" in exchange:
        if not quiet:
            print("Fetching NASDAQ symbols...", flush=True)
        dest = Path(tempfile.gettempdir()) / "nasdaqlisted.txt"
        urllib.request.urlretrieve(base + "nasdaqlisted.txt", dest)
        nasdaq_rows = [_symbol_row(row, nasdaq=True) for row in _read_listed(dest, drop_last=False)]
    if len(exchange) > 1:
        if not quiet:
            print("Fetching non-NASDAQ symbols...", flush=True)
        dest = Path(tempfile.gettempdir()) / "otherlisted.txt"
        urllib.request.urlretrieve(base + "otherlisted.txt", dest)
        other_rows = [_symbol_row(row, nasdaq=False) for row in _read_listed(dest, drop_last=True)]
    symbols = nasdaq_rows + other_rows
    if not symbols:
        raise C.TTRError("incorrect number of dimensions")
    import re

    for row in symbols:
        symbol = row["Symbol"] or ""
        symbol = re.sub(r"-(.?)$", r"-P\1", symbol)
        symbol = re.sub(r"\.(.?)$", r"-\1", symbol)
        symbol = re.sub(r"\+(.?)$", r"-WT\1", symbol)
        symbol = re.sub(r"=$", "-UN", symbol)
        symbol = re.sub(r"\^$", "-R", symbol)
        row["Symbol"] = symbol

    import icu

    collator = icu.Collator.createInstance(icu.Locale.getDefault())

    def sort_value(value):
        if value is None:
            return (1, 0, b"")
        if isinstance(value, bool):
            return (0, int(value), b"")
        if isinstance(value, int):
            return (0, value, b"")
        return (0, 0, collator.getSortKey(str(value)))

    symbols.sort(key=lambda row: tuple(sort_value(row[name]) for name in sort_by))
    return symbols


def _unix_midnight(year: int, month: int, day: int) -> int:
    from datetime import datetime

    return int(datetime(year, month, day).timestamp())


def _date_to_unix(value) -> int:
    from datetime import datetime

    text = str(value)
    moment = datetime.strptime(text, "%Y%m%d")
    return _unix_midnight(moment.year, moment.month, moment.day)


def _yahoo_session():
    """The cookie jar TTR builds before it asks Yahoo for a crumb."""
    import http.cookiejar
    import random
    import string
    import time
    import urllib.request

    alphabet = string.ascii_lowercase + string.digits
    for _ in range(5):
        jar = http.cookiejar.CookieJar()
        opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
        token = "".join(random.sample(alphabet, 4))
        request = urllib.request.Request(
            f"https://finance.yahoo.com?{token}",
            headers={"User-Agent": "curl/8.14.1"},
        )
        try:
            with opener.open(request, timeout=30) as response:
                response.read()
        except OSError:
            pass
        if len(jar):
            return opener, jar
        time.sleep(0.1)
    raise C.TTRError("Could not establish session after 5 attempts.")


def getYahooData(symbol, start=None, end=None, freq: str = "daily", type: str = "price", adjust: bool = True, quiet: bool = False):
    """Download Yahoo Finance history. The session is a cookie jar, not a curl handle."""
    import urllib.request
    from datetime import datetime

    warnings.warn(
        "TTR::getYahooData is deprecated and will be removed in a future release.\nPlease use quantmod::getSymbols instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    intervals = {"daily": "1d", "weekly": "1wk", "monthly": "1mo"}
    freq = match_arg(freq, list(intervals))
    kind = match_arg(type, ["price", "split"])
    today = datetime.now()
    today_unix = _unix_midnight(today.year, today.month, today.day)
    beg = _unix_midnight(1900, 1, 1) if start is None else _date_to_unix(start)
    stop = today_unix if end is None else _date_to_unix(end)
    if beg > stop:
        raise C.TTRError("Start date must be before end date.")
    if beg > today_unix:
        raise C.TTRError("Start date is after today's date.")
    if kind != "price" and freq != "daily" and not quiet:
        print('Only freq="daily" data available for type="split".\nSetting freq="daily"...', flush=True)
        freq = "daily"
    if kind != "price" and not quiet:
        print("Unadjusted and adjusted dividend data are always returned.", flush=True)
    opener, _jar = _yahoo_session()
    server = 1 if (datetime.now().timestamp() % 1) >= 0.5 else 2
    crumb_url = f"https://query{server}.finance.yahoo.com/v1/test/getcrumb"
    with opener.open(crumb_url, timeout=30) as response:
        crumb = response.read().decode("utf-8", errors="replace")
    event = "history" if kind == "price" else "split"
    url = (
        f"https://query{server}.finance.yahoo.com/v7/finance/download/{symbol}"
        f"?period1={beg}&period2={stop}&interval={intervals[freq]}&events={event}&crumb={crumb}"
    )
    with opener.open(url, timeout=30) as response:
        text = response.read().decode("utf-8", errors="replace")
    rows = list(csv.DictReader(text.splitlines()))
    if kind != "price":
        raise C.TTRError("Could not establish session after 5 attempts.") if not rows else C.TTRError(text[:200])
    out = []
    for row in rows:
        item = {}
        for name in ("Open", "High", "Low", "Close", "Volume"):
            raw = row.get(name)
            item[name] = NA if raw in (None, "", "null") else float(raw)
        item["Date"] = row.get("Date")
        out.append(item)
    out.sort(key=lambda row: row["Date"] or "")
    if adjust:
        raise C.TTRError("Only freq=\"daily\" adjusted data is currently supported.") if freq != "daily" else C.TTRError(
            "adjust=TRUE merges prices with splits on a date index. This translation keeps the unadjusted columns; pass adjust=False."
        )
    return out
