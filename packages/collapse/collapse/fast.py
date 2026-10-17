"""Fast grouped statistics from collapse.

The C++ in collapse is reached through Rcpp's evalCpp. This module is the
single-thread numeric path: vectors, matrices, and data frames. A data frame
is a dict of columns. Missing values are NaN. Group levels are sorted, and an
all-missing group stays missing unless fill is set on a sum.
"""

from __future__ import annotations

import math

import numpy as np

EPS = 10.0 * float(np.finfo(float).eps)

TIES = {
    "mean": 1,
    "min": 2,
    "max": 3,
    "q4": 4,
    "q5": 5,
    "q6": 6,
    "q7": 7,
    "q8": 8,
    "q9": 9,
}


class CollapseError(Exception):
    pass


class Vec:
    """A numeric vector. ``names`` is the R names attribute."""

    def __init__(self, values, names=None):
        self.values = np.asarray(values, dtype=np.float64).reshape(-1)
        self.names = None if names is None else [str(name) for name in names]

    def __repr__(self):
        return str(self)

    def __str__(self):
        vals = self.values
        if self.names:
            return "\n".join(f"{name} {_fmt(val)}" for name, val in zip(self.names, vals))
        if vals.size == 1:
            return _fmt(float(vals[0]))
        return " ".join(_fmt(val) for val in vals)


class Mat:
    """A numeric matrix stored row by row. Flattening follows R's column order."""

    def __init__(self, values, rows=None, columns=None):
        self.values = np.asarray(values, dtype=np.float64)
        self.rows = None if rows is None else [str(name) for name in rows]
        self.columns = None if columns is None else [str(name) for name in columns]

    def __repr__(self):
        return str(self)

    def __str__(self):
        values = self.values
        if values.ndim == 1:
            return str(Vec(values, self.columns))
        lines = []
        if self.columns:
            lines.append(" ".join(self.columns))
        for i in range(values.shape[0]):
            body = " ".join(_fmt(val) for val in values[i])
            if self.rows:
                body = f"{self.rows[i]} {body}"
            lines.append(body)
        return "\n".join(lines)


class Frame:
    """A data frame: a dict of columns, with optional row names."""

    def __init__(self, columns, rows=None):
        self.columns = {
            str(name): np.asarray(values, dtype=np.float64).reshape(-1)
            for name, values in columns.items()
        }
        self.rows = None if rows is None else [str(name) for name in rows]

    def __repr__(self):
        return str(self)

    def __str__(self):
        names = list(self.columns)
        lines = [" ".join(names)]
        nrow = 0 if not names else next(iter(self.columns.values())).shape[0]
        for i in range(nrow):
            body = " ".join(_fmt(self.columns[name][i]) for name in names)
            if self.rows:
                body = f"{self.rows[i]} {body}"
            lines.append(body)
        return "\n".join(lines)


def flat(obj):
    """Column-major numeric values, in the order R's as.numeric uses."""
    if isinstance(obj, Vec):
        return np.asarray(obj.values, dtype=np.float64).reshape(-1)
    if isinstance(obj, Mat):
        return np.asarray(obj.values, dtype=np.float64).ravel(order="F")
    if isinstance(obj, Frame):
        parts = [np.asarray(values, dtype=np.float64).reshape(-1) for values in obj.columns.values()]
        if not parts:
            return np.array([], dtype=np.float64)
        return np.concatenate(parts)
    return np.atleast_1d(np.asarray(obj, dtype=np.float64)).reshape(-1)


def _fmt(value):
    if isinstance(value, (float, np.floating)) and math.isnan(float(value)):
        return "NA"
    return format(float(value), ".10g")


def _reject(TRA):
    if TRA is not None:
        raise CollapseError("TRA is not translated")


def _vector(x):
    try:
        values = np.asarray(x, dtype=np.float64)
    except (TypeError, ValueError) as exc:
        raise CollapseError("x must be numeric") from exc
    if values.ndim == 0:
        values = values.reshape(1)
    if values.ndim != 1:
        raise CollapseError("expected a vector")
    return np.ascontiguousarray(values)


def _matrix(x):
    try:
        values = np.asarray(x, dtype=np.float64)
    except (TypeError, ValueError) as exc:
        raise CollapseError("x must be numeric") from exc
    if values.ndim != 2:
        raise CollapseError("expected a matrix")
    return np.ascontiguousarray(values)


