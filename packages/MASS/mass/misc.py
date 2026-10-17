"""Small MASS helpers that do not fit a model."""

from __future__ import annotations

import math
import warnings
from decimal import Decimal, ROUND_HALF_EVEN

import numpy as np

from mass.errors import MassError


def enlist(vec):
    """Copy a vector into a list, keeping names when the input is a dict."""
    if isinstance(vec, dict):
        return {key: value for key, value in vec.items()}
    return list(vec)


def contr_sdif(n, contrasts: bool = True, sparse: bool = False):
    """Successive-difference contrasts."""
    if isinstance(n, (int, float, np.integer, np.floating)) and np.ndim(n) == 0:
        level = int(n)
        if level != n or level < 2:
            raise MassError("invalid number of levels")
        labels = [str(i) for i in range(1, level + 1)]
    else:
        labels = [str(item) for item in n]
        level = len(labels)
        if level < 2:
            raise MassError("invalid number of levels")
    if contrasts:
        columns = np.tile(np.arange(1, level), (level, 1)).astype(float)
        lower = np.tril(np.ones((level, level - 1), dtype=bool), -1)
        columns[~lower] = columns[~lower] - level
        matrix = columns / level
        names = [f"{labels[i + 1]}-{labels[i]}" for i in range(level - 1)]
        return matrix, labels, names
    if sparse:
        raise MassError("sparse contrasts are not started")
    matrix = np.eye(level)
    return matrix, labels, labels


def con2tr(obj) -> dict[str, list]:
    """Stack a contour object the way expand.grid stacks x and y."""
    xs = list(obj["x"])
    ys = list(obj["y"])
    grid = np.asarray(obj["z"], dtype=float)
    flat = grid.ravel(order="F")
    out_x = []
    out_y = []
    for y in ys:
        for x in xs:
            out_x.append(x)
            out_y.append(y)
    return {"x": out_x, "y": out_y, "z": flat.tolist()}


def fbeta(x, alpha, beta):
    """The beta density kernel without the constant."""
    values = np.asarray(x, dtype=float)
    return values ** (alpha - 1) * (1 - values) ** (beta - 1)


def area(f, a, b, *args, fa=None, fb=None, limit: int = 10, eps: float = 1e-5):
    """Adaptive Simpson integral of f from a to b."""
    if fa is None:
        fa = f(a, *args)
    if fb is None:
        fb = f(b, *args)
    h = b - a
    d = (a + b) / 2
    fd = f(d, *args)
    a1 = ((fa + fb) * h) / 2
    a2 = ((fa + 4 * fd + fb) * h) / 6
    if abs(a1 - a2) < eps:
        return a2
    if limit == 0:
        warnings.warn(
            f"iteration limit reached near 'x = {d:f}'",
            RuntimeWarning,
            stacklevel=2,
        )
        return a2
    left = area(f, a, d, *args, fa=fa, fb=fd, limit=limit - 1, eps=eps)
    right = area(f, d, b, *args, fa=fd, fb=fb, limit=limit - 1, eps=eps)
    return left + right


def _sample_sd(x: np.ndarray) -> float:
    return float(np.sqrt(np.var(x, ddof=1)))


def bandwidth_nrd(x) -> float:
    """Normal-reference bandwidth on the scale MASS uses for density."""
    values = np.asarray(x, dtype=float).reshape(-1)
    quartiles = np.quantile(values, [0.25, 0.75], method="linear")
    h = (quartiles[1] - quartiles[0]) / 1.34
    return 4 * 1.06 * min(_sample_sd(values), float(h)) * len(values) ** (-1 / 5)


_DELMAX = 1000.0
_SQRT_PI = math.sqrt(math.pi)


def _vr_den_bin(x: np.ndarray, nb: int) -> tuple[float, np.ndarray]:
    """Pairwise distance bin counts used by bcv and ucv."""
    nn = x.size
    cnt = np.zeros(nb, dtype=np.int64)
    xmin = float(x[0])
    xmax = float(x[0])
    for i in range(1, nn):
        xi = float(x[i])
        xmin = min(xmin, xi)
        xmax = max(xmax, xi)
    rang = (xmax - xmin) * 1.01
    dd = rang / nb
    for i in range(1, nn):
        ii = int(x[i] / dd)
        for j in range(i):
            jj = int(x[j] / dd)
            iij = abs(ii - jj)
            if cnt[iij] == np.iinfo(np.int64).max:
                raise MassError("maximum count exceeded in pairwise distance binning")
            cnt[iij] += 1
    return dd, cnt


