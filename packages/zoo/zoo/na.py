"""Missing-value fillers from zoo.

Numeric results follow the installed zoo 1.9-1 methods. Linear interpolation
follows ``stats::approx``. Cubic interpolation follows ``stats::splinefun``
(``fmm`` by default). ``na.StructTS`` follows ``stats::StructTS``: a basic
structural model, ``KalmanLike`` / ``KalmanSmooth``, and ``L-BFGS-B``.
"""

from __future__ import annotations

import math
import warnings
from typing import Any

import numpy as np

from zoo.series import Zoo

# R's NA_real_: the quiet NaN whose low 32 bits are 1954.
_NA_BITS = np.uint64(0x7FF00000000007A2)
_NA = np.array([_NA_BITS]).view(np.float64)[0]


def _na_array(n: int) -> np.ndarray:
    out = np.empty(int(n), dtype=np.float64)
    out.view(np.uint64)[:] = _NA_BITS
    return out


def _is_missing(value: Any) -> bool:
    try:
        return bool(math.isnan(float(value)))
    except (TypeError, ValueError):
        return False


def _as_float_vector(data: Any) -> np.ndarray:
    array = np.asarray(data, dtype=np.float64)
    if array.ndim == 0:
        array = array.reshape(1)
    return array


def _core(object: Any) -> np.ndarray:
    if isinstance(object, Zoo):
        return _as_float_vector(object.data) if np.asarray(object.data).ndim < 2 else np.asarray(object.data, dtype=np.float64)
    array = np.asarray(object)
    if array.dtype.kind not in "iufc" and array.dtype != object:
        return array
    if array.dtype.kind in "iufc":
        return np.asarray(array, dtype=np.float64)
    return array


def _nrow(object: Any) -> int:
    if isinstance(object, Zoo):
        return len(object)
    array = np.asarray(object)
    if array.ndim == 0:
        return 1
    return int(array.shape[0])


def _index_of(object: Any) -> np.ndarray:
    if isinstance(object, Zoo):
        return np.asarray(object.index, dtype=np.float64).reshape(-1)
    return np.arange(1, _nrow(object) + 1, dtype=np.float64)


def _copy_zoo(object: Zoo, data: np.ndarray, index: Any | None = None) -> Zoo:
    return Zoo(
        np.array(data, dtype=np.float64, order="F", copy=True),
        object.index if index is None else index,
        frequency=object.frequency,
        regular=object.regular,
    )


def _subset_index(index: Any, keep: np.ndarray) -> Any:
    idx = np.asarray(index)
    if idx.ndim == 0:
        return index
    return idx[np.asarray(keep)]


def _match_arg(arg: Any, choices: list[str]) -> str:
    if arg is None:
        return choices[0]
    text = str(arg)
    exact = [choice for choice in choices if choice == text]
    if exact:
        return exact[0]
    hits = [choice for choice in choices if choice.startswith(text)]
    if len(hits) == 1:
        return hits[0]
    quoted = ", ".join(repr(choice) for choice in choices)
    raise ValueError(f"'{text}' should be one of {quoted}")


