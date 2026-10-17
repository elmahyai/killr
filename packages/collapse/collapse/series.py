"""Cumulative sums, lags, differences, and within transformations.

A grouped lag uses the row `n` places back after the group has already been
seen `n` times. That is the ordered-panel rule in collapse. A cumulative sum
keeps a separate running total for each group in row order.
"""

from __future__ import annotations

import math

import numpy as np

from collapse.fast import (
    CollapseError,
    Frame,
    Mat,
    Vec,
    _frame,
    _looks_matrix,
    _matrix,
    _vector,
    _weights,
    factor,
)


def _codes(g, n):
    if g is None:
        return None, 0
    codes, _names = factor(g)
    if codes.shape[0] != n:
        raise CollapseError("length(g) must match length(x)")
    return codes, len(_names)


def _order(o, n):
    if o is None:
        return None
    index = np.asarray(o, dtype=int).reshape(-1)
    if index.shape[0] != n:
        raise CollapseError("length(o) must match length(x)")
    if np.any(index < 1) or np.any(index > n):
        raise CollapseError("o must be 1-based positions")
    return index - 1


def _cumsum_vector(x, g, na_rm, fill, o):
    x = _vector(x)
    n = x.shape[0]
    codes, ng = _codes(g, n)
    order = _order(o, n)
    out = np.empty(n, dtype=np.float64)
    if order is None:
        positions = range(n)
    else:
        positions = order.tolist()
    if codes is None:
        last = 0.0
        started = False
        for i in positions:
            value = float(x[i])
            missing = math.isnan(value)
            if not na_rm:
                last = value if not started else last + value
                started = True
                out[i] = last
            elif fill:
                if not started and missing:
                    last = 0.0
                elif not missing:
                    last = value if not started else last + value
                started = True
                out[i] = last
            else:
                if missing:
                    out[i] = np.nan
                else:
                    last = value if not started else last + value
                    started = True
                    out[i] = last
        return out
    last = np.zeros(ng, dtype=np.float64)
    started = np.zeros(ng, dtype=bool)
    for i in positions:
        gi = int(codes[i])
        value = float(x[i])
        missing = math.isnan(value)
        if not na_rm:
            last[gi] = value if not started[gi] else last[gi] + value
            started[gi] = True
            out[i] = last[gi]
        elif fill:
            if not missing:
                last[gi] = value if not started[gi] else last[gi] + value
            started[gi] = True
            out[i] = last[gi]
        else:
            if missing:
                out[i] = np.nan
            else:
                last[gi] = value if not started[gi] else last[gi] + value
                started[gi] = True
                out[i] = last[gi]
    return out


def _as_lags(n):
    if isinstance(n, (list, tuple, np.ndarray)):
        lags = [int(item) for item in np.asarray(n).reshape(-1)]
    else:
        lags = [int(n)]
    if any(item != item for item in lags):
        raise CollapseError("NA in n")
    return lags


def _lag_vector(x, n, codes, ng, fill):
    """Shift by n rows. With groups, count visits and then read x[i - n]."""
    length = x.shape[0]
    out = np.empty(length, dtype=np.float64)
    if n == 0:
        out[:] = x
        return out
    if abs(n) > length:
        raise CollapseError("lag-length exceeds length of vector")
    if codes is None:
        if n > 0:
            out[:n] = fill
            out[n:] = x[:-n]
        else:
            k = -n
            out[-k:] = fill
            out[:-k] = x[k:]
        return out
    seen = np.zeros(ng, dtype=int)
    if n > 0:
        for i in range(length):
            gi = int(codes[i])
            if seen[gi] == n:
                out[i] = x[i - n]
            else:
                out[i] = fill
                seen[gi] += 1
    else:
        for i in range(length - 1, -1, -1):
            gi = int(codes[i])
            if seen[gi] == n:
                out[i] = x[i - n]
            else:
                out[i] = fill
                seen[gi] -= 1
    return out


def _column_apply(values, fn):
    return np.column_stack([fn(values[:, j]) for j in range(values.shape[1])])


def _finish_vector(values):
    return Vec(values)


def _finish_matrix(values, columns=None):
    return Mat(values, columns=columns)