def _vr_bcv_bin(n: int, cnt: np.ndarray, d: float, h: float) -> float:
    """Biased cross-validation score at bandwidth h."""
    nbin = cnt.size
    hh = h / 4.0
    total = 0.0
    for i in range(nbin):
        delta = i * d / hh
        delta *= delta
        if delta >= _DELMAX:
            break
        term = math.exp(-delta / 4.0) * (delta * delta - 12.0 * delta + 12.0)
        total += term * cnt[i]
    return 1.0 / (2.0 * n * hh * _SQRT_PI) + total / (
        64.0 * n * n * hh * _SQRT_PI
    )


def _vr_ucv_bin(n: int, cnt: np.ndarray, d: float, h: float) -> float:
    """Unbiased cross-validation score at bandwidth h."""
    nbin = cnt.size
    hh = h / 4.0
    total = 0.0
    for i in range(nbin):
        delta = i * d / hh
        delta *= delta
        if delta >= _DELMAX:
            break
        term = math.exp(-delta / 4.0) - math.sqrt(8.0) * math.exp(-delta / 2.0)
        total += term * cnt[i]
    return 1.0 / (2.0 * n * hh * _SQRT_PI) + total / (n * n * hh * _SQRT_PI)


def _optimize_brent(func, a: float, b: float, *, xatol: float) -> float:
    """One-dimensional minimizer matching R's optimize(..., maximum = FALSE)."""
    sqrt_eps = math.sqrt(2.2e-16)
    golden_mean = 0.5 * (3.0 - math.sqrt(5.0))
    fulc = a + golden_mean * (b - a)
    nfc = fulc
    xf = fulc
    rat = 0.0
    e = 0.0
    x = xf
    fx = func(x)
    ffulc = fx
    fnfc = fx
    fu = math.inf
    xm = 0.5 * (a + b)
    tol1 = sqrt_eps * abs(xf) + xatol / 3.0
    tol2 = 2.0 * tol1

    while abs(xf - xm) > (tol2 - 0.5 * (b - a)):
        golden = True
        if abs(e) > tol1:
            golden = False
            r = (xf - nfc) * (fx - ffulc)
            q = (xf - fulc) * (fx - fnfc)
            p = (xf - fulc) * q - (xf - nfc) * r
            q = 2.0 * (q - r)
            if q > 0.0:
                p = -p
            q = abs(q)
            r = e
            e = rat
            if abs(p) < abs(0.5 * q * r) and p > q * (a - xf) and p < q * (b - xf):
                rat = p / q
                x = xf + rat
                if (x - a) < tol2 or (b - x) < tol2:
                    si = 1.0 if xm - xf >= 0 else -1.0
                    if xm == xf:
                        si = 0.0
                    rat = tol1 * si
            else:
                golden = True

        if golden:
            if xf >= xm:
                e = a - xf
            else:
                e = b - xf
            rat = golden_mean * e

        si = 1.0 if rat >= 0 else -1.0
        if rat == 0:
            si = 0.0
        x = xf + si * max(abs(rat), tol1)
        fu = func(x)
        if fu <= fx:
            if x >= xf:
                a = xf
            else:
                b = xf
            fulc, ffulc = nfc, fnfc
            nfc, fnfc = xf, fx
            xf, fx = x, fu
        else:
            if x < xf:
                a = x
            else:
                b = x
            if fu <= fnfc or nfc == xf:
                fulc, ffulc = nfc, fnfc
                nfc, fnfc = x, fu
            elif fu <= ffulc or fulc == xf or fulc == nfc:
                fulc, ffulc = x, fu

        xm = 0.5 * (a + b)
        tol1 = sqrt_eps * abs(xf) + xatol / 3.0
        tol2 = 2.0 * tol1

    return xf


