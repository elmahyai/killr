"""Numeric kernels from TTR's C, on NumPy arrays."""

from __future__ import annotations

import math
import warnings

import numpy as np

NA = np.nan


class TTRError(ValueError):
    pass


def as_float(x) -> np.ndarray:
    arr = np.asarray(x, dtype=float)
    if arr.ndim == 0:
        arr = arr.reshape(1)
    return arr


def column(x, index: int | None = None) -> np.ndarray:
    arr = as_float(x)
    if arr.ndim == 1:
        if index not in (None, 0):
            raise TTRError("Price series has one column")
        return arr.reshape(-1)
    if index is None:
        if arr.shape[1] != 1:
            raise TTRError("expected one column")
        return arr[:, 0]
    return arr[:, index]


def n_row(x) -> int:
    arr = as_float(x)
    return arr.shape[0]


def n_col(x) -> int:
    arr = as_float(x)
    if arr.ndim == 1:
        return 1
    return arr.shape[1]


def leading_na(x: np.ndarray) -> int:
    """Index of the first finite value. Non-leading missing values are an error."""
    values = np.asarray(x, dtype=float).reshape(-1)
    first = 0
    count = len(values)
    while first < count and not np.isfinite(values[first]):
        first += 1
    if first < count and not np.isfinite(values[first:]).all():
        raise TTRError("Series contains non-leading NAs")
    return first


def _need(n: int, first: int, count: int, what: str = "") -> None:
    if n + first > count:
        if what:
            raise TTRError(f"not enough non-NA values in {what}")
        raise TTRError("not enough non-NA values")


def run_sum(x, n: int) -> np.ndarray:
    values = column(x)
    count = len(values)
    first = leading_na(values)
    _need(n, first, count)
    result = np.full(count, NA)
    seed = 0.0
    for i in range(first, first + n):
        seed += values[i]
    result[first + n - 1] = seed
    for i in range(first + n, count):
        result[i] = result[i - 1] + values[i] - values[i - n]
    return result


def run_min(x, n: int) -> np.ndarray:
    values = column(x)
    count = len(values)
    first = leading_na(values)
    _need(n, first, count)
    result = np.full(count, NA)
    lowest = values[first]
    for i in range(first, first + n):
        if values[i] < lowest:
            lowest = values[i]
    result[first + n - 1] = lowest
    for i in range(first + n, count):
        lowest = values[i]
        for j in range(1, n):
            if values[i - j] < lowest:
                lowest = values[i - j]
        result[i] = lowest
    return result


def run_max(x, n: int) -> np.ndarray:
    values = column(x)
    count = len(values)
    first = leading_na(values)
    _need(n, first, count)
    result = np.full(count, NA)
    highest = values[first]
    for i in range(first, first + n):
        if values[i] > highest:
            highest = values[i]
    result[first + n - 1] = highest
    for i in range(first + n, count):
        highest = values[i]
        for j in range(1, n):
            if values[i - j] > highest:
                highest = values[i - j]
        result[i] = highest
    return result


def _tie(a: float, b: float, which: int) -> float:
    if which == 0:
        return (a + b) / 2.0
    if which < 0:
        return a if a < b else b
    return a if a > b else b