def _finish_frame(columns):
    return Frame(columns)


def _dispatch_columns(layout, x, fn):
    if layout == "vector":
        return _finish_vector(fn(_vector(x)))
    if layout == "matrix":
        if isinstance(x, Mat):
            values = np.asarray(x.values, dtype=np.float64)
            columns = x.columns
        else:
            values = _matrix(x)
            columns = None
        reduced = _column_apply(values, fn)
        return _finish_matrix(reduced, columns)
    columns, _nrow = _frame(x)
    return _finish_frame({name: fn(column) for name, column in columns.items()})


def _run_cumsum(layout, x, g=None, o=None, na_rm=True, fill=False):
    def one(column):
        return _cumsum_vector(column, g, na_rm, fill, o)

    return _dispatch_columns(layout, x, one)


def fcumsum_default(x, g=None, o=None, na_rm=True, fill=False, check_o=True):
    del check_o
    return _run_cumsum("vector", x, g, o, na_rm, fill)


def fcumsum_matrix(x, g=None, o=None, na_rm=True, fill=False, check_o=True):
    del check_o
    return _run_cumsum("matrix", x, g, o, na_rm, fill)


def fcumsum_data_frame(x, g=None, o=None, na_rm=True, fill=False, check_o=True):
    del check_o
    return _run_cumsum("frame", x, g, o, na_rm, fill)


def fcumsum(x, g=None, o=None, na_rm=True, fill=False, check_o=True):
    if isinstance(x, dict):
        return fcumsum_data_frame(x, g, o, na_rm, fill, check_o)
    if _looks_matrix(x):
        return fcumsum_matrix(x, g, o, na_rm, fill, check_o)
    return fcumsum_default(x, g, o, na_rm, fill, check_o)


def _flag_vector(x, lags, g, fill):
    x = _vector(x)
    codes, ng = _codes(g, x.shape[0])
    columns = [_lag_vector(x, lag, codes, ng, fill) for lag in lags]
    if len(columns) == 1:
        return columns[0]
    return np.column_stack(columns)


def _run_flag(layout, x, n=1, g=None, fill=np.nan):
    lags = _as_lags(n)
    if layout == "vector":
        values = _flag_vector(x, lags, g, fill)
        if values.ndim == 1:
            return Vec(values)
        names = [("F%d" % abs(lag) if lag < 0 else "L%d" % lag) if lag else "--" for lag in lags]
        return Mat(values, columns=names)
    if layout == "matrix":
        if len(lags) != 1:
            raise CollapseError("several lags of a matrix are not translated")
        def one(column):
            return _flag_vector(column, lags, g, fill)
        return _dispatch_columns(layout, x, one)
    if len(lags) != 1:
        raise CollapseError("several lags of a data frame are not translated")
    def one(column):
        return _flag_vector(column, lags, g, fill)
    return _dispatch_columns("frame", x, one)


def flag_default(x, n=1, g=None, t=None, fill=np.nan, stubs=True):
    if t is not None:
        raise CollapseError("a time variable is not translated")
    del stubs
    return _run_flag("vector", x, n, g, fill)


def flag_matrix(x, n=1, g=None, t=None, fill=np.nan, stubs=None):
    if t is not None:
        raise CollapseError("a time variable is not translated")
    del stubs
    return _run_flag("matrix", x, n, g, fill)


def flag_data_frame(x, n=1, g=None, t=None, fill=np.nan, stubs=None):
    if t is not None:
        raise CollapseError("a time variable is not translated")
    del stubs
    return _run_flag("frame", x, n, g, fill)


def flag(x, n=1, g=None, t=None, fill=np.nan, stubs=True):
    if isinstance(x, dict):
        return flag_data_frame(x, n, g, t, fill, stubs)
    if _looks_matrix(x):
        return flag_matrix(x, n, g, t, fill, stubs)
    return flag_default(x, n, g, t, fill, stubs)


def _diff_once(x, n, codes, ng, rho, fill):
    lagged = _lag_vector(x, n, codes, ng, np.nan)
    out = np.asarray(x, dtype=np.float64) - rho * lagged
    missing = np.isnan(lagged)
    out[missing] = fill
    return out