def _frame(x):
    if not isinstance(x, dict):
        raise CollapseError("a data frame is a dict of columns")
    columns = {}
    nrow = None
    for name, column in x.items():
        values = _vector(column)
        if nrow is None:
            nrow = values.shape[0]
        elif values.shape[0] != nrow:
            raise CollapseError("columns must have the same length")
        columns[str(name)] = values
    return columns, 0 if nrow is None else nrow


def _looks_matrix(x):
    if isinstance(x, Mat):
        return True
    if isinstance(x, np.ndarray) and x.ndim == 2:
        return True
    if isinstance(x, (list, tuple)) and x and isinstance(x[0], (list, tuple, np.ndarray)):
        return True
    return False


def _missing(value):
    if value is None:
        return True
    if isinstance(value, (float, np.floating)) and math.isnan(float(value)):
        return True
    return False


def _level_name(value):
    if isinstance(value, (bool, np.bool_)):
        return "TRUE" if bool(value) else "FALSE"
    if isinstance(value, (int, np.integer)) and not isinstance(value, (bool, np.bool_)):
        return str(int(value))
    if isinstance(value, (float, np.floating)):
        number = float(value)
        if number.is_integer() and abs(number) < 2**53:
            return str(int(number))
        return repr(number)
    return str(value)


def _level_key(value):
    if isinstance(value, (bool, np.bool_)):
        return (0, 0, int(bool(value)))
    if isinstance(value, (int, np.integer)):
        return (0, 0, int(value))
    if isinstance(value, (float, np.floating)):
        return (0, 0, float(value))
    return (1, 0, str(value))


def factor(g):
    """Sorted group codes, with a trailing NA level when the group itself is missing."""
    if isinstance(g, dict):
        raise CollapseError("grouping by several columns is not translated")
    if isinstance(g, (list, tuple)) and g and isinstance(g[0], (list, tuple, dict)):
        raise CollapseError("grouping by several columns is not translated")
    raw = np.asarray(g, dtype=object)
    if raw.ndim == 2:
        raise CollapseError("grouping by several columns is not translated")
    if raw.ndim != 1:
        raise CollapseError("g must be a vector")
    missing = np.fromiter((_missing(value) for value in raw), dtype=bool, count=raw.shape[0])
    present = [value for value, flag in zip(raw.tolist(), missing) if not flag]
    levels = sorted(set(present), key=_level_key)
    index = {level: i for i, level in enumerate(levels)}
    codes = np.empty(raw.shape[0], dtype=np.intp)
    for i, value in enumerate(raw.tolist()):
        if not missing[i]:
            codes[i] = index[value]
    names = [_level_name(level) for level in levels]
    if missing.any():
        codes[missing] = len(names)
        names.append("NA")
    return codes, names


def _split(x, codes, ng, w):
    columns = [[] for _ in range(ng)]
    weights = None if w is None else [[] for _ in range(ng)]
    for i, code in enumerate(codes.tolist()):
        columns[code].append(x[i])
        if w is not None:
            weights[code].append(w[i])
    xs = [np.asarray(column, dtype=np.float64) for column in columns]
    if w is None:
        return xs, None
    return xs, [np.asarray(column, dtype=np.float64) for column in weights]


def _sum(x, w, na_rm, fill):
    narm = 0
    if na_rm:
        narm = 2 if fill else 1
    if x.size == 0:
        return 0.0 if narm != 1 else np.nan
    if w is None:
        if narm == 0:
            if np.isnan(x).any():
                return np.nan
            return float(np.sum(x))
        kept = x[~np.isnan(x)]
        if kept.size == 0:
            return 0.0 if narm == 2 else np.nan
        return float(np.sum(kept))
    if narm == 0:
        if np.isnan(x).any() or np.isnan(w).any():
            return np.nan
        return float(np.sum(x * w))
    mask = ~np.isnan(x) & ~np.isnan(w)
    if not mask.any():
        return 0.0 if narm == 2 else np.nan
    return float(np.sum(x[mask] * w[mask]))


