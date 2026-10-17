"""Bootstrap confidence intervals from CRAN boot 1.3-32.

``boot.ci``, ``print.bootci``, ``norm.ci``, and ``abc.ci`` live here, with
the unexported helpers ``norm.inter``, ``basic.ci``, ``stud.ci``, ``perc.ci``,
and ``bca.ci``. Index arguments stay 1-based, as in R. A statistic that
receives resample indices (``stype`` ``"i"``) also receives those indices
1-based.

``bca.ci`` asks ``empinf`` for influence values. That routine belongs to
another module, so the jackknife it would run for a weight statistic, or for
an index statistic when there are fewer replicates than rows, is copied
below. The regression estimate needs the bootstrap frequency array, which
this module does not rebuild.
"""

from __future__ import annotations

import math
import warnings

import numpy as np

_SQRT2 = math.sqrt(2.0)
_INV_SQRT_2PI = 1.0 / math.sqrt(2.0 * math.pi)

# Peter Acklam's rational approximation for the standard normal quantile.
# Two Halley steps against math.erf bring it inside the comparison tolerance.
_ACKLAM_A = (
    -3.969683028665376e01,
    2.209460984245205e02,
    -2.759285104469687e02,
    1.383577518672690e02,
    -3.066479806614716e01,
    2.506628277459239e00,
)
_ACKLAM_B = (
    -5.447609879822406e01,
    1.615858368580409e02,
    -1.556989798598866e02,
    6.680131188771972e01,
    -1.328068155288572e01,
)
_ACKLAM_C = (
    -7.784894002430293e-03,
    -3.223964580411365e-01,
    -2.400758277161838e00,
    -2.549732539343734e00,
    4.374664141464968e00,
    2.938163982698783e00,
)
_ACKLAM_D = (
    7.784695709041462e-03,
    3.224671290700398e-01,
    2.445134137142996e00,
    3.754408661907416e00,
)
_ACKLAM_LOW = 0.02425
_ACKLAM_HIGH = 1.0 - _ACKLAM_LOW

_MISSING = object()

_LAB_NORMAL = "     Normal        "
_LAB_BASIC = "     Basic         "
_LAB_STUDENT = "   Studentized     "
_LAB_PERCENT = "    Percentile     "
_LAB_BCA = "      BCa          "


def _pnorm_scalar(z):
    if math.isnan(z):
        return math.nan
    if math.isinf(z):
        return 1.0 if z > 0 else 0.0
    return 0.5 * (1.0 + math.erf(z / _SQRT2))


def _acklam(p):
    if p < _ACKLAM_LOW:
        q = math.sqrt(-2.0 * math.log(p))
        return (
            (((((_ACKLAM_C[0] * q + _ACKLAM_C[1]) * q + _ACKLAM_C[2]) * q + _ACKLAM_C[3]) * q + _ACKLAM_C[4]) * q + _ACKLAM_C[5])
            / ((((_ACKLAM_D[0] * q + _ACKLAM_D[1]) * q + _ACKLAM_D[2]) * q + _ACKLAM_D[3]) * q + 1.0)
        )
    if p > _ACKLAM_HIGH:
        q = math.sqrt(-2.0 * math.log(1.0 - p))
        return -(
            (((((_ACKLAM_C[0] * q + _ACKLAM_C[1]) * q + _ACKLAM_C[2]) * q + _ACKLAM_C[3]) * q + _ACKLAM_C[4]) * q + _ACKLAM_C[5])
            / ((((_ACKLAM_D[0] * q + _ACKLAM_D[1]) * q + _ACKLAM_D[2]) * q + _ACKLAM_D[3]) * q + 1.0)
        )
    q = p - 0.5
    r = q * q
    return (
        (((((_ACKLAM_A[0] * r + _ACKLAM_A[1]) * r + _ACKLAM_A[2]) * r + _ACKLAM_A[3]) * r + _ACKLAM_A[4]) * r + _ACKLAM_A[5])
        * q
        / (((((_ACKLAM_B[0] * r + _ACKLAM_B[1]) * r + _ACKLAM_B[2]) * r + _ACKLAM_B[3]) * r + _ACKLAM_B[4]) * r + 1.0)
    )


def _refine_quantile(z, p):
    for _ in range(4):
        cdf = _pnorm_scalar(z)
        err = cdf - p
        if err == 0.0:
            return z
        pdf = math.exp(-0.5 * z * z) * _INV_SQRT_2PI
        if pdf == 0.0 or not math.isfinite(pdf):
            return z
        denom = pdf + 0.5 * z * err
        if denom == 0.0 or not math.isfinite(denom):
            return z
        step = err / denom
        if not math.isfinite(step):
            return z
        z = z - step
        if abs(step) <= 1e-15 * (1.0 + abs(z)):
            return z
    return z


def _qnorm_scalar(p):
    if math.isnan(p):
        return math.nan
    if p == 0.0:
        return -math.inf
    if p == 1.0:
        return math.inf
    if p < 0.0 or p > 1.0:
        return math.nan
    z0 = _acklam(p)
    if abs(z0) > 6.0:
        return z0
    z = _refine_quantile(z0, p)
    if abs(z - z0) > 1e-7:
        return z0
    return z


def _map_scalar(values, fn):
    arr = np.asarray(values, dtype=float)
    if arr.shape == ():
        return fn(float(arr))
    out = np.empty(arr.shape, dtype=float)
    for idx, value in np.ndenumerate(arr):
        out[idx] = fn(float(value))
    return out