def bcv(x, nb: int = 1000, lower=None, upper=None) -> float:
    """Biased cross-validation bandwidth for a Gaussian kernel density estimate."""
    values = np.asarray(x, dtype=float).reshape(-1)
    n = values.size
    if n == 0:
        raise MassError("'x' has length zero")
    hmax = 1.144 * math.sqrt(float(np.var(values, ddof=1))) * n ** (-0.2) * 4.0
    if lower is None:
        lower = 0.1 * hmax
    if upper is None:
        upper = hmax
    d, cnt = _vr_den_bin(values, nb)
    lo = float(lower)
    hi = float(upper)

    def fbcv(h: float) -> float:
        return _vr_bcv_bin(n, cnt, d, h)

    h = _optimize_brent(fbcv, lo, hi, xatol=0.1 * lo)
    if h < 1.1 * lo or h > hi - 0.1 * lo:
        warnings.warn(
            "minimum occurred at one end of the range",
            RuntimeWarning,
            stacklevel=2,
        )
    return h


def ucv(x, nb: int = 1000, lower=None, upper=None) -> float:
    """Unbiased cross-validation bandwidth for a Gaussian kernel density estimate."""
    values = np.asarray(x, dtype=float).reshape(-1)
    n = values.size
    if n == 0:
        raise MassError("'x' has length zero")
    hmax = 1.144 * math.sqrt(float(np.var(values, ddof=1))) * n ** (-0.2) * 4.0
    if lower is None:
        lower = 0.1 * hmax
    if upper is None:
        upper = hmax
    d, cnt = _vr_den_bin(values, nb)
    lo = float(lower)
    hi = float(upper)

    def fucv(h: float) -> float:
        return _vr_ucv_bin(n, cnt, d, h)

    h = _optimize_brent(fucv, lo, hi, xatol=0.1 * lo)
    if h < 1.1 * lo or h > hi - 0.1 * lo:
        warnings.warn(
            "minimum occurred at one end of the range",
            RuntimeWarning,
            stacklevel=2,
        )
    return h


def nclass_freq(x) -> int:
    """Number of histogram classes from the frequency-polygon rule."""
    values = np.asarray(x, dtype=float).reshape(-1)
    h = 2.15 * _sample_sd(values) * len(values) ** (-1 / 5)
    return int(math.ceil((values.max() - values.min()) / h))


def _dnorm(z: np.ndarray) -> np.ndarray:
    return np.exp(-0.5 * z * z) / math.sqrt(2 * math.pi)


def kde2d(x, y, h=None, n=25, lims=None):
    """Two-dimensional kernel density on a grid."""
    xs = np.asarray(x, dtype=float).reshape(-1)
    ys = np.asarray(y, dtype=float).reshape(-1)
    nx = len(xs)
    if len(ys) != nx:
        raise MassError("data vectors must be the same length")
    if not np.isfinite(xs).all() or not np.isfinite(ys).all():
        raise MassError("missing or infinite values in the data are not allowed")
    if lims is None:
        limits = np.array([xs.min(), xs.max(), ys.min(), ys.max()], dtype=float)
    else:
        limits = np.asarray(lims, dtype=float).reshape(-1)
    if not np.isfinite(limits).all():
        raise MassError("only finite values are allowed in 'lims'")
    counts = np.resize(np.asarray(n, dtype=int).reshape(-1), 2)
    gx = np.linspace(limits[0], limits[1], int(counts[0]))
    gy = np.linspace(limits[2], limits[3], int(counts[1]))
    if h is None:
        width = np.array([bandwidth_nrd(xs), bandwidth_nrd(ys)], dtype=float)
    else:
        width = np.resize(np.asarray(h, dtype=float).reshape(-1), 2)
    if np.any(width <= 0):
        raise MassError("bandwidths must be strictly positive")
    width = width / 4
    ax = (gx[:, None] - xs[None, :]) / width[0]
    ay = (gy[:, None] - ys[None, :]) / width[1]
    z = (_dnorm(ax) @ _dnorm(ay).T) / (nx * width[0] * width[1])
    return {"x": gx, "y": gy, "z": z}


def _rounded_parts(value: float, digits: int = 7):
    """Sign, digit string, and the power of ten of the leading digit."""
    number = Decimal(str(value))
    if number == 0:
        return "", "0", 0
    sign = "-" if number < 0 else ""
    number = abs(number)
    exponent = int(number.adjusted())
    quantum = Decimal(10) ** (exponent - digits + 1)
    rounded = number.quantize(quantum, rounding=ROUND_HALF_EVEN)
    if rounded == 0:
        return "", "0", 0
    exponent = int(rounded.adjusted())
    quantum = Decimal(10) ** (exponent - digits + 1)
    scaled = (rounded / quantum).to_integral_value(rounding=ROUND_HALF_EVEN)
    text = f"{int(scaled):0{digits}d}"
    return sign, text, exponent