def _mean(x, w, na_rm):
    if x.size == 0:
        return np.nan
    if w is None:
        if not na_rm:
            if np.isnan(x).any():
                return np.nan
            return float(np.sum(x) / x.size)
        kept = x[~np.isnan(x)]
        if kept.size == 0:
            return np.nan
        return float(np.sum(kept) / kept.size)
    if not na_rm:
        if np.isnan(x).any() or np.isnan(w).any():
            return np.nan
        total = float(np.sum(w))
        if total == 0.0:
            return np.nan
        return float(np.sum(x * w) / total)
    mask = ~np.isnan(x) & ~np.isnan(w)
    if not mask.any():
        return np.nan
    total = float(np.sum(w[mask]))
    if total == 0.0:
        return np.nan
    return float(np.sum(x[mask] * w[mask]) / total)


def _extreme(x, na_rm, larger):
    if x.size == 0:
        return np.nan
    if not na_rm:
        if np.isnan(x).any():
            return np.nan
        kept = x
    else:
        kept = x[~np.isnan(x)]
        if kept.size == 0:
            return np.nan
    return float(np.max(kept) if larger else np.min(kept))


def _nobs(x):
    return float(np.count_nonzero(~np.isnan(x)))


def _prod(x, w, na_rm):
    if x.size == 0:
        return np.nan
    if w is None:
        if not na_rm:
            if np.isnan(x).any():
                return np.nan
            return float(np.prod(x))
        kept = x[~np.isnan(x)]
        if kept.size == 0:
            return np.nan
        return float(np.prod(kept))
    if not na_rm:
        if np.isnan(x).any() or np.isnan(w).any():
            return np.nan
        return float(np.prod(x * w))
    mask = ~np.isnan(x) & ~np.isnan(w)
    if not mask.any():
        return np.nan
    return float(np.prod(x[mask] * w[mask]))


def _moments(x, w, na_rm, sd, stable):
    if w is not None and (not na_rm) and (np.isnan(x).any() or np.isnan(w).any()):
        return np.nan
    if w is None and (not na_rm) and np.isnan(x).any():
        return np.nan
    if w is None:
        kept_x = x if not na_rm else x[~np.isnan(x)]
        kept_w = None
    else:
        mask = np.ones(x.shape[0], dtype=bool) if not na_rm else (~np.isnan(x) & ~np.isnan(w))
        if na_rm:
            mask = mask & (w != 0)
        elif w is not None:
            # Zero weights are skipped. A missing weight has already returned.
            mask = ~np.isnan(x) & ~np.isnan(w) & (w != 0) if na_rm else (w != 0)
        kept_x = x[mask]
        kept_w = w[mask]
    if kept_x.size < 2 and kept_w is None:
        return np.nan
    if kept_w is None:
        if not stable:
            total = float(np.sum(kept_x))
            squares = float(np.sum(kept_x * kept_x))
            count = kept_x.size
            moment = (squares - (total / count) ** 2 * count) / (count - 1)
        else:
            count = 0.0
            mean = 0.0
            moment = 0.0
            for value in kept_x[::-1]:
                count += 1.0
                delta = float(value) - mean
                mean += delta / count
                moment += delta * (float(value) - mean)
            moment /= count - 1.0
    else:
        if kept_x.size == 0:
            return np.nan
        total_w = 0.0
        mean = 0.0
        moment = 0.0
        pairs = list(zip(kept_x[::-1], kept_w[::-1]))
        if not stable:
            total = 0.0
            squares = 0.0
            weight = 0.0
            for value, wt in pairs:
                total += float(value) * float(wt)
                squares += float(value) * float(value) * float(wt)
                weight += float(wt)
            if weight == 0.0:
                return np.nan
            moment = (squares - (total / weight) ** 2 * weight) / (weight - 1.0)
        else:
            for value, wt in pairs:
                wt = float(wt)
                value = float(value)
                total_w += wt
                delta = value - mean
                mean += delta * (wt / total_w)
                moment += wt * delta * (value - mean)
            moment /= total_w - 1.0
    if sd:
        moment = math.sqrt(moment) if moment >= 0.0 else np.nan
    if isinstance(moment, float) and math.isnan(moment):
        return np.nan
    return float(moment)