def _pnorm(z):
    return _map_scalar(z, _pnorm_scalar)


def _qnorm(p):
    return _map_scalar(p, _qnorm_scalar)


def _warn(message):
    warnings.warn(message, UserWarning, stacklevel=3)


def _get(obj, name, default=None):
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj[name] if name in obj else default
    return getattr(obj, name, default)


def _nrow(data):
    arr = np.asarray(data)
    if arr.ndim == 0:
        return 1
    if arr.ndim == 1:
        return int(arr.shape[0])
    return int(arr.shape[0])


def _as_1d(values):
    return np.asarray(values, dtype=float).reshape(-1)


def _scalar(value):
    arr = np.asarray(value, dtype=float).reshape(-1)
    if arr.size != 1:
        raise ValueError("expected a scalar")
    return float(arr[0])


def _maybe_float(values):
    arr = _as_1d(values)
    if arr.size == 1:
        return float(arr[0])
    return arr


def _identity(t):
    return t


def _ones_hdot(t):
    return np.ones(_as_1d(t).size, dtype=float)


def _one_hdot(t):
    return 1.0


def _as_index(index):
    if isinstance(index, (int, np.integer)):
        return [int(index)]
    return [int(v) for v in np.asarray(index).reshape(-1)]


def _column(values, index):
    arr = np.asarray(values, dtype=float)
    if arr.ndim <= 1:
        if index != 1:
            raise IndexError("subscript out of bounds")
        return arr.reshape(-1).copy()
    if index < 1 or index > arr.shape[1]:
        raise IndexError("subscript out of bounds")
    return np.array(arr[:, index - 1], dtype=float, copy=True)


def _at(values, index):
    arr = _as_1d(values)
    if index < 1 or index > arr.size:
        raise IndexError("subscript out of bounds")
    return float(arr[index - 1])


def _stat_at(statistic, data, argument, index, **kwargs):
    value = statistic(data, argument, **kwargs)
    return _at(value, index)


def _sample_var(values):
    arr = _as_1d(values)
    if arr.size < 2 or not np.all(np.isfinite(arr)):
        return math.nan
    return float(np.var(arr, ddof=1))


def _const(values, eps):
    """R's ``const``: every finite deviation is below ``eps``.

    ``all()`` is true only when every comparison is true. A missing
    comparison with no explicit false comparison is the R error from
    ``if (NA)``.
    """
    w = _as_1d(values)
    if w.size == 0 or not np.any(np.isfinite(w)):
        raise ValueError("missing value where TRUE/FALSE needed")
    center = float(np.nanmean(w))
    cmp = np.abs(w - center) < eps
    if bool(np.all(cmp)):
        return True
    finite = np.isfinite(w)
    if bool(np.any(~cmp & finite)):
        return False
    raise ValueError("missing value where TRUE/FALSE needed")


def _as_character_number(value):
    x = float(value)
    if math.isnan(x):
        return "NaN"
    if math.isinf(x):
        return "Inf" if x > 0 else "-Inf"
    if x == 0.0:
        return "0"
    rounded = float(np.round(x))
    if abs(x) < 1e15 and rounded == x:
        return str(int(rounded))
    text = np.format_float_positional(x, precision=15, unique=True, fractional=False, trim=".")
    if text in {"-0", "-0.0"}:
        return "0"
    return text


def _floor_log10(x):
    ax = abs(float(x))
    if ax == 0.0 or not math.isfinite(ax):
        return 0
    e = math.floor(math.log10(ax))
    ten = 10.0 ** e
    if ax < ten:
        e -= 1
    elif ax >= ten * 10.0:
        e += 1
    return e


def _nonfinite_text(x):
    if math.isnan(x):
        return "NaN"
    return "Inf" if x > 0 else "-Inf"


def _format_fixed_one(x, d):
    if not math.isfinite(x):
        return _nonfinite_text(x)
    if d <= 0:
        return str(int(np.round(x)))
    return f"{float(x):.{int(d)}f}"


def _sci_mantissa(x, de):
    if x == 0.0 or not math.isfinite(x):
        return 0.0, 0
    exp = _floor_log10(abs(x))
    mant = float(x) / (10.0 ** exp)
    if de > 0:
        mant = float(np.round(mant * 10.0 ** de) / 10.0 ** de)
    else:
        mant = float(np.round(mant))
    if abs(mant) >= 10.0:
        mant /= 10.0
        exp += 1
    elif mant != 0.0 and abs(mant) < 1.0:
        mant *= 10.0
        exp -= 1
    return mant, exp


def _format_sci_one(x, de):
    if not math.isfinite(x):
        return _nonfinite_text(x)
    mant, exp = _sci_mantissa(x, de)
    if de <= 0:
        body = f"{mant:.0f}"
    else:
        body = f"{mant:.{int(de)}f}"
    return f"{body}e{exp:+03d}"


def _fixed_trailing_zero(x, d):
    if not math.isfinite(x) or d <= 0:
        return True
    hi = float(np.round(float(x) * 10.0 ** d))
    lo = float(np.round(float(x) * 10.0 ** (d - 1)))
    return hi == lo * 10.0


def _fixed_decimals(xs, digits, nsmall):
    finite = [abs(x) for x in xs if math.isfinite(x) and x != 0.0]
    if not finite:
        return nsmall
    emin = min(_floor_log10(v) for v in finite)
    d = max(nsmall, digits - 1 - emin)
    while d > nsmall and all(_fixed_trailing_zero(x, d) for x in xs):
        d -= 1
    return d