def _rle(mask: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    if len(mask) == 0:
        return np.array([], dtype=bool), np.array([], dtype=int)
    change = np.flatnonzero(mask[1:] != mask[:-1]) + 1
    bounds = np.concatenate(([0], change, [len(mask)]))
    values = mask[bounds[:-1]]
    lengths = np.diff(bounds)
    return values, lengths


def _fill_short_gaps(x: np.ndarray, fill: np.ndarray, maxgap: float) -> np.ndarray:
    """Copy ``fill`` into NA runs of ``x`` that are no longer than ``maxgap``."""
    x = np.array(x, dtype=np.float64, copy=True)
    fill = np.asarray(fill, dtype=np.float64)
    if maxgap <= 0:
        return x
    if maxgap >= len(x):
        return np.array(fill, dtype=np.float64, copy=True)
    values, lengths = _rle(np.isnan(x))
    values = values.copy()
    values[lengths > maxgap] = False
    naok = np.repeat(values, lengths)
    x[naok] = fill[naok]
    return x


def _sample_variance(y: np.ndarray) -> float:
    observed = y[~np.isnan(y)]
    if len(observed) < 2:
        return float("nan")
    mean = float(np.sum(observed) / len(observed))
    return float(np.sum((observed - mean) ** 2) / (len(observed) - 1))


# ---------------------------------------------------------------------------
# stats::approx and stats::splinefun
# ---------------------------------------------------------------------------


def _regularize(x: np.ndarray, y: np.ndarray, ties: Any = None) -> tuple[np.ndarray, np.ndarray]:
    x = np.asarray(x, dtype=np.float64).reshape(-1)
    y = np.asarray(y, dtype=np.float64).reshape(-1)
    if len(x) != len(y):
        raise ValueError("x and y must have the same length")
    keep = ~(np.isnan(x) | np.isnan(y))
    x = x[keep]
    y = y[keep]
    if len(x) == 0:
        return x, y
    order = np.argsort(x, kind="mergesort")
    x = x[order]
    y = y[order]
    if ties is None:
        ties = "mean"
    # Collapse exact ties. R's default ties = mean.
    if len(x) >= 2 and np.any(x[1:] == x[:-1]):
        uniq = []
        vals = []
        start = 0
        for i in range(1, len(x) + 1):
            if i == len(x) or x[i] != x[start]:
                uniq.append(x[start])
                block = y[start:i]
                if ties == "mean" or ties is None:
                    vals.append(float(np.sum(block) / len(block)))
                elif callable(ties):
                    vals.append(float(ties(block)))
                else:
                    vals.append(float(np.sum(block) / len(block)))
                start = i
        x = np.asarray(uniq, dtype=np.float64)
        y = np.asarray(vals, dtype=np.float64)
    return x, y


def _approx1(v: float, x: np.ndarray, y: np.ndarray, method: int, yleft: float, yright: float, f: float) -> float:
    n = len(x)
    if n == 0:
        return float("nan")
    if v < x[0]:
        return yleft
    if v > x[-1]:
        return yright
    i = 0
    j = n - 1
    while i < j - 1:
        ij = (i + j) // 2
        if v < x[ij]:
            j = ij
        else:
            i = ij
    if v == x[j]:
        return float(y[j])
    if v == x[i]:
        return float(y[i])
    if method == 1:
        return float(y[i] + (y[j] - y[i]) * ((v - x[i]) / (x[j] - x[i])))
    return float(y[i] * (1.0 - f) + y[j] * f)


def approx(
    x: Any,
    y: Any = None,
    xout: Any = None,
    method: str = "linear",
    n: int = 50,
    yleft: Any = None,
    yright: Any = None,
    rule: Any = 1,
    f: float = 0.0,
    ties: Any = None,
    na_rm: bool = True,
) -> np.ndarray:
    """``stats::approx`` for the ``y`` values at ``xout``. Returns only ``y``."""
    del n, na_rm  # na.approx always supplies xout; n is not used
    method_index = {"linear": 1, "constant": 2}.get(str(method), None)
    if method_index is None:
        # unique prefix, as pmatch
        hits = [name for name in ("linear", "constant") if name.startswith(str(method))]
        if len(hits) != 1:
            raise ValueError("invalid interpolation method")
        method_index = 1 if hits[0] == "linear" else 2
    x_arr, y_arr = _regularize(np.asarray(x, dtype=np.float64), np.asarray(y, dtype=np.float64), ties)
    if len(x_arr) < (2 if method_index == 1 else 1):
        raise ValueError("need at least two non-NA values to interpolate")
    rule_arr = np.asarray(rule, dtype=float).reshape(-1)
    if len(rule_arr) == 1:
        rule_arr = np.array([rule_arr[0], rule_arr[0]])
    if yleft is None:
        yleft = _NA if rule_arr[0] == 1 else float(y_arr[0])
    if yright is None:
        yright = _NA if rule_arr[1] == 1 else float(y_arr[-1])
    if xout is None:
        raise ValueError("xout is required")
    xout_arr = np.asarray(xout, dtype=np.float64).reshape(-1)
    out = np.empty(len(xout_arr), dtype=np.float64)
    for i, value in enumerate(xout_arr):
        if math.isnan(float(value)):
            out[i] = _NA
        else:
            out[i] = _approx1(float(value), x_arr, y_arr, method_index, float(yleft) if not _is_missing(yleft) else _NA, float(yright) if not _is_missing(yright) else _NA, float(f))
    # Restore NA payloads that float() may have stripped.
    for i, value in enumerate(xout_arr):
        if math.isnan(float(value)) or (out[i] != out[i]):
            # Re-evaluate edges so rule-1 NA keeps R's payload.
            pass
    out_bits = out.view(np.uint64)
    for i, value in enumerate(xout_arr):
        v = float(value)
        if math.isnan(v) or math.isnan(float(out[i])):
            out_bits[i] = _NA_BITS
    return out


def _fmm_spline(x: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Forsythe–Malcolm–Moler coefficients stored as R's b, c, d."""
    n = len(x)
    b = np.zeros(n)
    c = np.zeros(n)
    d = np.zeros(n)
    if n < 2:
        return b, c, d
    if n == 2:
        slope = (y[1] - y[0]) / (x[1] - x[0])
        b[:] = slope
        return b, c, d
    nm1 = n - 1
    d[0] = x[1] - x[0]
    c[1] = (y[1] - y[0]) / d[0]
    for i in range(1, nm1):
        d[i] = x[i + 1] - x[i]
        b[i] = 2.0 * (d[i - 1] + d[i])
        c[i + 1] = (y[i + 1] - y[i]) / d[i]
        c[i] = c[i + 1] - c[i]
    b[0] = -d[0]
    b[nm1] = -d[n - 2]
    c[0] = 0.0
    c[nm1] = 0.0
    if n != 3:
        c[0] = c[2] / (x[3] - x[1]) - c[1] / (x[2] - x[0])
        c[nm1] = c[n - 2] / (x[nm1] - x[n - 3]) - c[n - 3] / (x[n - 2] - x[n - 4])
        c[0] = c[0] * d[0] * d[0] / (x[3] - x[0])
        c[nm1] = -c[nm1] * d[n - 2] * d[n - 2] / (x[nm1] - x[n - 4])
    for i in range(1, n):
        t = d[i - 1] / b[i - 1]
        b[i] = b[i] - t * d[i - 1]
        c[i] = c[i] - t * c[i - 1]
    c[nm1] = c[nm1] / b[nm1]
    for i in range(n - 2, -1, -1):
        c[i] = (c[i] - d[i] * c[i + 1]) / b[i]
    b[nm1] = (y[nm1] - y[n - 2]) / d[n - 2] + d[n - 2] * (c[n - 2] + 2.0 * c[nm1])
    for i in range(nm1):
        b[i] = (y[i + 1] - y[i]) / d[i] - d[i] * (c[i + 1] + 2.0 * c[i])
        d[i] = (c[i + 1] - c[i]) / d[i]
        c[i] = 3.0 * c[i]
    c[nm1] = 3.0 * c[nm1]
    d[nm1] = d[n - 2]
    return b, c, d


def _natural_spline(x: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    n = len(x)
    b = np.zeros(n)
    c = np.zeros(n)
    d = np.zeros(n)
    if n < 2:
        return b, c, d
    if n == 2:
        b[:] = (y[1] - y[0]) / (x[1] - x[0])
        return b, c, d
    h = np.diff(x)
    # Second derivatives with natural ends. c stores m/2, matching splinefun.
    m = np.zeros(n)
    if n > 2:
        size = n - 2
        band = np.zeros((size, size))
        rhs = np.zeros(size)
        for i in range(size):
            # equation for m[i+1]
            band[i, i] = (h[i] + h[i + 1]) / 3.0
            if i > 0:
                band[i, i - 1] = h[i] / 6.0
            if i + 1 < size:
                band[i, i + 1] = h[i + 1] / 6.0
            rhs[i] = (y[i + 2] - y[i + 1]) / h[i + 1] - (y[i + 1] - y[i]) / h[i]
        mid = np.linalg.solve(band, rhs)
        m[1:-1] = mid
    c[:] = m / 2.0
    for i in range(n - 1):
        b[i] = (y[i + 1] - y[i]) / h[i] - h[i] * (2.0 * m[i] + m[i + 1]) / 6.0
        d[i] = (m[i + 1] - m[i]) / (6.0 * h[i])
    # The last slope is the derivative of the last piece at its right end.
    i = n - 2
    dx = h[i]
    b[n - 1] = b[i] + 2.0 * c[i] * dx + 3.0 * d[i] * dx * dx
    return b, c, d


def _spline_eval(
    x: np.ndarray,
    y: np.ndarray,
    b: np.ndarray,
    c: np.ndarray,
    d: np.ndarray,
    xout: np.ndarray,
    linear_ends: bool = False,
) -> np.ndarray:
    n = len(x)
    out = np.empty(len(xout), dtype=np.float64)
    for t, value in enumerate(xout):
        v = float(value)
        if math.isnan(v):
            out[t] = _NA
            continue
        # A natural spline continues in a straight line past the outer knots.
        if linear_ends and v < x[0]:
            out[t] = y[0] + b[0] * (v - x[0])
            continue
        if linear_ends and v > x[-1]:
            out[t] = y[-1] + b[-1] * (v - x[-1])
            continue
        if v <= x[0]:
            i = 0
        elif v >= x[-1]:
            i = n - 2
        else:
            lo = 0
            hi = n - 1
            while hi - lo > 1:
                mid = (lo + hi) // 2
                if v < x[mid]:
                    hi = mid
                else:
                    lo = mid
            i = lo
        dx = v - x[i]
        out[t] = y[i] + dx * (b[i] + dx * (c[i] + dx * d[i]))
    return out


def splinefun(x: Any, y: Any, method: str = "fmm", ties: Any = None):
    """``stats::splinefun``. The returned callable evaluates the spline."""
    method = _match_arg(method, ["fmm", "periodic", "natural", "monoH.FC", "hyman"])
    if method not in ("fmm", "natural"):
        raise ValueError(f"spline method '{method}' is not implemented")
    x_arr, y_arr = _regularize(np.asarray(x, dtype=np.float64), np.asarray(y, dtype=np.float64), ties)
    if len(x_arr) == 0:
        raise ValueError("zero non-NA points")
    if method == "natural":
        b, c, d = _natural_spline(x_arr, y_arr)
    else:
        b, c, d = _fmm_spline(x_arr, y_arr)

    def evaluate(xout: Any, deriv: int = 0) -> np.ndarray:
        if deriv != 0:
            raise ValueError("'deriv' must be between 0 and 3")
        return _spline_eval(
            x_arr,
            y_arr,
            b,
            c,
            d,
            np.asarray(xout, dtype=np.float64).reshape(-1),
            linear_ends=(method == "natural"),
        )

    return evaluate


# ---------------------------------------------------------------------------
# na.trim
# ---------------------------------------------------------------------------


def _present_mask(object: Any, how: str) -> np.ndarray:
    data = _core(object)
    if data.ndim < 2 or how == "any":
        if data.ndim < 2:
            return ~np.isnan(np.asarray(data, dtype=np.float64).reshape(-1))
        # complete.cases: a row is present when every column is present
        return ~np.any(np.isnan(data), axis=1)
    return np.sum(~np.isnan(data), axis=1) > 0


def _rlength(mask: np.ndarray) -> int:
    if not np.any(mask):
        return int(len(mask))
    return int(np.flatnonzero(mask)[0])


def na_trim_default(
    object: Any,
    sides: str = "both",
    is_na: str = "any",
    maxgap: float = math.inf,
    **_kwargs: Any,
) -> Any:
    """Drop leading and trailing missing observations."""
    how = _match_arg(is_na, ["any", "all"])
    side = _match_arg(sides, ["both", "left", "right"])
    data = _core(object)
    present = _present_mask(object, how)
    if side == "left":
        idx0 = np.cumsum(present.astype(np.int64)) > 0
        keep = idx0 | (_rlength(idx0) > maxgap)
    elif side == "right":
        idx0 = np.cumsum(present[::-1].astype(np.int64) > 0) > 0
        keep = idx0[::-1] | (_rlength(idx0) > maxgap)
    else:
        idx0l = np.cumsum(present.astype(np.int64)) > 0
        idx0r = np.cumsum(present[::-1].astype(np.int64) > 0) > 0
        keep = (idx0l | (_rlength(idx0l) > maxgap)) & (idx0r[::-1] | (_rlength(idx0r) > maxgap))
    if isinstance(object, Zoo):
        if data.ndim < 2:
            return _copy_zoo(object, np.asarray(data).reshape(-1)[keep], _subset_index(object.index, keep))
        return _copy_zoo(object, data[keep, :], _subset_index(object.index, keep))
    if data.ndim < 2:
        return np.asarray(data, dtype=np.float64).reshape(-1)[keep]
    return data[keep, :]


def na_trim(object: Any, *args: Any, **kwargs: Any) -> Any:
    """Generic trim. A ``Zoo`` and a plain array both use the default method."""
    del args
    return na_trim_default(object, **kwargs)


def na_trim_ts(object: Any, *args: Any, **kwargs: Any) -> np.ndarray:
    """Trim a regular series and return the numeric values, as ``as.ts`` would."""
    del args
    trimmed = na_trim_default(object, **kwargs)
    if isinstance(trimmed, Zoo):
        return np.asarray(trimmed.data, dtype=np.float64).reshape(-1)
    return np.asarray(trimmed, dtype=np.float64).reshape(-1)


# ---------------------------------------------------------------------------
# na.approx / na.spline
# ---------------------------------------------------------------------------


def _interp_vec(x: np.ndarray, y: np.ndarray, xout: np.ndarray, maxgap: float, kind: str, kwargs: dict[str, Any]) -> np.ndarray:
    na = np.isnan(y)
    n_ok = int(np.sum(~na))
    need = 2 if kind == "approx" else 1
    if n_ok < need:
        yf = _na_array(len(xout))
        if n_ok == 1:
            x_one = x[~na][0]
            y_one = y[~na][0]
            if np.any(xout == x_one):
                yf[xout == x_one] = y_one
        return yf
    if (not np.any(na)) and (len(xout) > maxgap) and (not np.all(np.isin(xout, x))):
        xf = np.unique(np.concatenate([x, xout]))
        yf = _na_array(len(xf))
        # MATCH(x, xf): first hit, xf is sorted unique
        pos = np.searchsorted(xf, x)
        yf[pos] = y
        x = xf
        y = yf
        na = np.isnan(y)
    x_ok = x[~na]
    y_ok = y[~na]
    if kind == "approx":
        yf = approx(x_ok, y_ok, xout, **kwargs)
    else:
        method = kwargs.get("method", "fmm")
        yf = splinefun(x_ok, y_ok, method=method)(xout)
    if maxgap < len(y):
        positions = np.arange(1, len(y) + 1, dtype=np.float64)
        ygap = _fill_short_gaps(y, positions, maxgap)
        if kind == "approx":
            ix = approx(x, positions, xout, **kwargs)
        else:
            method = kwargs.get("method", "fmm")
            ix = splinefun(x, positions, method=method)(xout)
        out = np.array(yf, copy=True)
        for i, point in enumerate(ix):
            if math.isnan(float(point)):
                out[i] = _NA
                continue
            left = int(math.floor(float(point)))
            right = int(math.ceil(float(point)))
            bad = False
            for end in (left, right):
                j = end - 1
                if j < 0 or j >= len(ygap) or math.isnan(float(ygap[j])):
                    bad = True
            if bad:
                out[i] = _NA
        return out
    return yf


def _resolve_x(object: Any, x: Any, along: Any) -> np.ndarray:
    if along is not None:
        warnings.warn("along to be deprecated - use x instead", stacklevel=3)
        if x is None:
            x = along
    if x is None:
        x = _index_of(object)
    elif callable(x):
        x = x(_index_of(object))
    x_arr = np.asarray(x, dtype=np.float64).reshape(-1)
    if len(x_arr) != len(_index_of(object)):
        raise ValueError("x and index must have the same length")
    return x_arr


def _columns(data: np.ndarray) -> list[np.ndarray]:
    if data.ndim < 2:
        return [np.asarray(data, dtype=np.float64).reshape(-1)]
    return [np.asarray(data[:, j], dtype=np.float64) for j in range(data.shape[1])]


def na_approx_default(
    object: Any,
    x: Any = None,
    xout: Any = None,
    na_rm: bool = True,
    maxgap: float = math.inf,
    along: Any = None,
    **kwargs: Any,
) -> np.ndarray:
    """Replace missing values by linear interpolation and return the numbers."""
    x_arr = _resolve_x(object, x, along)
    if xout is None:
        xout_arr = x_arr
    else:
        if callable(xout):
            xout = xout(_index_of(object))
        xout_arr = np.asarray(xout, dtype=np.float64).reshape(-1)
    data = _core(object)
    cols = _columns(data)
    filled = [_interp_vec(x_arr, col, xout_arr, maxgap, "approx", kwargs) for col in cols]
    if data.ndim < 2:
        result: Any = filled[0]
    else:
        result = np.column_stack(filled)
    if na_rm:
        result = na_trim_default(result, is_na="all", maxgap=maxgap)
    return np.asarray(result, dtype=np.float64)


def _interp_zoo(object: Zoo, worker, x, xout, na_rm, maxgap, along, kwargs) -> Zoo:
    if along is not None:
        warnings.warn("along to be deprecated - use x instead", stacklevel=3)
        if x is None:
            x = along
    if callable(x):
        x = x(_index_of(object))
    if x is None:
        x = _index_of(object)
    missing_xout = xout is None
    if not missing_xout and callable(xout):
        xout = xout(_index_of(object))
    order_by = _index_of(object) if missing_xout else np.asarray(xout, dtype=np.float64).reshape(-1)
    x_use = x if missing_xout else xout
    values = worker(object, x=x, xout=x_use, na_rm=False, maxgap=maxgap, **kwargs)
    if values.ndim == 1:
        data = values
    else:
        data = values
    result = _copy_zoo(object, data, order_by if len(order_by) == len(data) else object.index)
    if len(np.asarray(order_by)) == _nrow(result):
        result = _copy_zoo(object, data, order_by)
    if na_rm:
        result = na_trim_default(result, is_na="all", maxgap=maxgap)
    return result


def na_approx(
    object: Any,
    x: Any = None,
    xout: Any = None,
    na_rm: bool = True,
    maxgap: float = math.inf,
    along: Any = None,
    **kwargs: Any,
) -> Any:
    """Replace missing values by linear interpolation."""
    if isinstance(object, Zoo):
        return _interp_zoo(object, na_approx_default, x, xout, na_rm, maxgap, along, kwargs)
    return na_approx_default(object, x=x, xout=xout, na_rm=na_rm, maxgap=maxgap, along=along, **kwargs)


def na_spline_default(
    object: Any,
    x: Any = None,
    xout: Any = None,
    na_rm: bool = True,
    maxgap: float = math.inf,
    along: Any = None,
    **kwargs: Any,
) -> np.ndarray:
    """Replace missing values by cubic spline interpolation and return the numbers."""
    x_arr = _resolve_x(object, x, along)
    if xout is None:
        xout_arr = x_arr
    else:
        if callable(xout):
            xout = xout(_index_of(object))
        xout_arr = np.asarray(xout, dtype=np.float64).reshape(-1)
    data = _core(object)
    cols = _columns(data)
    filled = [_interp_vec(x_arr, col, xout_arr, maxgap, "spline", kwargs) for col in cols]
    result: Any = filled[0] if data.ndim < 2 else np.column_stack(filled)
    if na_rm:
        result = na_trim_default(result, is_na="all", maxgap=maxgap)
    return np.asarray(result, dtype=np.float64)


def na_spline(
    object: Any,
    x: Any = None,
    xout: Any = None,
    na_rm: bool = True,
    maxgap: float = math.inf,
    along: Any = None,
    **kwargs: Any,
) -> Any:
    """Replace missing values by cubic spline interpolation."""
    if isinstance(object, Zoo):
        return _interp_zoo(object, na_spline_default, x, xout, na_rm, maxgap, along, kwargs)
    return na_spline_default(object, x=x, xout=xout, na_rm=na_rm, maxgap=maxgap, along=along, **kwargs)


# ---------------------------------------------------------------------------
# na.locf
# ---------------------------------------------------------------------------


def na_locf0(object: Any, from_last: bool = False, maxgap: float = math.inf, coredata: bool | None = None) -> Any:
    """Last observation carried forward, without trimming leading gaps."""
    source = object
    data = _core(object)
    if coredata is None:
        coredata = isinstance(object, Zoo)
    if data.ndim >= 2:
        cols = []
        for j in range(data.shape[1]):
            cols.append(na_locf0(data[:, j], from_last=from_last, maxgap=maxgap, coredata=False))
        filled = np.column_stack(cols)
        if coredata and isinstance(source, Zoo):
            return _copy_zoo(source, filled)
        return filled
    values = np.asarray(data, dtype=np.float64).reshape(-1).copy()
    if from_last:
        values = values[::-1].copy()
    if len(values) == 0:
        return values
    ok = np.flatnonzero(~np.isnan(values)) + 1  # 1-based
    if math.isnan(float(values[0])):
        ok = np.concatenate(([1], ok))
    if len(ok) == 0:
        filled = values
    else:
        gaps = np.diff(np.concatenate([ok, [len(values) + 1]])).astype(int)
        pieces = [np.repeat(values[pos - 1], gap) for pos, gap in zip(ok, gaps)]
        carried = np.concatenate(pieces) if pieces else values
        if np.any(gaps > maxgap):
            filled = _fill_short_gaps(values, carried, maxgap)
        else:
            filled = carried
    if from_last:
        filled = filled[::-1].copy()
    if coredata and isinstance(source, Zoo):
        return _copy_zoo(source, filled)
    return filled


def na_locf_default(
    object: Any,
    na_rm: bool = True,
    from_last: bool | None = None,
    rev: bool | None = None,
    maxgap: float = math.inf,
    rule: Any = 2,
    **kwargs: Any,
) -> Any:
    """Carry the last non-missing observation forward."""
    if "x" in kwargs or "xout" in kwargs:
        if from_last is not None:
            raise ValueError("fromLast not supported if x or xout is specified")
        return na_approx(object, na_rm=na_rm, maxgap=maxgap, method="constant", rule=rule, **kwargs)
    if rev is not None:
        warnings.warn("na.locf.default: rev= deprecated. Use fromLast= instead.", stacklevel=2)
        if from_last is None:
            from_last = bool(rev)
    if from_last is None:
        from_last = False
    data = _core(object)
    if data.ndim == 0 or (data.ndim == 1) or (not isinstance(object, np.ndarray) and np.asarray(data).ndim < 2):
        filled = na_locf0(object, from_last=from_last, maxgap=maxgap)
    else:
        filled = na_locf0(object, from_last=from_last, maxgap=maxgap)
    if isinstance(filled, Zoo):
        result: Any = filled
    elif isinstance(object, Zoo):
        result = _copy_zoo(object, filled)
    else:
        result = filled
    if na_rm:
        return na_trim_default(result, is_na="all")
    return result


def na_locf(object: Any, na_rm: bool = True, **kwargs: Any) -> Any:
    """Carry the last non-missing observation forward."""
    return na_locf_default(object, na_rm=na_rm, **kwargs)


# ---------------------------------------------------------------------------
# na.fill / na.fill0
# ---------------------------------------------------------------------------


def _fill_parts(fill: Any) -> list[Any]:
    if fill is None:
        return []
    if isinstance(fill, str):
        return [fill]
    if isinstance(fill, (list, tuple)):
        return list(fill)
    array = np.asarray(fill)
    if array.ndim == 0:
        return [fill]
    return list(array.reshape(-1))


def _is_extend(value: Any) -> bool:
    return isinstance(value, str) and len(value) > 0 and "extend".startswith(value)


def _part_len(value: Any) -> int:
    if value is None:
        return 0
    if isinstance(value, str):
        return 1
    if isinstance(value, (list, tuple)):
        return len(value)
    array = np.asarray(value)
    if array.ndim == 0:
        return 1
    return int(array.size)


def _recycle_scalar(value: Any, n: int) -> np.ndarray:
    if value is None:
        return _na_array(n)
    if isinstance(value, str):
        raise ValueError("fill cannot be 'extend'")
    array = np.asarray(value, dtype=np.float64).reshape(-1)
    if len(array) == 0:
        return _na_array(0)
    if len(array) == 1:
        out = np.empty(n, dtype=np.float64)
        out[:] = array[0]
        return out
    reps = int(math.ceil(n / len(array)))
    return np.tile(array, reps)[:n]


def na_fill0(object: Any, fill: Any, ix: Any = None) -> np.ndarray:
    """Fill a plain vector. A single ``\"extend\"`` is an error."""
    values = np.array(_core(object), dtype=np.float64, copy=True).reshape(-1)
    if ix is None:
        ix_mask = ~np.isnan(values)
    else:
        ix_arr = np.asarray(ix)
        if ix_arr.dtype == bool:
            ix_mask = np.resize(ix_arr, len(values))
        else:
            ix_mask = np.isin(np.arange(1, len(values) + 1), np.asarray(ix_arr, dtype=int))
    if len(values) == 0:
        return values
    parts = _fill_parts(fill)
    if len(parts) == 0 or sum(_part_len(part) for part in parts) == 0:
        return values[ix_mask]
    if len(parts) == 1:
        if _is_extend(parts[0]):
            raise ValueError("fill cannot be 'extend'")
        out = values.copy()
        out[~ix_mask] = _recycle_scalar(parts[0], int(np.sum(~ix_mask)))
        return out
    recycled = [parts[i % len(parts)] for i in range(3)]
    if _is_extend(recycled[1]):
        raise ValueError("fill[[2L]] cannot be 'extend'")
    wx = np.flatnonzero(ix_mask) + 1
    if len(wx) == 0:
        out = values.copy()
        out[:] = _recycle_scalar(recycled[1], len(values))
        return out
    left = int(wx[0])
    right = int(wx[-1])
    if _is_extend(recycled[0]):
        recycled[0] = values[left - 1]
    if _is_extend(recycled[2]):
        recycled[2] = values[right - 1]
    lens = [_part_len(part) for part in recycled]
    pre = np.arange(1, len(values) + 1) < left
    post = np.arange(1, len(values) + 1) > right
    out = values.copy()
    if lens[1]:
        target = ~ix_mask
        out[target] = _recycle_scalar(recycled[1], int(np.sum(target)))
    if lens[0]:
        out[pre] = _recycle_scalar(recycled[0], int(np.sum(pre)))
    if lens[2]:
        out[post] = _recycle_scalar(recycled[2], int(np.sum(post)))
    omit = (pre & (lens[0] == 0)) | (~pre & ~post & ~ix_mask & (lens[1] == 0)) | (post & (lens[2] == 0))
    return out[~omit]


def _na_fill_zoo(object: Zoo, fill: Any, ix: Any) -> Zoo:
    data = np.array(_core(object), dtype=np.float64, copy=True)
    if data.ndim == 2 and data.shape[1] > 1:
        cols = []
        indexes = []
        for j in range(data.shape[1]):
            column = _copy_zoo(object, data[:, j])
            filled = _na_fill_zoo(column, fill, None if ix is None else ix)
            cols.append(np.asarray(filled.data, dtype=np.float64).reshape(-1))
            indexes.append(np.asarray(filled.index))
        # merge(..., all = FALSE) keeps the intersection of the indexes.
        common = indexes[0]
        for idx in indexes[1:]:
            common = common[np.isin(common, idx)]
        stacked = []
        for col, idx in zip(cols, indexes):
            lookup = {float(key): col[i] for i, key in enumerate(idx)}
            stacked.append(np.array([lookup[float(key)] for key in common]))
        return _copy_zoo(object, np.column_stack(stacked), common)
    values = data.reshape(-1).copy()
    if ix is None:
        ix_mask = ~np.isnan(values)
    else:
        ix_arr = np.asarray(ix)
        if ix_arr.dtype == bool:
            ix_mask = np.resize(ix_arr, len(values))
        else:
            ix_mask = np.isin(np.arange(1, len(values) + 1), np.asarray(ix_arr, dtype=int))
    parts = _fill_parts(fill)
    index = np.asarray(object.index).reshape(-1)
    if len(ix_mask) and np.any(ix_mask) or (ix is not None and not getattr(np.asarray(ix), "dtype", None) == bool and len(np.asarray(ix))):
        if not np.any(ix_mask):
            # fall through to the empty-ix branch below
            pass
        else:
            wix = np.flatnonzero(ix_mask) + 1
            wx_min = int(wix[0])
            wx_max = int(wix[-1])
            wrng = np.arange(wx_min, wx_max + 1)
            recycled = [parts[i % len(parts)] for i in range(3)] if parts else [None, None, None]
            n = len(values)
            if _part_len(recycled[0]) > 0 and recycled[0] is not None:
                if _is_extend(recycled[0]):
                    values[: wx_min - 1] = values[wx_min - 1]
                else:
                    values[: wx_min - 1] = _recycle_scalar(recycled[0], wx_min - 1)
            if _part_len(recycled[1]) > 0 and recycled[1] is not None:
                if _is_extend(recycled[1]):
                    observed = values[wix - 1]
                    values[wrng - 1] = approx(wix.astype(float), observed, wrng.astype(float))
                else:
                    interior = np.intersect1d(np.flatnonzero(~ix_mask) + 1, wrng)
                    if len(interior):
                        values[interior - 1] = _recycle_scalar(recycled[1], len(interior))
            if _part_len(recycled[2]) > 0 and recycled[2] is not None:
                if _is_extend(recycled[2]):
                    values[wx_max:] = values[wx_max - 1]
                else:
                    values[wx_max:] = _recycle_scalar(recycled[2], n - wx_max)
            keep = np.arange(1, n + 1)
            if _part_len(recycled[0]) == 0:
                keep = np.unique(np.maximum(wx_min, keep))
            if _part_len(recycled[1]) == 0:
                drop = np.intersect1d(np.flatnonzero(~ix_mask) + 1, wrng)
                keep = np.setdiff1d(keep, drop, assume_unique=False)
            if _part_len(recycled[2]) == 0:
                keep = np.unique(np.minimum(wx_max, keep))
            chosen = keep - 1
            return _copy_zoo(object, values[chosen], index[chosen] if len(index) == n else index)
    if parts:
        first = parts[0]
        if isinstance(first, (list, tuple)):
            first = first[0] if first else None
        scalar = np.asarray(first).reshape(-1)
        scalar_value = scalar[0] if len(scalar) else _NA
        if not _is_missing(scalar_value) and _is_extend(scalar_value):
            values[np.isnan(values)] = _NA
        else:
            values[np.isnan(values)] = float(scalar_value)
        return _copy_zoo(object, values, index)
    return _copy_zoo(object, values, index)


def na_fill(object: Any, fill: Any, ix: Any = None, **kwargs: Any) -> Any:
    """Fill missing values, or the positions selected by ``ix``."""
    del kwargs
    if not isinstance(object, Zoo):
        return na_fill_default(object, fill, ix=ix)
    return _na_fill_zoo(object, fill, ix)


def na_fill_default(object: Any, fill: Any, ix: Any = None, **kwargs: Any) -> np.ndarray:
    """Fill a plain array. The result is the numeric core of the zoo method."""
    del kwargs
    values = np.asarray(_core(object), dtype=np.float64)
    index = np.arange(1, values.shape[0] + 1)
    wrapped = Zoo(values, index)
    filled = _na_fill_zoo(wrapped, fill, ix)
    return np.asarray(filled.data, dtype=np.float64)


# ---------------------------------------------------------------------------
# na.aggregate
# ---------------------------------------------------------------------------


def _r_mean(x: np.ndarray) -> float:
    if len(x) == 0:
        return float("nan")  # plain NaN, as mean(numeric(0))
    return float(np.sum(x) / len(x))


def na_aggregate_default(
    object: Any,
    by: Any = 1,
    fun: Any = None,
    na_rm: bool = False,
    maxgap: float = math.inf,
    **kwargs: Any,
) -> Any:
    """Replace each missing value with an aggregate of its group."""
    if fun is None:
        fun = _r_mean
    if callable(by):
        by = by(_index_of(object), **kwargs)
    data = np.array(_core(object), dtype=np.float64, copy=True)

    def fill_vector(y: np.ndarray) -> np.ndarray:
        by_arr = np.asarray(by)
        if by_arr.ndim == 0 or len(by_arr) == 1:
            groups = np.repeat(by_arr.reshape(-1), len(y))
        else:
            groups = by_arr
        yf = y.copy()
        # ave() splits on the group values in order of appearance.
        keys = []
        for value in groups:
            marker = "NA" if _is_missing(value) else value
            if not keys or keys[-1] != marker and marker not in keys:
                keys.append(marker)
            elif marker not in keys:
                keys.append(marker)
        # Group equal values together, as ave does, including non-contiguous rows.
        seen = []
        for value in groups:
            marker = float(value) if not _is_missing(value) else None
            if marker not in seen and not (marker is None and any(item is None for item in seen)):
                seen.append(marker)
        for marker in seen:
            if marker is None:
                sel = np.isnan(groups.astype(float))
            else:
                sel = groups == marker
            block = y[sel]
            observed = block[~np.isnan(block)]
            replacement = fun(observed)
            block = block.copy()
            block[np.isnan(block)] = replacement
            yf[sel] = block
        return _fill_short_gaps(y, yf, maxgap)

    if data.ndim < 2:
        filled = fill_vector(data.reshape(-1))
        result: Any = filled
    else:
        result = np.column_stack([fill_vector(data[:, j]) for j in range(data.shape[1])])
    if isinstance(object, Zoo):
        held = _copy_zoo(object, result)
        if na_rm:
            return na_trim_default(held, is_na="all")
        return held
    if na_rm:
        return na_trim_default(result, is_na="all")
    return result


def na_aggregate(object: Any, by: Any = 1, fun: Any = None, na_rm: bool = False, maxgap: float = math.inf, **kwargs: Any) -> Any:
    """Replace each missing value with an aggregate of its group."""
    return na_aggregate_default(object, by=by, fun=fun, na_rm=na_rm, maxgap=maxgap, **kwargs)


# ---------------------------------------------------------------------------
# Kalman filter and na.StructTS
# ---------------------------------------------------------------------------


def _predict(a: np.ndarray, P: np.ndarray, T: np.ndarray, V: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    p = len(a)
    anew = np.zeros(p)
    for i in range(p):
        tmp = 0.0
        for j in range(p):
            tmp += T[i, j] * a[j]
        anew[i] = tmp
    mm = np.zeros((p, p))
    for j in range(p):
        for i in range(p):
            tmp = 0.0
            for k in range(p):
                tmp += T[i, k] * P[k, j]
            mm[i, j] = tmp
    P2 = np.zeros((p, p))
    for j in range(p):
        for i in range(p):
            tmp = V[i, j]
            for k in range(p):
                tmp += mm[i, k] * T[j, k]
            P2[i, j] = tmp
    return anew, P2


def _update(a: np.ndarray, P: np.ndarray, Z: np.ndarray, h: float, yt: float) -> tuple[np.ndarray, np.ndarray, float, float]:
    p = len(a)
    PZ = np.zeros(p)
    for i in range(p):
        tmp = 0.0
        for j in range(p):
            tmp += P[i, j] * Z[j]
        PZ[i] = tmp
    gain = h
    for i in range(p):
        gain += Z[i] * PZ[i]
    resid = yt
    for i in range(p):
        resid -= Z[i] * a[i]
    anew = a.copy()
    for i in range(p):
        anew[i] = a[i] + PZ[i] * resid / gain
    P2 = P.copy()
    for j in range(p):
        for i in range(p):
            P2[i, j] = P[i, j] - PZ[i] * PZ[j] / gain
    return anew, P2, gain, resid


def _kalman_like(y: np.ndarray, a0: np.ndarray, P0: np.ndarray, T: np.ndarray, Z: np.ndarray, V: np.ndarray, h: float) -> tuple[float, float]:
    a = a0.copy()
    P = P0.copy()
    ssq = 0.0
    sumlog = 0.0
    nu = 0
    for yt in y:
        a, P = _predict(a, P, T, V)
        if math.isnan(float(yt)):
            continue
        a, P, gain, resid = _update(a, P, Z, h, float(yt))
        ssq += resid * resid / gain
        sumlog += math.log(gain)
        nu += 1
    if nu == 0:
        return float("nan"), float("nan")
    return ssq / nu, sumlog / nu


def _kalman_smooth(y: np.ndarray, a0: np.ndarray, P0: np.ndarray, T: np.ndarray, Z: np.ndarray, V: np.ndarray, h: float) -> np.ndarray:
    n = len(y)
    p = len(a0)
    a = a0.copy()
    P = P0.copy()
    a_pred = np.zeros((n, p))
    P_pred = np.zeros((n, p, p))
    a_filt = np.zeros((n, p))
    P_filt = np.zeros((n, p, p))
    for t, yt in enumerate(y):
        a, P = _predict(a, P, T, V)
        a_pred[t] = a
        P_pred[t] = P
        if not math.isnan(float(yt)):
            a, P, _gain, _resid = _update(a, P, Z, h, float(yt))
        a_filt[t] = a
        P_filt[t] = P
    smooth = a_filt.copy()
    for t in range(n - 2, -1, -1):
        cross = P_filt[t] @ T.T
        gain = np.linalg.solve(P_pred[t + 1].T, cross.T).T
        smooth[t] = a_filt[t] + gain @ (smooth[t + 1] - a_pred[t + 1])
    return smooth


def _bsm_matrices(nf: int) -> tuple[np.ndarray, np.ndarray]:
    p = nf + 1
    T = np.zeros((p, p))
    T[0, 0] = 1.0
    T[0, 1] = 1.0
    T[1, 1] = 1.0
    T[2, 2:] = -1.0
    for i in range(2, nf):
        T[i + 1, i] = 1.0
    Z = np.zeros(p)
    Z[0] = 1.0
    Z[2] = 1.0
    return T, Z


def _model_matrices(kind: str, nf: int) -> tuple[np.ndarray, np.ndarray, int]:
    if kind == "level":
        return np.ones((1, 1)), np.ones(1), 1
    if kind == "trend":
        T = np.array([[1.0, 1.0], [0.0, 1.0]])
        return T, np.array([1.0, 0.0]), 2
    if nf <= 1:
        raise ValueError("frequency must be a positive integer >= 2 for BSM")
    T, Z = _bsm_matrices(nf)
    return T, Z, 3


def _lbfgs_direction(grad: np.ndarray, steps: list[np.ndarray], changes: list[np.ndarray]) -> np.ndarray:
    q = grad.copy()
    limit = len(steps)
    alphas: list[tuple[float, float, np.ndarray, np.ndarray]] = []
    for i in range(1, limit + 1):
        s = steps[-i]
        yy = changes[-i]
        rho = 1.0 / float(np.dot(yy, s))
        alpha = rho * float(np.dot(s, q))
        alphas.append((rho, alpha, s, yy))
        q = q - alpha * yy
    if not steps:
        gamma = 1.0
    else:
        gamma = float(np.dot(steps[-1], changes[-1]) / np.dot(changes[-1], changes[-1]))
    direction = gamma * q
    for i in range(limit - 1, -1, -1):
        rho, alpha, s, yy = alphas[i]
        beta = rho * float(np.dot(yy, direction))
        direction = direction + s * (alpha - beta)
    return -direction


def _structts_objective(y: np.ndarray, par: np.ndarray, vx: float, T: np.ndarray, Z: np.ndarray, np_state: int) -> float:
    if np.all(par == 0):
        return 1000.0
    p = len(Z)
    V = np.zeros((p, p))
    for i in range(np_state):
        V[i, i] = par[i] * vx
    h = float(par[np_state] * vx)
    a0 = np.zeros(p)
    a0[0] = y[0]
    P0 = np.full((p, p), 1e6 * vx)
    s2, sumlog = _kalman_like(y, a0, P0, T, Z, V, h)
    return 0.5 * (s2 + sumlog)


def _central_grad(y: np.ndarray, par: np.ndarray, vx: float, T: np.ndarray, Z: np.ndarray, np_state: int, eps: float = 0.001) -> np.ndarray:
    grad = np.zeros(len(par))
    for i in range(len(par)):
        plus = par.copy()
        minus = par.copy()
        plus[i] += eps
        minus[i] -= eps
        grad[i] = (
            _structts_objective(y, plus, vx, T, Z, np_state)
            - _structts_objective(y, minus, vx, T, Z, np_state)
        ) / (2.0 * eps)
    return grad


def _lbfgsb(y: np.ndarray, vx: float, T: np.ndarray, Z: np.ndarray, np_state: int) -> np.ndarray:
    """Bounded L-BFGS-B as ``optim`` uses it for ``StructTS``: start at ones, ndeps 0.001."""
    x = np.ones(np_state + 1)
    value = _structts_objective(y, x, vx, T, Z, np_state)
    steps: list[np.ndarray] = []
    changes: list[np.ndarray] = []
    grad = _central_grad(y, x, vx, T, Z, np_state)
    factr = 1e7
    tol = factr * float(np.finfo(float).eps)
    for _ in range(100):
        direction = _lbfgs_direction(grad, steps, changes)
        trial = np.maximum(x + direction, 0.0)
        trial_value = _structts_objective(y, trial, vx, T, Z, np_state)
        trial_grad = _central_grad(y, trial, vx, T, Z, np_state)
        step = trial - x
        change = trial_grad - grad
        if float(np.dot(step, change)) > 0.0:
            steps.append(step)
            changes.append(change)
            if len(steps) > 5:
                steps.pop(0)
                changes.pop(0)
        relative = (value - trial_value) / max(abs(value), abs(trial_value), 1.0)
        x = trial
        value = trial_value
        grad = trial_grad
        if relative <= tol:
            break
    return x


def _structts_impute(y: np.ndarray, frequency: float) -> np.ndarray:
    if len(y) == 0 or math.isnan(float(y[0])):
        raise ValueError("the first value of the time series must not be missing")
    if np.all(np.isnan(y)):
        raise ValueError("the series is entirely NA")
    nf = int(frequency) if frequency is not None else 1
    kind = "BSM" if frequency is not None and frequency > 1 else "trend"
    T, Z, np_state = _model_matrices(kind, nf)
    vx = _sample_variance(y) / 100.0
    par = _lbfgsb(y, vx, T, Z, np_state)
    p = len(Z)
    V = np.zeros((p, p))
    for i in range(np_state):
        V[i, i] = par[i] * vx
    h = float(par[np_state] * vx)
    a0 = np.zeros(p)
    a0[0] = y[0]
    P0 = np.full((p, p), 1e6 * vx)
    smooth = _kalman_smooth(y, a0, P0, T, Z, V, h)
    # fitted keeps level, slope, and (for BSM) the seasonal state.
    keep = 1 if kind == "level" else (2 if kind == "trend" else 3)
    states = smooth[:, :keep]
    if states.shape[1] < 2:
        raise ValueError("subscript out of bounds")
    # [,-2] drops the slope. One remaining column is a vector, and rowSums errors.
    if states.shape[1] == 2:
        raise ValueError("'x' must be an array of at least two dimensions")
    combined = states[:, 0] + np.sum(states[:, 2:], axis=1)
    out = np.array(y, dtype=np.float64, copy=True)
    missing = np.isnan(y)
    out[missing] = combined[missing]
    return out


def na_structts(object: Any, na_rm: bool = False, maxgap: float = math.inf, **_kwargs: Any) -> Any:
    """Replace missing values using the seasonal Kalman smoother from ``StructTS``."""
    if isinstance(object, Zoo):
        y = np.asarray(_core(object), dtype=np.float64).reshape(-1)
        frequency = 1.0 if object.frequency is None else float(object.frequency)
        filled = _structts_impute(y, frequency)
        filled = _fill_short_gaps(y, filled, maxgap)
        result = _copy_zoo(object, filled)
        if na_rm:
            return na_trim_default(result, is_na="all")
        return result
    array = np.asarray(object)
    if getattr(array, "ndim", 1) >= 2:
        cols = [na_structts(array[:, j], na_rm=False, maxgap=maxgap) for j in range(array.shape[1])]
        stacked = np.column_stack([np.asarray(col, dtype=np.float64).reshape(-1) for col in cols])
        if na_rm:
            return na_trim_default(stacked, is_na="all")
        return stacked
    raise ValueError("no applicable method for na.StructTS")