def _probability(n, length, ng):
    q = float(n)
    override = None
    if math.isnan(q) or q <= 0.0 or q == 1.0:
        raise CollapseError(
            "n needs to be between 0 and 1, or between 1 and length(x). Use fmin and fmax for minima and maxima."
        )
    if q > 1.0:
        override = "min"
        span = length / ng
        if q >= span:
            raise CollapseError(
                "n needs to be between 0 and 1, or between 1 and length(x). Use fmin and fmax for minima and maxima."
            )
        q = (q - 1.0) / (span - 1.0)
    return q, override


def _index(n, q, ret):
    if ret in (7, 1, 2):
        return (n - 1) * q
    if ret == 3:
        return n * q
    if ret == 4:
        return n * q - 1.0
    if ret == 5:
        return n * q - 0.5
    if ret == 6:
        return (n + 1) * q - 1.0
    if ret == 8:
        return (n + 1.0 / 3.0) * q - 2.0 / 3.0
    if ret == 9:
        return (n + 0.25) * q - 5.0 / 8.0
    raise CollapseError(f"unknown ties option: {ret}")


def _unweighted_nth(x, q, ties):
    ordered = np.sort(np.asarray(x, dtype=np.float64))
    n = int(ordered.size)
    if n == 0:
        return np.nan
    if n == 1:
        return float(ordered[0])
    ret = TIES[ties]
    h = _index(n, q, ret)
    if h < 0.0:
        return float(ordered[0])
    elem = int(math.floor(h))
    if elem >= n:
        elem = n - 1
    frac = h - math.floor(h)
    left = float(ordered[elem])
    if (ret < 4 and (ret != 1 or n % 2 == 1)) or elem == n - 1 or frac <= 0.0:
        return left
    right = float(ordered[elem + 1])
    if ret == 1:
        return (left + right) / 2.0
    return left + frac * (right - left)


def _add_weighted_offset(h, q, ret):
    if ret == 7:
        return h + 1.0 - q
    if ret == 5:
        return h + 0.5
    if ret == 6:
        return h + q
    if ret == 8:
        return h + (1.0 / 3.0) * (q + 1.0)
    if ret == 9:
        return h + 0.25 * q + 0.375
    return h


def _weighted_nth(x, w, q, ties):
    ordered = np.argsort(np.asarray(x, dtype=np.float64), kind="mergesort")
    x = np.asarray(x, dtype=np.float64)[ordered]
    w = np.asarray(w, dtype=np.float64)[ordered]
    n = int(x.size)
    if n == 0:
        return np.nan
    if np.any(w < 0):
        raise CollapseError("Weights must be positive or zero")
    total = float(np.sum(w))
    if math.isnan(total):
        raise CollapseError("Missing weights in order statistics are currently only supported if x is also missing")
    h = q * total
    ret = TIES[ties]
    if ret < 3:
        wsum = float(w[0])
        k = 1
        while k < n and wsum < h:
            wsum += float(w[k])
            k += 1
        left = float(x[k - 1])
        if ret == 2 or wsum > h + EPS or k >= n:
            return left
        right = float(x[k])
        count = 2.0
        while k < n - 1 and float(w[k]) == 0.0:
            k += 1
            right += float(x[k])
            count += 1.0
        return (left + right) / count
    wsum = float(w[0])
    k = 1
    limit = h + EPS
    while k < n and wsum <= limit:
        wsum += float(w[k])
        k += 1
    if ret == 3:
        return float(x[k - 1])
    k -= 1
    wsum -= float(w[k])
    h = (k - 1) + (h - wsum) / float(w[k])
    h = _add_weighted_offset(h, q, ret)
    j = int(math.floor(h))
    frac = h - j
    if j >= n - 1 or frac < EPS:
        return float(x[min(max(j, 0), n - 1)])
    return (1.0 - frac) * float(x[j]) + frac * float(x[j + 1])


def _sample(x, w, na_rm):
    if w is None:
        if not na_rm and np.isnan(x).any():
            return None
        if na_rm:
            return x[~np.isnan(x)], None
        return x, None
    if not na_rm and (np.isnan(x).any() or np.isnan(w).any()):
        return None
    mask = ~np.isnan(x) & ~np.isnan(w) if na_rm else np.ones(x.shape[0], dtype=bool)
    return x[mask], w[mask]