def _sci_trailing_zero(x, de):
    if not math.isfinite(x) or de <= 0:
        return True
    hi, exp_hi = _sci_mantissa(x, de)
    lo, exp_lo = _sci_mantissa(x, de - 1)
    if exp_hi != exp_lo:
        return False
    return abs(hi - lo) <= 5e-12 * max(1.0, abs(hi))


def _sci_decimals(xs, digits, nsmall):
    de = max(nsmall, digits - 1)
    while de > nsmall and all(_sci_trailing_zero(x, de) for x in xs):
        de -= 1
    return de


def _r_format(values, digits=7, nsmall=0, scipen=0):
    """R ``format`` for a numeric vector, digits 7 and scipen 0 by default.

    One field width covers the whole vector. Fixed notation wins a tie.
    """
    xs = [float(v) for v in _as_1d(values)]
    if not xs:
        return []
    fixed_d = _fixed_decimals(xs, digits, nsmall)
    sci_d = _sci_decimals(xs, digits, nsmall)
    fixed = [_format_fixed_one(x, fixed_d) for x in xs]
    sci = [_format_sci_one(x, sci_d) for x in xs]
    wf = max(len(s) for s in fixed)
    we = max(len(s) for s in sci)
    chosen = sci if wf > we + scipen else fixed
    width = max(len(s) for s in chosen)
    return [s.rjust(width) for s in chosen]


def _r_round_scalar(x, digits):
    """R ``round``.

    The fractional part is scaled on its own. Scaling the whole number in
    float64 turns ``101 * 0.975`` into an exact tie and NumPy returns
    ``98.48``; R returns ``98.47``.
    """
    if not math.isfinite(x):
        return float(x)
    digits = int(digits)
    sign = -1.0 if x < 0.0 else 1.0
    ax = abs(float(x))
    if digits == 0:
        return sign * float(np.round(ax))
    if digits > 0:
        pow10 = 10.0 ** digits
        intx = math.floor(ax)
        scaled = (ax - intx) * pow10
        return sign * (intx + float(np.round(scaled)) / pow10)
    pow10 = 10.0 ** (-digits)
    return sign * float(np.round(ax / pow10)) * pow10


def _r_round(values, digits):
    arr = np.asarray(values, dtype=float)
    if digits is None:
        return arr
    flat = [_r_round_scalar(float(v), int(digits)) for v in arr.reshape(-1)]
    return np.asarray(flat, dtype=float).reshape(arr.shape)


def _strata_codes(strata, n):
    """Integer group codes from ``tapply(strata, as.numeric(strata))``."""
    if strata is None:
        return np.ones(n, dtype=int)
    arr = np.asarray(strata)
    if arr.shape == ():
        arr = np.repeat(arr, n)
    arr = arr.reshape(-1)
    if arr.size != n:
        raise ValueError("strata has the wrong length")
    if arr.dtype.kind not in "iufb":
        _warn("NAs introduced by coercion")
        return np.full(n, -1, dtype=int)
    values = arr.astype(float)
    levels = np.unique(values[~np.isnan(values)])
    codes = np.empty(n, dtype=int)
    finite = ~np.isnan(values)
    codes[finite] = np.searchsorted(levels, values[finite]) + 1
    codes[~finite] = -1
    return codes


def _jackknife_influence(boot_out, index=1, t=None, strata=None, eps=0.001, **kwargs):
    """Jackknife influence copied from ``empinf`` for the paths BCa can run.

    A supplied replicate vector selects the regression estimate, which needs
    ``boot.array``. Weight statistics use the infinitesimal jackknife. Other
    statistics use the delete-one jackknife when a parametric or permutation
    bootstrap is in hand, or when there are fewer replicates than rows.
    """
    if _get(boot_out, "sim", "ordinary") == "parametric":
        raise ValueError("influence values cannot be found from a parametric bootstrap")
    data = _get(boot_out, "data")
    statistic = _get(boot_out, "statistic")
    if data is None or statistic is None:
        raise ValueError("neither 'data' nor bootstrap object specified")
    stype = _get(boot_out, "stype", None)
    if stype is None:
        stype = "i" if _get(boot_out, "sim", None) is not None else "w"
    if strata is None:
        strata = _get(boot_out, "strata", None)
    n = _nrow(data)
    if t is not None:
        raise ValueError(
            "regression influence needs the bootstrap frequency array; pass L"
        )
    sim = _get(boot_out, "sim", "ordinary")
    if stype == "w":
        kind = "inf"
    elif sim not in ("parametric", "permutation"):
        kind = "jack" if int(_get(boot_out, "R")) < n else "reg"
    else:
        kind = "jack"
    if kind == "reg":
        raise ValueError(
            "regression influence needs the bootstrap frequency array; pass L"
        )
    if kind == "inf":
        return _inf_jack(data, statistic, index, strata, eps, **kwargs)
    return _usual_jack(data, statistic, stype, index, strata, **kwargs)


def _inf_jack(data, stat, index=1, strata=None, eps=0.001, **kwargs):
    n = _nrow(data)
    eps = eps / n
    codes = _strata_codes(strata, n)
    counts = {int(s): int(np.sum(codes == s)) for s in np.unique(codes)}
    w_orig = np.array([1.0 / counts[int(s)] for s in codes], dtype=float)
    tobs = _stat_at(stat, data, w_orig, index, **kwargs)
    influence = np.empty(n, dtype=float)
    for i in range(n):
        group = codes == codes[i]
        w = w_orig.copy()
        w[group] = (1.0 - eps) * w[group]
        w[i] = w[i] + eps
        influence[i] = (_stat_at(stat, data, w, index, **kwargs) - tobs) / eps
    return influence