def _difference(x, n, times, codes, ng, rho, fill, take_log):
    values = np.log(np.asarray(x, dtype=np.float64)) if take_log else np.asarray(x, dtype=np.float64)
    for _ in range(times):
        values = _diff_once(values, n, codes, ng, rho, fill)
    return values


def _growth(x, n, times, codes, ng, fill, logdiff, scale, power):
    values = np.asarray(x, dtype=np.float64).copy()
    for _ in range(times):
        lagged = _lag_vector(values, n, codes, ng, np.nan)
        if logdiff:
            grown = scale * np.log(values / lagged)
        else:
            grown = scale * ((values / lagged) ** power - 1.0)
        missing = np.isnan(lagged)
        grown = np.asarray(grown, dtype=np.float64)
        grown[missing] = fill
        values = grown
    return values


def _run_diff(layout, x, n, times, g, fill, take_log, rho, kind, logdiff=False, scale=100.0, power=1.0):
    lags = _as_lags(n)
    diffs = _as_lags(times)

    def one(column):
        column = _vector(column)
        codes, ng = _codes(g, column.shape[0])
        pieces = []
        for lag in lags:
            for repeat in diffs:
                if kind == "diff":
                    pieces.append(_difference(column, lag, repeat, codes, ng, rho, fill, take_log))
                else:
                    pieces.append(_growth(column, lag, repeat, codes, ng, fill, logdiff, scale, power))
        if len(pieces) == 1:
            return pieces[0]
        return np.column_stack(pieces)

    if len(lags) > 1 or len(diffs) > 1:
        raise CollapseError("several lags of a matrix or data frame are not translated")
    return _dispatch_columns(layout, x, one)


def _stack_named(x, lags, diffs, g, fill, take_log, rho, kind, logdiff, scale, power):
    column = _vector(x)
    codes, ng = _codes(g, column.shape[0])
    pieces = []
    names = []
    for lag in lags:
        for repeat in diffs:
            if kind == "diff":
                pieces.append(_difference(column, lag, repeat, codes, ng, rho, fill, take_log))
                names.append("D%d" % repeat if lag == 1 else "L%dD%d" % (lag, repeat))
            else:
                pieces.append(_growth(column, lag, repeat, codes, ng, fill, logdiff, scale, power))
                names.append("G%d" % repeat if lag == 1 else "L%dG%d" % (lag, repeat))
    if len(pieces) == 1:
        return Vec(pieces[0])
    return Mat(np.column_stack(pieces), columns=names)


def fdiff_default(x, n=1, diff=1, g=None, t=None, fill=np.nan, log=False, rho=1, stubs=True):
    if t is not None:
        raise CollapseError("a time variable is not translated")
    del stubs
    return _stack_named(x, _as_lags(n), _as_lags(diff), g, fill, log, rho, "diff", False, 100.0, 1.0)


def fdiff_matrix(x, n=1, diff=1, g=None, t=None, fill=np.nan, log=False, rho=1, stubs=None):
    if t is not None:
        raise CollapseError("a time variable is not translated")
    del stubs
    return _run_diff("matrix", x, n, diff, g, fill, log, rho, "diff")


def fdiff_data_frame(x, n=1, diff=1, g=None, t=None, fill=np.nan, log=False, rho=1, stubs=None):
    if t is not None:
        raise CollapseError("a time variable is not translated")
    del stubs
    return _run_diff("frame", x, n, diff, g, fill, log, rho, "diff")


def fdiff(x, n=1, diff=1, g=None, t=None, fill=np.nan, log=False, rho=1, stubs=True):
    if isinstance(x, dict):
        return fdiff_data_frame(x, n, diff, g, t, fill, log, rho, stubs)
    if _looks_matrix(x):
        return fdiff_matrix(x, n, diff, g, t, fill, log, rho, stubs)
    return fdiff_default(x, n, diff, g, t, fill, log, rho, stubs)


def fgrowth_default(x, n=1, diff=1, g=None, t=None, fill=np.nan, logdiff=False, scale=100, power=1, stubs=True):
    if t is not None:
        raise CollapseError("a time variable is not translated")
    del stubs
    return _stack_named(x, _as_lags(n), _as_lags(diff), g, fill, False, 1, "growth", logdiff, scale, power)