def _nth(x, w, na_rm, q, ties):
    sampled = _sample(x, w, na_rm)
    if sampled is None:
        return np.nan
    values, weights = sampled
    if weights is None:
        return _unweighted_nth(values, q, ties)
    return _weighted_nth(values, weights, q, ties)


def _endpoint(x, na_rm, last):
    if x.size == 0:
        return np.nan
    seq = x[::-1] if last else x
    if not na_rm:
        return float(seq[0])
    for value in seq:
        if not math.isnan(float(value)):
            return float(value)
    return np.nan


def _one(kind, x, w, na_rm, fill, stable, q, ties):
    x = np.asarray(x, dtype=np.float64).reshape(-1)
    if w is not None:
        w = np.asarray(w, dtype=np.float64).reshape(-1)
    if kind == "sum":
        return _sum(x, w, na_rm, fill)
    if kind == "mean":
        return _mean(x, w, na_rm)
    if kind == "min":
        return _extreme(x, na_rm, False)
    if kind == "max":
        return _extreme(x, na_rm, True)
    if kind == "nobs":
        return _nobs(x)
    if kind == "prod":
        return _prod(x, w, na_rm)
    if kind == "sd":
        return _moments(x, w, na_rm, True, stable)
    if kind == "var":
        return _moments(x, w, na_rm, False, stable)
    if kind in ("nth", "median"):
        return _nth(x, w, na_rm, q, ties)
    if kind == "first":
        return _endpoint(x, na_rm, False)
    if kind == "last":
        return _endpoint(x, na_rm, True)
    raise CollapseError(f"unknown statistic: {kind}")


def _grouped_values(kind, x, codes, ng, w, na_rm, fill, stable, q, ties):
    parts, weights = _split(x, codes, ng, w)
    return np.array(
        [
            _one(
                kind,
                parts[i],
                None if weights is None else weights[i],
                na_rm,
                fill,
                stable,
                q,
                ties,
            )
            for i in range(ng)
        ],
        dtype=np.float64,
    )


def _prepare(kind, n, ties, length, ng):
    if kind == "median":
        return 0.5, ties or "mean"
    if kind != "nth":
        return n, ties
    q, override = _probability(n, length, max(ng, 1))
    if override:
        ties = override
    return q, ties or "q7"


def _weights(w, n, what):
    if w is None:
        return None
    weights = _vector(w)
    if weights.shape[0] != n:
        raise CollapseError(f"length(w) must match {what}")
    return weights


def _go(kind, layout, x, g=None, w=None, TRA=None, na_rm=True, use_g_names=True, fill=False,
        nthreads=1, stable_algo=True, n=0.5, ties=None, drop=True):
    del nthreads  # the single-thread result matches collapse at nthreads = 1
    if TRA is not None:
        stat = _go(
            kind, layout, x, g=g, w=w, TRA=None, na_rm=na_rm, use_g_names=False, fill=fill,
            stable_algo=stable_algo, n=n, ties=ties, drop=False,
        )
        from collapse.rest import apply_tra
        return apply_tra(x, stat, TRA, g, layout)
    if layout == "vector":
        values = _vector(x)
        weights = _weights(w, values.shape[0], "length(x)")
        if g is None:
            if values.size == 0:
                return Vec([])
            q, ties = _prepare(kind, n, ties, values.shape[0], 1)
            return Vec([_one(kind, values, weights, na_rm, fill, stable_algo, q, ties)])
        codes, names = factor(g)
        if codes.shape[0] != values.shape[0]:
            raise CollapseError("length(g) must match length(x)")
        q, ties = _prepare(kind, n, ties, values.shape[0], len(names))
        reduced = _grouped_values(kind, values, codes, len(names), weights, na_rm, fill, stable_algo, q, ties)
        return Vec(reduced, names if use_g_names else None)
    if layout == "matrix":
        if isinstance(x, Mat):
            values = np.asarray(x.values, dtype=np.float64)
            columns = x.columns
        else:
            values = _matrix(x)
            columns = None
        weights = _weights(w, values.shape[0], "nrow(x)")
        if g is None:
            if values.shape[0] == 0:
                return Vec([]) if drop else Mat(np.empty((0, values.shape[1])), columns=columns)
            q, ties = _prepare(kind, n, ties, values.shape[0], 1)
            reduced = np.array(
                [_one(kind, values[:, j], weights, na_rm, fill, stable_algo, q, ties) for j in range(values.shape[1])],
                dtype=np.float64,
            )
            if drop:
                return Vec(reduced, columns)
            return Mat(reduced.reshape(1, -1), columns=columns)
        codes, names = factor(g)
        if codes.shape[0] != values.shape[0]:
            raise CollapseError("length(g) must match nrow(x)")
        q, ties = _prepare(kind, n, ties, values.shape[0], len(names))
        reduced = np.column_stack(
            [
                _grouped_values(kind, values[:, j], codes, len(names), weights, na_rm, fill, stable_algo, q, ties)
                for j in range(values.shape[1])
            ]
        )
        return Mat(reduced, rows=names if use_g_names else None, columns=columns)
    columns, nrow = _frame(x)
    weights = _weights(w, nrow, "nrow(x)")
    if g is None:
        if nrow == 0:
            return Vec([]) if drop else Frame({name: np.array([]) for name in columns})
        q, ties = _prepare(kind, n, ties, nrow, 1)
        reduced = {
            name: _one(kind, column, weights, na_rm, fill, stable_algo, q, ties)
            for name, column in columns.items()
        }
        if drop:
            return Vec(list(reduced.values()), list(reduced))
        return Frame({name: [value] for name, value in reduced.items()}, rows=["1"])
    codes, names = factor(g)
    if codes.shape[0] != nrow:
        raise CollapseError("length(g) must match nrow(x)")
    q, ties = _prepare(kind, n, ties, nrow, len(names))
    reduced = {
        name: _grouped_values(kind, column, codes, len(names), weights, na_rm, fill, stable_algo, q, ties)
        for name, column in columns.items()
    }
    return Frame(reduced, rows=names if use_g_names else None)