def _median(window: np.ndarray, which: int) -> float:
    ordered = np.sort(window)
    length = len(ordered)
    odd = length - 2 * (length // 2)
    mid = length // 2 - 1
    if odd:
        return float(ordered[mid + 1])
    return _tie(float(ordered[mid]), float(ordered[mid + 1]), which)


def run_median(x, n: int, tie: int = 0, cumulative: bool = False) -> np.ndarray:
    values = column(x)
    count = len(values)
    first = leading_na(values)
    _need(n, first, count)
    result = np.full(count, NA)
    start = first + n - 1
    if cumulative:
        for i in range(start, count):
            result[i] = _median(values[first : i + 1], tie)
    else:
        for i in range(start, count):
            result[i] = _median(values[i - n + 1 : i + 1], tie)
    return result


def _mean(window: np.ndarray) -> float:
    total = 0.0
    length = len(window)
    for value in window:
        total += value / length
    return total


def run_mad(x, center, n: int, median: bool, tie: int, cumulative: bool) -> np.ndarray:
    values = column(x)
    middle = column(center)
    count = len(values)
    if len(middle) != count:
        raise TTRError("'x' and 'center' must have the same number of observations")
    first = leading_na(values)
    _need(n, first, count, "'x'")
    result = np.full(count, NA)
    start = first + n - 1
    if cumulative:
        for i in range(start, count):
            if median:
                length = i - first + 1
                window = np.empty(length)
                for j in range(length):
                    window[j] = abs(values[i - j] - middle[i])
                result[i] = _median(window, tie)
            else:
                window = np.empty(i + 1)
                for j in range(i + 1):
                    window[j] = abs(values[i - j] - middle[i])
                result[i] = _mean(window)
    else:
        for i in range(start, count):
            window = np.empty(n)
            for j in range(n):
                window[j] = abs(values[i - j] - middle[i])
            result[i] = _median(window, tie) if median else _mean(window)
    return result


def run_cov(x, y, n: int, sample: bool = True, cumulative: bool = False) -> np.ndarray:
    left = column(x)
    right = column(y)
    count = len(left)
    if len(right) != count:
        raise TTRError("'x' and 'y' must have the same number of observations")
    first_x = leading_na(left)
    _need(n, first_x, count, "'x'")
    first_y = leading_na(right)
    _need(n, first_y, count, "'y'")
    first = max(first_x, first_y)
    start = first + n - 1
    result = np.full(count, NA)
    if cumulative:
        sum_x = 0.0
        sum_y = 0.0
        for i in range(first, start):
            sum_x += left[i]
            sum_y += right[i]
        for i in range(start, count):
            width = float(i - start + n)
            sum_x += left[i]
            sum_y += right[i]
            mu_x = sum_x / width
            mu_y = sum_y / width
            total = 0.0
            for j in range(first, i + 1):
                total += (left[j] - mu_x) * (right[j] - mu_y)
            result[i] = total / ((width - 1.0) if sample else width)
        result[first] = NA
        return result
    if n == 1:
        warnings.warn(
            "(co-)variance is not defined for one observation; returning NA",
            RuntimeWarning,
            stacklevel=2,
        )
        return result
    denom = (n - 1) if sample else n
    for i in range(start, count):
        mu_x = _mean(left[i - n + 1 : i + 1])
        mu_y = _mean(right[i - n + 1 : i + 1])
        total = 0.0
        for j in range(n):
            total += (left[i - j] - mu_x) * (right[i - j] - mu_y)
        result[i] = total / denom
    return result


def ema_c(x, n, ratio, wilder: bool) -> np.ndarray:
    values = column(x)
    if n_col(x) > 1 and as_float(x).ndim == 2 and as_float(x).shape[1] > 1:
        raise TTRError("ncol(x) > 1; EMA only supports univariate 'x'")
    count = len(values)
    period = None if n is None else int(n)
    decay = None if ratio is None else float(ratio)
    if period is None or period <= 0:
        if decay is None or decay <= 0:
            raise TTRError(
                f"either 'n' or 'ratio' must be specified and > 0\n'n' is {period} and 'ratio' is {decay}"
            )
        period = int(2.0 / decay - 1.0)
    elif decay is None:
        decay = (1.0 / period) if wilder else (2.0 / (period + 1))
    else:
        warnings.warn("both 'n' and 'ratio' are specified; using 'n'", RuntimeWarning, stacklevel=2)
        decay = (1.0 / period) if wilder else (2.0 / (period + 1))
    first = leading_na(values)
    _need(period, first, count)
    result = np.full(count, NA)
    seed = 0.0
    for i in range(first, first + period):
        seed += values[i] / period
    result[first + period - 1] = seed
    for i in range(first + period, count):
        result[i] = values[i] * decay + result[i - 1] * (1.0 - decay)
    return result


def evwma_c(price, volume, n: int) -> np.ndarray:
    prices = column(price)
    volumes = column(volume)
    count = len(prices)
    first_price = leading_na(prices)
    _need(n, first_price, count, "'price'")
    first_volume = leading_na(volumes)
    _need(n, first_volume, count, "'volume'")
    first = max(first_price, first_volume)
    begin = first + n - 1
    result = np.full(count, NA)
    result[begin] = prices[begin]
    vol_sum = 0.0
    for i in range(first, begin + 1):
        vol_sum += volumes[i]
    for i in range(begin + 1, count):
        vol_sum = vol_sum + volumes[i] - volumes[i - n]
        result[i] = ((vol_sum - volumes[i]) * result[i - 1] + volumes[i] * prices[i]) / vol_sum
    return result


def wma_c(x, weights, n: int) -> np.ndarray:
    values = column(x)
    wts = column(weights)
    count = len(values)
    first = leading_na(values)
    _need(n, first, count)
    result = np.full(count, NA)
    begin = first + n - 1
    weight_sum = 0.0
    for j in range(n):
        if not np.isfinite(wts[j]):
            raise TTRError("wts cannot contain NA")
        weight_sum += wts[j]
    for i in range(begin, count):
        start = i - n + 1
        total = 0.0
        for j in range(n):
            total += values[start + j] * wts[j]
        result[i] = total / weight_sum
    return result


def zlema_c(x, n, ratio) -> np.ndarray:
    values = column(x)
    count = len(values)
    period = None if n is None else int(n)
    decay = None if ratio is None else float(ratio)
    if period is None or period <= 0:
        if decay is None or decay <= 0:
            raise TTRError(
                f"either 'n' or 'ratio' must be specified and > 0\n'n' is {period} and 'ratio' is {decay}"
            )
        period = int(2.0 / decay - 1.0)
    elif decay is None:
        decay = 2.0 / (period + 1)
    else:
        warnings.warn("both 'n' and 'ratio' are specified; using 'n'", RuntimeWarning, stacklevel=2)
        decay = 2.0 / (period + 1)
    first = leading_na(values)
    _need(period, first, count)
    result = np.full(count, NA)
    seed = 0.0
    for i in range(first, first + period):
        seed += values[i] / period
    result[first + period - 1] = seed
    lag = 1.0 / decay
    wt = math.fmod(lag, 1.0)
    w1 = 1.0 - wt
    remain = 1.0 - decay
    for i in range(first + period, count):
        loc = int(i - lag)
        value = 2 * values[i] - (w1 * values[loc] + wt * values[loc + 1])
        result[i] = decay * value + remain * result[i - 1]
    return result


def wilder_sum(x, n: int) -> np.ndarray:
    values = column(x)
    count = len(values)
    result = np.empty(count)
    beg = n - 1
    total = 0.0
    i = 0
    while i < beg:
        if not np.isfinite(values[i]):
            result[i] = NA
            beg += 1
            if beg < count:
                result[beg] = 0.0
            i += 1
            continue
        if i < beg:
            result[i] = NA
        total += values[i]
        i += 1
    result[beg] = values[i] + total * (n - 1) / n
    for i in range(beg + 1, count):
        result[i] = values[i] + result[i - 1] * (n - 1) / n
    return result


def aroon_max(x, n: int) -> np.ndarray:
    values = column(x)
    count = len(values)
    first = leading_na(values)
    _need(n, first, count)
    result = np.full(count, NA)
    highest = values[0]
    loc = 0
    for i in range(first + n - 1):
        result[i] = NA
        if values[i] >= highest:
            highest = values[i]
            loc = 0
        loc += 1
    for i in range(first + n - 1, count):
        if loc > n:
            highest = values[i]
            loc = 0
            for j in range(1, n + 1):
                if values[i - j] > highest:
                    highest = values[i - j]
                    loc = j
        elif values[i] >= highest:
            highest = values[i]
            loc = 0
        result[i] = (100.0 * (n - loc)) / n
        loc += 1
    return result


def sar_c(high, low, accel, init_gap: float) -> np.ndarray:
    hi = column(high)
    lo = column(low)
    step = float(accel[0])
    cap = float(accel[1])
    count = len(hi)
    result = np.empty(count)
    beg = 1
    for i in range(count):
        if not np.isfinite(hi[i]) or not np.isfinite(lo[i]):
            result[i] = NA
            beg += 1
        else:
            break
    sig0 = 1
    xpt0 = hi[beg - 1]
    af0 = step
    result[beg - 1] = lo[beg - 1] - init_gap
    for i in range(beg, count):
        sig1 = sig0
        xpt1 = xpt0
        af1 = af0
        local_min = min(lo[i - 1], lo[i])
        local_max = max(hi[i - 1], hi[i])
        if sig1 == 1:
            sig0 = 1 if lo[i] > result[i - 1] else -1
            xpt0 = max(local_max, xpt1)
        else:
            sig0 = -1 if hi[i] < result[i - 1] else 1
            xpt0 = min(local_min, xpt1)
        if sig0 == sig1:
            result[i] = result[i - 1] + (xpt1 - result[i - 1]) * af1
            af0 = cap if af1 == cap else (step + af1)
            if sig0 == 1:
                af0 = af0 if xpt0 > xpt1 else af1
                result[i] = min(result[i], local_min)
            else:
                af0 = af0 if xpt0 < xpt1 else af1
                result[i] = max(result[i], local_max)
        else:
            af0 = step
            result[i] = xpt0
    return result


def zigzag_c(high, low, change: float, percent: bool, retrace: bool, last_extreme: bool) -> np.ndarray:
    hi = column(high)
    lo = column(low)
    if percent:
        change = change / 100.0
    count = len(hi)
    zigzag = np.full(count, NA)
    reference_price = (hi[0] + lo[0]) / 2.0
    reference_index = 0
    inflection_price = (hi[1] + lo[1]) / 2.0
    inflection_index = 1
    signal = 0
    for i in range(1, count):
        zigzag[i] = NA
        if percent:
            extreme_min = inflection_price * (1.0 - change)
            extreme_max = inflection_price * (1.0 + change)
        else:
            extreme_min = inflection_price - change
            extreme_max = inflection_price + change
        local_max = inflection_price if inflection_price > hi[i] else hi[i]
        local_min = inflection_price if inflection_price < lo[i] else lo[i]
        if signal == 0:
            if retrace:
                signal = 1 if inflection_price >= reference_price else -1
            else:
                if local_min <= extreme_min:
                    signal = -1
                if local_max >= extreme_max:
                    signal = 1
        if signal == -1:
            if lo[i] == local_min:
                if last_extreme or lo[i] != lo[i - 1]:
                    inflection_price = lo[i]
                    inflection_index = i
            if retrace:
                extreme_max = inflection_price + (reference_price - inflection_price) * change
            if hi[i] >= extreme_max:
                zigzag[reference_index] = reference_price
                reference_price = inflection_price
                reference_index = inflection_index
                inflection_price = hi[i]
                inflection_index = i
                signal = 1
                continue
        if signal == 1:
            if hi[i] == local_max:
                if last_extreme or hi[i] != hi[i - 1]:
                    inflection_price = hi[i]
                    inflection_index = i
            if retrace:
                extreme_min = inflection_price - (inflection_price - reference_price) * change
            if lo[i] <= extreme_min:
                zigzag[reference_index] = reference_price
                reference_price = inflection_price
                reference_index = inflection_index
                inflection_price = lo[i]
                inflection_index = i
                signal = -1
                continue
    zigzag[reference_index] = reference_price
    zigzag[inflection_index] = inflection_price
    return zigzag


def percent_rank(x, n: int, cumulative: bool, mult: float) -> np.ndarray:
    values = column(x)
    count = len(values)
    result = np.full(count, NA)
    beg = n - 1
    n_na = 0
    for i in range(beg):
        result[i] = NA
        if not np.isfinite(values[i]):
            beg += 1
            n_na += 1
            if beg >= count:
                raise TTRError(
                    f"runPercentRank input has {count} rows, {n_na} NA. Cannot calculate result with n = {n}."
                )
    if cumulative:
        result[beg] = mult
        for i in range(beg + 1, count):
            result[i] = _n_less(values, mult, i, 0) / (i + 1)
    else:
        for i in range(beg, count):
            result[i] = _n_less(values, mult, i, i - n + 1) / n
    return result


def _n_less(values: np.ndarray, mult: float, i: int, j1: int) -> float:
    n_less = mult
    current = values[i]
    for j in range(j1, i):
        diff = values[j] - current
        if diff < 0:
            n_less += 1.0
        elif abs(diff) < 1e-8:
            n_less += mult
    return n_less


def adj_ratios_c(splits, dividends, close) -> tuple[np.ndarray, np.ndarray]:
    split = column(splits)
    div = column(dividends)
    px = column(close)
    count = len(px)
    split_ratio = np.empty(count)
    div_ratio = np.empty(count)
    split_ratio[-1] = 1.0
    div_ratio[-1] = 1.0
    for i in range(count - 1, 0, -1):
        if not np.isfinite(split[i]):
            split_ratio[i - 1] = split_ratio[i]
        else:
            split_ratio[i - 1] = split_ratio[i] * split[i]
        if not np.isfinite(div[i]):
            div_ratio[i - 1] = div_ratio[i]
        else:
            div_ratio[i - 1] = div_ratio[i] * (1.0 - div[i] / px[i - 1])
    return split_ratio, div_ratio