def fgrowth_matrix(x, n=1, diff=1, g=None, t=None, fill=np.nan, logdiff=False, scale=100, power=1, stubs=None):
    if t is not None:
        raise CollapseError("a time variable is not translated")
    del stubs
    return _run_diff("matrix", x, n, diff, g, fill, False, 1, "growth", logdiff, scale, power)


def fgrowth_data_frame(x, n=1, diff=1, g=None, t=None, fill=np.nan, logdiff=False, scale=100, power=1, stubs=None):
    if t is not None:
        raise CollapseError("a time variable is not translated")
    del stubs
    return _run_diff("frame", x, n, diff, g, fill, False, 1, "growth", logdiff, scale, power)


def fgrowth(x, n=1, diff=1, g=None, t=None, fill=np.nan, logdiff=False, scale=100, power=1, stubs=True):
    if isinstance(x, dict):
        return fgrowth_data_frame(x, n, diff, g, t, fill, logdiff, scale, power, stubs)
    if _looks_matrix(x):
        return fgrowth_matrix(x, n, diff, g, t, fill, logdiff, scale, power, stubs)
    return fgrowth_default(x, n, diff, g, t, fill, logdiff, scale, power, stubs)


def _center_scale(x, w, na_rm):
    x = np.asarray(x, dtype=np.float64)
    if w is None:
        if not na_rm and np.isnan(x).any():
            return np.nan, np.nan, np.zeros(x.shape[0], dtype=bool)
        mask = ~np.isnan(x) if na_rm else np.ones(x.shape[0], dtype=bool)
        kept = x[mask]
        if kept.size == 0:
            return np.nan, np.nan, mask
        mean = float(np.sum(kept) / kept.size)
        if kept.size < 2:
            return mean, np.nan, mask
        sd = math.sqrt(float(np.sum((kept - mean) ** 2) / (kept.size - 1)))
        return mean, sd, mask
    w = np.asarray(w, dtype=np.float64)
    if not na_rm and (np.isnan(x).any() or np.isnan(w).any()):
        return np.nan, np.nan, np.zeros(x.shape[0], dtype=bool)
    mask = (~np.isnan(x) & ~np.isnan(w) & (w != 0)) if na_rm else (w != 0)
    kept_x = x[mask]
    kept_w = w[mask]
    if kept_x.size == 0 or float(np.sum(kept_w)) == 0.0:
        return np.nan, np.nan, mask
    total = 0.0
    mean = 0.0
    moment = 0.0
    for value, weight in zip(kept_x[::-1], kept_w[::-1]):
        weight = float(weight)
        value = float(value)
        total += weight
        delta = value - mean
        mean += delta * (weight / total)
        moment += weight * delta * (value - mean)
    sd = math.sqrt(moment / (total - 1.0)) if total > 1.0 else np.nan
    return mean, sd, mask


def _scale_vector(x, g, w, na_rm, target_mean, target_sd):
    x = _vector(x)
    weights = None if w is None else _weights(w, x.shape[0], "length(x)")
    codes, ng = _codes(g, x.shape[0])
    out = np.full(x.shape[0], np.nan, dtype=np.float64)
    if codes is None:
        groups = [np.arange(x.shape[0])]
    else:
        groups = [np.flatnonzero(codes == i) for i in range(ng)]
    for index in groups:
        mean, sd, mask = _center_scale(x[index], None if weights is None else weights[index], na_rm)
        if math.isnan(sd) or sd == 0.0:
            continue
        local = np.full(index.shape[0], np.nan)
        local[mask] = (x[index][mask] - mean) / sd * target_sd + target_mean
        out[index] = local
    return out


def _within_vector(x, g, w, na_rm, theta, target_mean):
    x = _vector(x)
    weights = None if w is None else _weights(w, x.shape[0], "length(x)")
    codes, ng = _codes(g, x.shape[0])
    out = np.full(x.shape[0], np.nan, dtype=np.float64)
    if codes is None:
        groups = [np.arange(x.shape[0])]
    else:
        groups = [np.flatnonzero(codes == i) for i in range(ng)]
    for index in groups:
        mean, _sd, mask = _center_scale(x[index], None if weights is None else weights[index], na_rm)
        if math.isnan(mean):
            continue
        local = np.full(index.shape[0], np.nan)
        local[mask] = x[index][mask] - theta * mean + target_mean
        out[index] = local
    return out