def _auto(kind, x, **kwargs):
    if isinstance(x, dict):
        return _go(kind, "frame", x, **kwargs)
    if _looks_matrix(x):
        return _go(kind, "matrix", x, **kwargs)
    kwargs.pop("drop", None)
    return _go(kind, "vector", x, **kwargs)


def fsum_default(x, g=None, w=None, TRA=None, na_rm=True, use_g_names=True, fill=False, nthreads=1):
    return _go("sum", "vector", x, g=g, w=w, TRA=TRA, na_rm=na_rm, use_g_names=use_g_names, fill=fill, nthreads=nthreads)


def fsum_matrix(x, g=None, w=None, TRA=None, na_rm=True, use_g_names=True, drop=True, fill=False, nthreads=1):
    return _go("sum", "matrix", x, g=g, w=w, TRA=TRA, na_rm=na_rm, use_g_names=use_g_names, drop=drop, fill=fill, nthreads=nthreads)


def fsum_data_frame(x, g=None, w=None, TRA=None, na_rm=True, use_g_names=True, drop=True, fill=False, nthreads=1):
    return _go("sum", "frame", x, g=g, w=w, TRA=TRA, na_rm=na_rm, use_g_names=use_g_names, drop=drop, fill=fill, nthreads=nthreads)


def fsum(x, g=None, w=None, TRA=None, na_rm=True, use_g_names=True, drop=True, fill=False, nthreads=1):
    return _auto("sum", x, g=g, w=w, TRA=TRA, na_rm=na_rm, use_g_names=use_g_names, drop=drop, fill=fill, nthreads=nthreads)


def fprod_default(x, g=None, w=None, TRA=None, na_rm=True, use_g_names=True, nthreads=1):
    return _go("prod", "vector", x, g=g, w=w, TRA=TRA, na_rm=na_rm, use_g_names=use_g_names, nthreads=nthreads)


def fprod_matrix(x, g=None, w=None, TRA=None, na_rm=True, use_g_names=True, drop=True, nthreads=1):
    return _go("prod", "matrix", x, g=g, w=w, TRA=TRA, na_rm=na_rm, use_g_names=use_g_names, drop=drop, nthreads=nthreads)


def fprod_data_frame(x, g=None, w=None, TRA=None, na_rm=True, use_g_names=True, drop=True, nthreads=1):
    return _go("prod", "frame", x, g=g, w=w, TRA=TRA, na_rm=na_rm, use_g_names=use_g_names, drop=drop, nthreads=nthreads)