def _is_pow10(value: float) -> bool:
    _sign, text, _exponent = _rounded_parts(value)
    return set(text[1:]) <= {"0"}


def _natural_fixed(value: float, digits: int = 7) -> str:
    sign, text, exponent = _rounded_parts(value, digits)
    if exponent >= 0:
        if exponent + 1 >= len(text):
            body = text + ("0" * (exponent + 1 - len(text)))
        else:
            body = text[: exponent + 1] + "." + text[exponent + 1 :]
    else:
        body = "0." + ("0" * (-exponent - 1)) + text
    if "." in body:
        body = body.rstrip("0").rstrip(".")
    return sign + (body or "0")


def _natural_scientific(value: float, digits: int = 7) -> str:
    if value == 0:
        return "0e+00"
    sign, text, exponent = _rounded_parts(value, digits)
    frac = text[1:].rstrip("0")
    body = text[0] if not frac else f"{text[0]}.{frac}"
    return f"{sign}{body}e{exponent:+03d}"


def _wants_scientific(value: float, digits: int = 7) -> bool:
    if not math.isfinite(value) or value == 0:
        return False
    magnitude = abs(value)
    if magnitude <= 1e-4 or (magnitude >= 1e5 and _is_pow10(magnitude)):
        return True
    return len(_natural_scientific(value, digits)) < len(_natural_fixed(value, digits))


def _decimal_places(text: str) -> int:
    if "e" in text or "E" in text:
        significand = text.split("e")[0].split("E")[0]
        if "." not in significand:
            return 0
        return len(significand.split(".", 1)[1])
    if "." not in text:
        return 0
    return len(text.split(".", 1)[1])


def _pad_decimals(text: str, places: int) -> str:
    if "e" in text or "E" in text:
        significand, exponent = text.split("e")
        sign = ""
        if significand.startswith("-"):
            sign = "-"
            significand = significand[1:]
        whole, _, frac = significand.partition(".")
        frac = frac[:places].ljust(places, "0")
        body = whole if places == 0 else f"{whole}.{frac}"
        return f"{sign}{body}e{exponent}"
    sign = ""
    if text.startswith("-"):
        sign = "-"
        text = text[1:]
    whole, _, frac = text.partition(".")
    if places == 0:
        return f"{sign}{whole}"
    frac = frac[:places].ljust(places, "0")
    return f"{sign}{whole}.{frac}"


def format_numeric(values, digits: int = 7) -> list[str]:
    """Format a numeric vector the way R's format does at digits 7."""
    raw = []
    for value in values:
        if value is None or (isinstance(value, float) and math.isnan(value)):
            raw.append(None)
        else:
            raw.append(float(value))
    scientific = any(item is not None and _wants_scientific(item, digits) for item in raw)
    natural = []
    for item in raw:
        if item is None:
            natural.append("NA")
        elif scientific:
            natural.append(_natural_scientific(item, digits))
        else:
            natural.append(_natural_fixed(item, digits))
    places = max((_decimal_places(text) for text in natural if text != "NA"), default=0)
    padded = ["NA" if item is None else _pad_decimals(text, places) for item, text in zip(raw, natural)]
    width = max(len(text) for text in padded)
    return [text.rjust(width) for text in padded]


def write_matrix(x, file: str = "", sep: str = " ", columns=None) -> str:
    """Write a numeric matrix the way MASS write.matrix writes it."""
    grid = np.asarray(x, dtype=float)
    if grid.ndim == 1:
        grid = grid.reshape(-1, 1)
    formatted = np.array(format_numeric(grid.T.reshape(-1)), dtype=object).reshape(grid.T.shape)
    # cat walks the formatted transpose in column-major order.
    flat = [str(item) for item in formatted.ravel(order="F")]
    width = grid.shape[1]
    names = list(columns) if columns is not None else None
    cleaned = []
    for start in range(0, len(flat), width):
        cleaned.append(sep.join(flat[start : start + width]))
    if names:
        cleaned.insert(0, sep.join(str(name) for name in names))
    text = "\n".join(cleaned)
    if file:
        with open(file, "w", encoding="utf-8") as handle:
            handle.write(text + "\n")
    return text