def _between_vector(x, g, w, na_rm, fill):
    x = _vector(x)
    weights = None if w is None else _weights(w, x.shape[0], "length(x)")
    codes, ng = _codes(g, x.shape[0])
    out = np.full(x.shape[0], np.nan, dtype=np.float64)
    if codes is None:
        groups = [np.arange(x.shape[0])]
    else:
        groups = [np.flatnonzero(codes == i) for i in range(ng)]
    for index in groups:
        mean, _sd, mask = _center_scale(x[index], None if weights is None else weights[index], na_rm)
        if math.isnan(mean):
            continue
        if fill:
            out[index] = mean
        else:
            local = np.full(index.shape[0], np.nan)
            local[mask] = mean
            out[index] = local
    return out


def _run_adjust(kind, layout, x, g=None, w=None, na_rm=True, mean=0, sd=1, theta=1, fill=False):
    def one(column):
        if kind == "scale":
            return _scale_vector(column, g, w, na_rm, mean, sd)
        if kind == "within":
            return _within_vector(column, g, w, na_rm, theta, mean)
        return _between_vector(column, g, w, na_rm, fill)

    return _dispatch_columns(layout, x, one)


def fscale_default(x, g=None, w=None, na_rm=True, mean=0, sd=1):
    return _run_adjust("scale", "vector", x, g, w, na_rm, mean, sd)


def fscale_matrix(x, g=None, w=None, na_rm=True, mean=0, sd=1):
    return _run_adjust("scale", "matrix", x, g, w, na_rm, mean, sd)


def fscale_data_frame(x, g=None, w=None, na_rm=True, mean=0, sd=1):
    return _run_adjust("scale", "frame", x, g, w, na_rm, mean, sd)


def fscale(x, g=None, w=None, na_rm=True, mean=0, sd=1):
    if isinstance(x, dict):
        return fscale_data_frame(x, g, w, na_rm, mean, sd)
    if _looks_matrix(x):
        return fscale_matrix(x, g, w, na_rm, mean, sd)
    return fscale_default(x, g, w, na_rm, mean, sd)


def fwithin_default(x, g=None, w=None, na_rm=True, mean=0, theta=1):
    return _run_adjust("within", "vector", x, g, w, na_rm, mean, theta=theta)


def fwithin_matrix(x, g=None, w=None, na_rm=True, mean=0, theta=1):
    return _run_adjust("within", "matrix", x, g, w, na_rm, mean, theta=theta)


def fwithin_data_frame(x, g=None, w=None, na_rm=True, mean=0, theta=1):
    return _run_adjust("within", "frame", x, g, w, na_rm, mean, theta=theta)


def fwithin(x, g=None, w=None, na_rm=True, mean=0, theta=1):
    if isinstance(x, dict):
        return fwithin_data_frame(x, g, w, na_rm, mean, theta=theta)
    if _looks_matrix(x):
        return fwithin_matrix(x, g, w, na_rm, mean, theta=theta)
    return fwithin_default(x, g, w, na_rm, mean, theta=theta)


def fbetween_default(x, g=None, w=None, na_rm=True, fill=False):
    return _run_adjust("between", "vector", x, g, w, na_rm, fill=fill)


def fbetween_matrix(x, g=None, w=None, na_rm=True, fill=False):
    return _run_adjust("between", "matrix", x, g, w, na_rm, fill=fill)


def fbetween_data_frame(x, g=None, w=None, na_rm=True, fill=False):
    return _run_adjust("between", "frame", x, g, w, na_rm, fill=fill)


def fbetween(x, g=None, w=None, na_rm=True, fill=False):
    if isinstance(x, dict):
        return fbetween_data_frame(x, g, w, na_rm, fill=fill)
    if _looks_matrix(x):
        return fbetween_matrix(x, g, w, na_rm, fill=fill)
    return fbetween_default(x, g, w, na_rm, fill=fill)