def fprod(x, g=None, w=None, TRA=None, na_rm=True, use_g_names=True, drop=True, nthreads=1):
    return _auto("prod", x, g=g, w=w, TRA=TRA, na_rm=na_rm, use_g_names=use_g_names, drop=drop, nthreads=nthreads)


def fmean_default(x, g=None, w=None, TRA=None, na_rm=True, use_g_names=True, nthreads=1):
    return _go("mean", "vector", x, g=g, w=w, TRA=TRA, na_rm=na_rm, use_g_names=use_g_names, nthreads=nthreads)


def fmean_matrix(x, g=None, w=None, TRA=None, na_rm=True, use_g_names=True, drop=True, nthreads=1):
    return _go("mean", "matrix", x, g=g, w=w, TRA=TRA, na_rm=na_rm, use_g_names=use_g_names, drop=drop, nthreads=nthreads)


def fmean_data_frame(x, g=None, w=None, TRA=None, na_rm=True, use_g_names=True, drop=True, nthreads=1):
    return _go("mean", "frame", x, g=g, w=w, TRA=TRA, na_rm=na_rm, use_g_names=use_g_names, drop=drop, nthreads=nthreads)


def fmean(x, g=None, w=None, TRA=None, na_rm=True, use_g_names=True, drop=True, nthreads=1):
    return _auto("mean", x, g=g, w=w, TRA=TRA, na_rm=na_rm, use_g_names=use_g_names, drop=drop, nthreads=nthreads)


def _extreme_family(kind):
    def default(x, g=None, TRA=None, na_rm=True, use_g_names=True):
        return _go(kind, "vector", x, g=g, TRA=TRA, na_rm=na_rm, use_g_names=use_g_names)

    def matrix(x, g=None, TRA=None, na_rm=True, use_g_names=True, drop=True):
        return _go(kind, "matrix", x, g=g, TRA=TRA, na_rm=na_rm, use_g_names=use_g_names, drop=drop)

    def data_frame(x, g=None, TRA=None, na_rm=True, use_g_names=True, drop=True):
        return _go(kind, "frame", x, g=g, TRA=TRA, na_rm=na_rm, use_g_names=use_g_names, drop=drop)

    def generic(x, g=None, TRA=None, na_rm=True, use_g_names=True, drop=True):
        return _auto(kind, x, g=g, TRA=TRA, na_rm=na_rm, use_g_names=use_g_names, drop=drop)

    return default, matrix, data_frame, generic


fmin_default, fmin_matrix, fmin_data_frame, fmin = _extreme_family("min")
fmax_default, fmax_matrix, fmax_data_frame, fmax = _extreme_family("max")
ffirst_default, ffirst_matrix, ffirst_data_frame, ffirst = _extreme_family("first")
flast_default, flast_matrix, flast_data_frame, flast = _extreme_family("last")


def fnobs_default(x, g=None, TRA=None, use_g_names=True):
    return _go("nobs", "vector", x, g=g, TRA=TRA, use_g_names=use_g_names)


def fnobs_matrix(x, g=None, TRA=None, use_g_names=True, drop=True):
    return _go("nobs", "matrix", x, g=g, TRA=TRA, use_g_names=use_g_names, drop=drop)


def fnobs_data_frame(x, g=None, TRA=None, use_g_names=True, drop=True):
    return _go("nobs", "frame", x, g=g, TRA=TRA, use_g_names=use_g_names, drop=drop)


def fnobs(x, g=None, TRA=None, use_g_names=True, drop=True):
    return _auto("nobs", x, g=g, TRA=TRA, use_g_names=use_g_names, drop=drop)


def fNobs_default(x, g=None, TRA=None, use_g_names=True):
    return fnobs_default(x, g=g, TRA=TRA, use_g_names=use_g_names)


def fNobs_matrix(x, g=None, TRA=None, use_g_names=True, drop=True):
    return fnobs_matrix(x, g=g, TRA=TRA, use_g_names=use_g_names, drop=drop)


def fNobs_data_frame(x, g=None, TRA=None, use_g_names=True, drop=True):
    return fnobs_data_frame(x, g=g, TRA=TRA, use_g_names=use_g_names, drop=drop)