def _usual_jack(data, stat, stype="w", index=1, strata=None, **kwargs):
    n = _nrow(data)
    codes = _strata_codes(strata, n)
    influence = np.zeros(n, dtype=float)
    if stype == "w":
        counts = {int(s): int(np.sum(codes == s)) for s in np.unique(codes)}
        w0 = np.array([1.0 / counts[int(s)] for s in codes], dtype=float)
        tobs = _stat_at(stat, data, w0, index, **kwargs)
        for i in range(n):
            w1 = w0.copy()
            w1[i] = 0.0
            group = codes == codes[i]
            total = float(np.sum(w1[group]))
            w1[group] = w1[group] / total
            influence[i] = (int(np.sum(group)) - 1) * (
                tobs - _stat_at(stat, data, w1, index, **kwargs)
            )
    elif stype == "f":
        f0 = np.ones(n, dtype=float)
        tobs = _stat_at(stat, data, f0, index, **kwargs)
        for i in range(n):
            f1 = f0.copy()
            f1[i] = 0.0
            group = codes == codes[i]
            influence[i] = (int(np.sum(group)) - 1) * (
                tobs - _stat_at(stat, data, f1, index, **kwargs)
            )
    else:
        i0 = np.arange(1, n + 1)
        tobs = _stat_at(stat, data, i0, index, **kwargs)
        for i in range(n):
            i1 = np.delete(i0, i)
            group = codes == codes[i]
            influence[i] = (int(np.sum(group)) - 1) * (
                tobs - _stat_at(stat, data, i1, index, **kwargs)
            )
    return influence


def _find_type(boot_out):
    kind = _get(boot_out, "boot_type", None)
    if kind:
        return str(kind)
    call = _get(boot_out, "call", None)
    text = call if isinstance(call, str) else ""
    name = text.split("(", 1)[0].strip()
    if name.startswith("boot::"):
        name = name[6:]
    return name or "boot"


def _normalize_strata(weights, codes):
    out = np.array(weights, dtype=float, copy=True)
    for s in np.unique(codes):
        group = codes == s
        total = float(np.sum(out[group]))
        out[group] = out[group] / total
    return out


class _Symbol:
    def __init__(self, name):
        self.name = name


class BootCI:
    """Ordered result of ``boot_ci``, with R's 1-based component positions."""

    def __init__(self):
        self._order = []

    def add(self, name, value):
        if name not in self._order:
            self._order.append(name)
        setattr(self, name, value)
        return value

    def __len__(self):
        return len(self._order)

    def __getitem__(self, index):
        if isinstance(index, int):
            return getattr(self, self._order[index - 1])
        return getattr(self, index)


def _format_call_value(value):
    if isinstance(value, _Symbol):
        return value.name
    if callable(value):
        name = getattr(value, "__name__", "function")
        if name == "<lambda>":
            return "function(...)"
        return name
    if isinstance(value, str):
        return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'
    if isinstance(value, (list, tuple, np.ndarray)):
        arr = np.asarray(value)
        if arr.dtype.kind in "UOS":
            parts = ", ".join(_format_call_value(v) for v in arr.reshape(-1))
            return parts if arr.size == 1 else f"c({parts})"
        if arr.dtype.kind in "iuf":
            parts = [_as_character_number(v) for v in arr.reshape(-1)]
            return parts[0] if len(parts) == 1 else "c(" + ", ".join(parts) + ")"
    if isinstance(value, (int, np.integer)):
        return str(int(value))
    if isinstance(value, (float, np.floating)):
        return _as_character_number(value)
    return str(value)


def _deparse_call(name, pairs, width=60):
    if not pairs:
        return name + "()"
    chunks = [f"{key} = {_format_call_value(value)}" for key, value in pairs]
    lines = []
    current = name + "("
    for i, chunk in enumerate(chunks):
        piece = chunk + (")" if i == len(chunks) - 1 else ", ")
        if lines and len(current) + len(piece) > width:
            lines.append(current)
            current = "    " + piece
        elif not lines and len(current) + len(piece) > width and i > 0:
            lines.append(current)
            current = "    " + piece
        else:
            current += piece
    lines.append(current)
    return "\n".join(lines)


def norm_inter(t, alpha):
    """Interpolate order statistics on the normal quantile scale.

    Rounds the rank ``(R + 1) * alpha`` to two decimals and returns those
    ranks beside the interpolated values. Ranks at or outside ``1`` and
    ``R`` warn, matching ``norm.inter``.
    """
    values = _as_1d(t)
    values = values[np.isfinite(values)]
    alpha = _as_1d(alpha)
    replicates = values.size
    rk = (replicates + 1) * alpha
    if not bool(np.all((rk > 1) & (rk < replicates))):
        _warn("extreme order statistics used as endpoints")
    k = np.trunc(rk).astype(int)
    out = np.arange(1, alpha.size + 1, dtype=float)
    if replicates == 0:
        return np.column_stack([_r_round(rk, 2), out])
    tstar = np.sort(values)
    exact = k == rk
    if bool(np.any(exact)):
        out[exact] = tstar[k[exact] - 1]
    zero = k == 0
    if bool(np.any(zero)):
        out[zero] = tstar[0]
    top = k == replicates
    if bool(np.any(top)):
        out[top] = tstar[replicates - 1]
    mask = (~exact) & (k != 0) & (k != replicates)
    if bool(np.any(mask)):
        kk = k[mask]
        temp1 = _qnorm(alpha[mask])
        temp2 = _qnorm(kk / (replicates + 1))
        temp3 = _qnorm((kk + 1) / (replicates + 1))
        tk = tstar[kk - 1]
        tk1 = tstar[kk]
        with np.errstate(invalid="ignore", divide="ignore"):
            out[mask] = tk + (temp1 - temp2) / (temp3 - temp2) * (tk1 - tk)
    return np.column_stack([_r_round(rk, 2), out])