def fNobs(x, g=None, TRA=None, use_g_names=True, drop=True):
    return fnobs(x, g=g, TRA=TRA, use_g_names=use_g_names, drop=drop)


def _var_family(kind):
    def default(x, g=None, w=None, TRA=None, na_rm=True, use_g_names=True, stable_algo=True):
        return _go(kind, "vector", x, g=g, w=w, TRA=TRA, na_rm=na_rm, use_g_names=use_g_names, stable_algo=stable_algo)

    def matrix(x, g=None, w=None, TRA=None, na_rm=True, use_g_names=True, drop=True, stable_algo=True):
        return _go(kind, "matrix", x, g=g, w=w, TRA=TRA, na_rm=na_rm, use_g_names=use_g_names, drop=drop, stable_algo=stable_algo)

    def data_frame(x, g=None, w=None, TRA=None, na_rm=True, use_g_names=True, drop=True, stable_algo=True):
        return _go(kind, "frame", x, g=g, w=w, TRA=TRA, na_rm=na_rm, use_g_names=use_g_names, drop=drop, stable_algo=stable_algo)

    def generic(x, g=None, w=None, TRA=None, na_rm=True, use_g_names=True, drop=True, stable_algo=True):
        return _auto(kind, x, g=g, w=w, TRA=TRA, na_rm=na_rm, use_g_names=use_g_names, drop=drop, stable_algo=stable_algo)

    return default, matrix, data_frame, generic


fsd_default, fsd_matrix, fsd_data_frame, fsd = _var_family("sd")
fvar_default, fvar_matrix, fvar_data_frame, fvar = _var_family("var")


def fnth_default(x, n=0.5, g=None, w=None, TRA=None, na_rm=True, use_g_names=True, ties="q7", nthreads=1):
    return _go("nth", "vector", x, g=g, w=w, TRA=TRA, na_rm=na_rm, use_g_names=use_g_names, n=n, ties=ties, nthreads=nthreads)


def fnth_matrix(x, n=0.5, g=None, w=None, TRA=None, na_rm=True, use_g_names=True, drop=True, ties="q7", nthreads=1):
    return _go("nth", "matrix", x, g=g, w=w, TRA=TRA, na_rm=na_rm, use_g_names=use_g_names, drop=drop, n=n, ties=ties, nthreads=nthreads)


def fnth_data_frame(x, n=0.5, g=None, w=None, TRA=None, na_rm=True, use_g_names=True, drop=True, ties="q7", nthreads=1):
    return _go("nth", "frame", x, g=g, w=w, TRA=TRA, na_rm=na_rm, use_g_names=use_g_names, drop=drop, n=n, ties=ties, nthreads=nthreads)


def fnth(x, n=0.5, g=None, w=None, TRA=None, na_rm=True, use_g_names=True, drop=True, ties="q7", nthreads=1):
    return _auto("nth", x, g=g, w=w, TRA=TRA, na_rm=na_rm, use_g_names=use_g_names, drop=drop, n=n, ties=ties, nthreads=nthreads)


def fmedian_default(x, g=None, w=None, TRA=None, na_rm=True, use_g_names=True, ties="mean", nthreads=1):
    return _go("median", "vector", x, g=g, w=w, TRA=TRA, na_rm=na_rm, use_g_names=use_g_names, ties=ties, nthreads=nthreads)


def fmedian_matrix(x, g=None, w=None, TRA=None, na_rm=True, use_g_names=True, drop=True, ties="mean", nthreads=1):
    return _go("median", "matrix", x, g=g, w=w, TRA=TRA, na_rm=na_rm, use_g_names=use_g_names, drop=drop, ties=ties, nthreads=nthreads)


def fmedian_data_frame(x, g=None, w=None, TRA=None, na_rm=True, use_g_names=True, drop=True, ties="mean", nthreads=1):
    return _go("median", "frame", x, g=g, w=w, TRA=TRA, na_rm=na_rm, use_g_names=use_g_names, drop=drop, ties=ties, nthreads=nthreads)


def fmedian(x, g=None, w=None, TRA=None, na_rm=True, use_g_names=True, drop=True, ties="mean", nthreads=1):
    return _auto("median", x, g=g, w=w, TRA=TRA, na_rm=na_rm, use_g_names=use_g_names, drop=drop, ties=ties, nthreads=nthreads)