def _conf_array(conf):
    return np.atleast_1d(np.asarray(conf, dtype=float))


def basic_ci(t0, t, conf=0.95, hinv=None):
    if hinv is None:
        hinv = _identity
    conf = _conf_array(conf)
    alpha = np.concatenate([(1.0 + conf) / 2.0, (1.0 - conf) / 2.0])
    qq = norm_inter(t, alpha)
    ranks = qq[:, 0].reshape((conf.size, 2), order="F")
    ends = _as_1d(hinv(2.0 * t0 - qq[:, 1])).reshape((conf.size, 2), order="F")
    return np.column_stack([conf, ranks, ends])


def stud_ci(tv0, tv, conf=0.95, hinv=None):
    if hinv is None:
        hinv = _identity
    tv0 = _as_1d(tv0)
    tv = np.asarray(tv, dtype=float)
    if tv.ndim == 1:
        tv = tv.reshape(-1, 1)
    if tv0.size < 2 or tv.shape[1] < 2:
        _warn("variance required for studentized intervals")
        return np.nan
    conf = _conf_array(conf)
    with np.errstate(invalid="ignore", divide="ignore"):
        z = (tv[:, 0] - tv0[0]) / np.sqrt(tv[:, 1])
    alpha = np.concatenate([(1.0 + conf) / 2.0, (1.0 - conf) / 2.0])
    qq = norm_inter(z, alpha)
    ranks = qq[:, 0].reshape((conf.size, 2), order="F")
    with np.errstate(invalid="ignore", divide="ignore"):
        ends = _as_1d(hinv(tv0[0] - math.sqrt(float(tv0[1])) * qq[:, 1]))
    ends = ends.reshape((conf.size, 2), order="F")
    return np.column_stack([conf, ranks, ends])


def perc_ci(t, conf=0.95, hinv=None):
    if hinv is None:
        hinv = _identity
    conf = _conf_array(conf)
    alpha = np.concatenate([(1.0 - conf) / 2.0, (1.0 + conf) / 2.0])
    qq = norm_inter(t, alpha)
    ranks = qq[:, 0].reshape((conf.size, 2), order="F")
    ends = _as_1d(hinv(qq[:, 1])).reshape((conf.size, 2), order="F")
    return np.column_stack([conf, ranks, ends])


def bca_ci(
    boot_out,
    conf=0.95,
    index=1,
    t0=None,
    t=None,
    L=None,
    h=None,
    hdot=None,
    hinv=None,
    **kwargs,
):
    if h is None:
        h = _identity
    if hinv is None:
        hinv = _identity
    t_argument = t
    if t is None or t0 is None:
        t = _column(_get(boot_out, "t"), index)
        t0 = _at(_get(boot_out, "t0"), index)
    t = _as_1d(t)
    t = t[np.isfinite(t)]
    t0 = float(_as_1d(t0)[0])
    proportion = float(np.sum(t < t0) / t.size)
    w = float(_qnorm(proportion))
    if not math.isfinite(w):
        raise ValueError("estimated adjustment 'w' is infinite")
    conf = _conf_array(conf)
    alpha = np.concatenate([(1.0 - conf) / 2.0, (1.0 + conf) / 2.0])
    zalpha = _qnorm(alpha)
    if L is None:
        L = _jackknife_influence(boot_out, index=index, t=t_argument, **kwargs)
    L = _as_1d(L)
    sum_sq = float(np.sum(L ** 2))
    with np.errstate(invalid="ignore", divide="ignore"):
        a = float(np.sum(L ** 3) / (6.0 * sum_sq ** 1.5))
    if not math.isfinite(a):
        raise ValueError("estimated adjustment 'a' is NA")
    with np.errstate(invalid="ignore", divide="ignore"):
        adj = _pnorm(w + (w + zalpha) / (1.0 - a * (w + zalpha)))
    qq = norm_inter(t, _as_1d(adj))
    ranks = qq[:, 0].reshape((conf.size, 2), order="F")
    transformed = _as_1d(h(qq[:, 1]))
    ends = _as_1d(hinv(transformed)).reshape((conf.size, 2), order="F")
    return np.column_stack([conf, ranks, ends])


def norm_ci(
    boot_out=None,
    conf=0.95,
    index=1,
    var_t0=None,
    t0=None,
    t=None,
    L=None,
    h=None,
    hdot=None,
    hinv=None,
):
    """Normal approximation interval, bias-corrected when replicates are supplied.

    A single confidence level is still one row of a three-column matrix.
    ``cbind`` in the installed ``norm.ci`` does not drop that row to a vector.
    """
    if h is None:
        h = _identity
    if hdot is None:
        hdot = _one_hdot
    if hinv is None:
        hinv = _identity
    if t0 is None:
        if boot_out is not None:
            t0 = _at(_get(boot_out, "t0"), index)
        else:
            raise ValueError("bootstrap output object or 't0' required")
    if boot_out is not None and t is None:
        t = _column(_get(boot_out, "t"), index)
    if t is not None:
        t = _as_1d(t)
        t = _as_1d(h(t[np.isfinite(t)]))
    if var_t0 is None:
        if t is None:
            if L is None:
                raise ValueError("unable to calculate 'var.t0'")
            L = _as_1d(L)
            dot = np.asarray(hdot(t0), dtype=float)
            var_t0 = float(np.sum((dot * L / L.size) ** 2))
        else:
            var_t0 = _sample_var(t)
    else:
        dot = np.asarray(hdot(t0), dtype=float)
        var_t0 = _scalar(np.asarray(var_t0, dtype=float) * dot ** 2)
    t0 = _maybe_float(h(t0))
    if t is not None:
        bias = float(np.mean(t) - t0)
    else:
        bias = 0.0
    conf = _conf_array(conf)
    with np.errstate(invalid="ignore"):
        merr = math.sqrt(var_t0) * _as_1d(_qnorm((1.0 + conf) / 2.0))
    lower = _as_1d(hinv(t0 - bias - merr))
    upper = _as_1d(hinv(t0 - bias + merr))
    return np.column_stack([conf, lower, upper])


def _type_names(type):
    if isinstance(type, str):
        return [type]
    return [str(v) for v in np.asarray(type, dtype=object).reshape(-1)]


def _wants(types, name):
    return "all" in types or name in types


def boot_ci(
    boot_out,
    conf=_MISSING,
    type=_MISSING,
    index=_MISSING,
    var_t0=_MISSING,
    var_t=_MISSING,
    t0=_MISSING,
    t=_MISSING,
    L=_MISSING,
    h=_MISSING,
    hdot=_MISSING,
    hinv=_MISSING,
    **kwargs,
):
    """Five bootstrap intervals. ``type="all"`` requests every one of them."""
    supplied = []
    if conf is _MISSING:
        conf = 0.95
    else:
        supplied.append(("conf", conf))
    if type is _MISSING:
        type = "all"
    else:
        supplied.append(("type", type))
    if index is _MISSING:
        t0_object = _as_1d(_get(boot_out, "t0"))
        last = min(2, int(t0_object.size))
        index = list(range(1, last + 1))
    else:
        supplied.append(("index", index))
        index = _as_index(index)
    if var_t0 is _MISSING:
        var_t0 = None
    else:
        supplied.append(("var.t0", var_t0))
    if var_t is _MISSING:
        var_t = None
    else:
        supplied.append(("var.t", var_t))
    if t0 is _MISSING:
        t0 = None
    else:
        supplied.append(("t0", t0))
    if t is _MISSING:
        t = None
    else:
        supplied.append(("t", t))
    if L is _MISSING:
        L = _get(boot_out, "L", None)
    else:
        supplied.append(("L", L))
    h_supplied = h is not _MISSING
    hinv_supplied = hinv is not _MISSING
    if h is _MISSING:
        h = _identity
    else:
        supplied.append(("h", h))
    if hdot is _MISSING:
        hdot = _ones_hdot
    else:
        supplied.append(("hdot", hdot))
    if hinv is _MISSING:
        hinv = _identity
    else:
        supplied.append(("hinv", hinv))
    call = _deparse_call("boot_ci", [("boot_out", _Symbol("boot_out")), *supplied])
    # The scale note looks at whether h and hinv were arguments, not at the
    # deparsed text. Keep that beside the call string.
    call_info = {"text": call, "h": h_supplied, "hinv": hinv_supplied}

    if (t is None) ^ (t0 is None):
        raise ValueError("'t' and 't0' must be supplied together")
    t_original = None if t is None else _as_1d(t).copy()
    t0_original = None if t0 is None else _maybe_float(t0)
    var_t0_original = var_t0

    if t is None:
        if len(index) == 1:
            t0 = _at(_get(boot_out, "t0"), index[0])
            t = _column(_get(boot_out, "t"), index[0])
        else:
            replicates = np.asarray(_get(boot_out, "t"), dtype=float)
            width = 1 if replicates.ndim <= 1 else replicates.shape[1]
            if width < max(index):
                _warn("index out of bounds; minimum index only used.")
                index = [min(index)]
                t0 = _at(_get(boot_out, "t0"), index[0])
                t = _column(replicates, index[0])
            else:
                t0 = _at(_get(boot_out, "t0"), index[0])
                t = _column(replicates, index[0])
                if var_t0 is None:
                    var_t0 = _at(_get(boot_out, "t0"), index[1])
                if var_t is None:
                    var_t = _column(replicates, index[1])
    else:
        t = _as_1d(t)
        t0 = _maybe_float(t0)

    t = _as_1d(t)
    center = float(np.nanmean(t)) if np.any(np.isfinite(t)) else math.nan
    eps = min(1e-8, center / 1e6)
    if _const(t, eps):
        message = " ".join(
            [
                "All values of t are equal to ",
                _as_character_number(float(np.nanmean(t))),
                "\n Cannot calculate confidence intervals",
            ]
        )
        shown = message.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
        print(f'[1] "{shown}"')
        return None
    if t.size != int(_get(boot_out, "R")):
        raise ValueError(f"'t' must of length {int(_get(boot_out, 'R'))}")
    if var_t is None:
        finite = np.isfinite(t)
    else:
        var_t = _as_1d(var_t)
        finite = np.isfinite(t) & np.isfinite(var_t)
        var_t = var_t[finite]
    t = t[finite]
    if var_t0 is not None:
        dot0 = np.asarray(hdot(t0), dtype=float)
        var_t0 = _scalar(np.asarray(var_t0, dtype=float) * dot0 ** 2)
    if var_t is not None:
        var_t = var_t * np.asarray(hdot(t), dtype=float) ** 2
    t0 = _maybe_float(h(t0))
    t = _as_1d(h(t))
    output = BootCI()
    output.add("R", int(t.size))
    output.add("t0", _maybe_float(hinv(t0)))
    output.add("call", call_info)
    types = _type_names(type)
    if _wants(types, "norm"):
        output.add(
            "normal",
            norm_ci(
                boot_out,
                conf,
                index[0],
                var_t0=var_t0_original,
                t0=t0_original,
                t=t_original,
                L=L,
                h=h,
                hdot=hdot,
                hinv=hinv,
            ),
        )
    if _wants(types, "basic"):
        output.add("basic", basic_ci(t0, t, conf, hinv=hinv))
    if _wants(types, "stud"):
        if len(index) == 1:
            _warn("bootstrap variances needed for studentized intervals")
        elif var_t is None or var_t0 is None:
            output.add("student", stud_ci(np.array([t0], dtype=float), t.reshape(-1, 1), conf, hinv=hinv))
        else:
            output.add(
                "student",
                stud_ci(
                    np.array([t0, var_t0], dtype=float),
                    np.column_stack([t, var_t]),
                    conf,
                    hinv=hinv,
                ),
            )
    if _wants(types, "perc"):
        output.add("percent", perc_ci(t, conf, hinv=hinv))
    if _wants(types, "bca"):
        if _find_type(boot_out) == "tsboot":
            _warn("BCa intervals not defined for time series bootstraps")
        else:
            output.add(
                "bca",
                bca_ci(
                    boot_out,
                    conf,
                    index[0],
                    L=L,
                    t=t_original,
                    t0=t0_original,
                    h=h,
                    hdot=hdot,
                    hinv=hinv,
                    **kwargs,
                ),
            )
    return output


def _interval_labels(result):
    labels = []
    names = []
    if getattr(result, "normal", None) is not None:
        labels.append(_LAB_NORMAL)
        names.append("normal")
    if getattr(result, "basic", None) is not None:
        labels.append(_LAB_BASIC)
        names.append("basic")
    if getattr(result, "student", None) is not None:
        labels.append(_LAB_STUDENT)
        names.append("student")
    if getattr(result, "percent", None) is not None:
        labels.append(_LAB_PERCENT)
        names.append("percent")
    if getattr(result, "bca", None) is not None:
        labels.append(_LAB_BCA)
        names.append("bca")
    return labels, names


def _print_digits(t0):
    digs = math.ceil(math.log10(abs(float(t0)))) if t0 != 0 else -math.inf
    if digs <= 0:
        return 4
    if digs >= 4:
        return 0
    return int(4 - digs)


def _format_block(rows, digs):
    rounded = _r_round(rows, digs)
    flat = _r_format(rounded.ravel())
    return np.array(flat, dtype=object).reshape(rounded.shape)


def print_bootci(x, hinv=None, **kwargs):
    """Print a ``boot_ci`` result and return that text."""
    del kwargs
    ntypes = len(x) - 3
    nints = int(np.asarray(x[4]).shape[0])
    t0 = x.t0
    if hinv is not None:
        t0 = _maybe_float(hinv(t0))
    digs = _print_digits(t0)
    labels, names = _interval_labels(x)
    ranges = {}
    for name in ("basic", "student", "percent", "bca"):
        block = getattr(x, name, None)
        if block is not None:
            ranks = np.asarray(block, dtype=float)[:, 1:3]
            ranges[name] = (float(np.min(ranks)), float(np.max(ranks)))
    level = 100.0 * np.asarray(x[4], dtype=float)[:, 0]
    if ntypes == 4:
        n1 = n2 = 2
    elif ntypes == 5:
        n1, n2 = 3, 2
    else:
        n1, n2 = ntypes, 0
    ints1 = np.full((nints, 2 * n1 + 1), np.nan)
    ints1[:, 0] = level
    for offset, name in enumerate(names[:n1]):
        block = np.asarray(getattr(x, name), dtype=float)
        cols = np.array([block.shape[1] - 2, block.shape[1] - 1])
        # i = 4 + offset. R's j = c(2*i-6, 2*i-5) is 1-based.
        dest = np.array([2 * (offset + 4) - 7, 2 * (offset + 4) - 6])
        taken = block[:, cols]
        if hinv is not None:
            taken = _as_1d(hinv(taken.ravel(order="F"))).reshape(taken.shape, order="F")
        ints1[:, dest] = taken
    text1 = _format_block(ints1, digs)
    for row in range(nints):
        text1[row, 0] = "\n" + _as_character_number(level[row]) + "%  "
    for col in range(1, 2 * n1 + 1, 2):
        for row in range(nints):
            text1[row, col] = "(" + text1[row, col] + ","
            text1[row, col + 1] = text1[row, col + 1] + " )  "
    parts = ["BOOTSTRAP CONFIDENCE INTERVAL CALCULATIONS\n"]
    parts.append(f"Based on {x.R} bootstrap replicates\n\n")
    parts.append("CALL : \n")
    parts.append(x.call["text"] + "\n")
    parts.append("\nIntervals : ")
    parts.append(" ".join(["\nLevel", *labels[:n1]]))
    parts.append(" ".join(text1.ravel()))
    if n2 > 0:
        ints2 = np.full((nints, 2 * n2 + 1), np.nan)
        ints2[:, 0] = level
        dest = 1
        for name in names[n1 : n1 + n2]:
            block = np.asarray(getattr(x, name), dtype=float)
            taken = block[:, 3:5]
            if hinv is not None:
                taken = _as_1d(hinv(taken.ravel(order="F"))).reshape(taken.shape, order="F")
            ints2[:, dest : dest + 2] = taken
            dest += 2
        text2 = _format_block(ints2, digs)
        for row in range(nints):
            text2[row, 0] = "\n" + _as_character_number(level[row]) + "%  "
        for col in range(1, 2 * n2 + 1, 2):
            for row in range(nints):
                text2[row, col] = "(" + text2[row, col] + ","
                text2[row, col + 1] = text2[row, col + 1] + " )  "
        parts.append(" ".join(["\n\nLevel", *labels[n1 : n1 + n2]]))
        parts.append(" ".join(text2.ravel()))
    call = x.call
    if call["h"]:
        if not call["hinv"] and hinv is None:
            parts.append("\nCalculations and Intervals on  Transformed Scale\n")
        else:
            parts.append("\nCalculations on Transformed Scale;  Intervals on Original Scale\n")
    elif not call["hinv"] and hinv is None:
        parts.append("\nCalculations and Intervals on Original Scale\n")
    else:
        parts.append("\nCalculations on Original Scale  but Intervals Transformed\n")
    replicates = x.R
    warnings_for = (
        ("basic", "Basic", "basic"),
        ("student", "Studentized", "studentized"),
        ("percent", "Percentile", "percentile"),
        ("bca", "BCa", "BCa"),
    )
    for key, title, lower in warnings_for:
        if key not in ranges:
            continue
        lo, hi = ranges[key]
        if lo <= 1 or hi >= replicates:
            parts.append(f"Warning : {title} Intervals used Extreme Quantiles\n")
        if lo <= 10 or hi >= replicates - 9:
            parts.append(f"Some {lower} intervals may be unstable\n")
    text = "".join(parts)
    print(text, end="")
    return text


def abc_ci(data, statistic, index=1, strata=None, conf=0.95, eps=None, **kwargs):
    """Approximate bootstrap interval by numerical differentiation.

    One confidence level comes back as a vector of length three. Several
    levels come back as a matrix with one row each. The installed function
    drops the one-row matrix with ``as.vector`` and leaves the taller one.
    """
    n = _nrow(data)
    if strata is None:
        strata = np.ones(n, dtype=int)
    if eps is None:
        eps = 0.001 / n
    index = _as_index(index)
    if len(index) != 1:
        _warn("only first element of 'index' used in 'abc.ci'")
        index = index[:1]
    pos = index[0]
    codes = _strata_codes(strata, n)
    y = data
    w_orig = np.full(n, 1.0 / n)
    t0 = _stat_at(statistic, y, _normalize_strata(w_orig, codes), pos, **kwargs)
    influence = np.empty(n, dtype=float)
    second = np.empty(n, dtype=float)
    for i in range(n):
        w1 = (1.0 - eps) * w_orig
        w1[i] = w1[i] + eps
        w2 = (1.0 + eps) * w_orig
        w2[i] = w2[i] - eps
        t1 = _stat_at(statistic, y, _normalize_strata(w1, codes), pos, **kwargs)
        t2 = _stat_at(statistic, y, _normalize_strata(w2, codes), pos, **kwargs)
        influence[i] = (t1 - t2) / (2.0 * eps)
        second[i] = (t1 - 2.0 * t0 + t2) / eps ** 2
    temp1 = float(np.sum(influence * influence))
    sigmahat = math.sqrt(temp1) / n
    ahat = float(np.sum(influence ** 3) / (6.0 * temp1 ** 1.5))
    bhat = float(np.sum(second) / (2.0 * n * n))
    dhat = influence / (n * n * sigmahat)
    w3 = w_orig + eps * dhat
    w4 = w_orig - eps * dhat
    chat = (
        _stat_at(statistic, y, _normalize_strata(w3, codes), pos, **kwargs)
        - 2.0 * t0
        + _stat_at(statistic, y, _normalize_strata(w4, codes), pos, **kwargs)
    ) / (2.0 * eps * eps * sigmahat)
    bprime = ahat - (bhat / sigmahat - chat)
    conf = _conf_array(conf)
    stacked = np.vstack([-conf, conf])
    alpha = (1.0 + stacked.ravel(order="F")) / 2.0
    zalpha = _as_1d(_qnorm(alpha))
    with np.errstate(invalid="ignore", divide="ignore"):
        lalpha = (bprime + zalpha) / (1.0 - ahat * (bprime + zalpha)) ** 2
    out = np.empty(alpha.size, dtype=float)
    for i, scale in enumerate(lalpha):
        w_fin = w_orig + scale * dhat
        out[i] = _stat_at(statistic, y, _normalize_strata(w_fin, codes), pos, **kwargs)
    grid = out.reshape((conf.size, 2))
    result = np.column_stack([conf, grid])
    if conf.size == 1:
        return result.reshape(-1)
    return result
