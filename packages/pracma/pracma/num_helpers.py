"""Private numeric helpers for the pracma numeric slice.

These follow the R implementations that the reserved functions call.
They are not package exports.
"""

from __future__ import annotations

import math
import warnings

import numpy as np

from pracma._util import PracmaError
from pracma.arrays import Norm, eye

_EPS = float(np.finfo(float).eps)


def match_arg(arg, choices):
    """R match.arg. The error text always says 'arg' and uses curly quotes."""
    if isinstance(arg, (list, tuple)):
        arg = arg[0]
    text = str(arg)
    matches = [choice for choice in choices if choice.startswith(text)]
    if len(matches) == 1:
        return matches[0]
    if text in choices:
        return text
    quoted = ", ".join(f"\u201c{choice}\u201d" for choice in choices)
    raise PracmaError(f"'arg' should be one of {quoted}")


def pmatch(arg, choices):
    """R pmatch with nomatch 0. An ambiguous prefix is 0."""
    text = str(arg)
    matches = [index for index, choice in enumerate(choices, start=1) if choice.startswith(text)]
    if len(matches) == 1:
        return matches[0]
    return 0


def is_r_numeric(value) -> bool:
    if value is None or isinstance(value, (str, bytes, bool, np.bool_)):
        return False
    if isinstance(value, (complex, np.complexfloating)):
        return False
    if isinstance(value, (int, float, np.integer, np.floating)):
        return True
    if isinstance(value, (list, tuple)):
        return all(is_r_numeric(item) for item in value)
    array = np.asarray(value)
    if array.dtype == object or array.dtype == bool:
        return False
    if np.issubdtype(array.dtype, np.complexfloating):
        return False
    return np.issubdtype(array.dtype, np.number)


def require_numeric(value, name):
    if not is_r_numeric(value):
        raise PracmaError(f"is.numeric({name}) is not TRUE")
    return value


def is_r_vector(value) -> bool:
    if isinstance(value, (str, bytes)):
        return False
    array = np.asarray(value)
    return array.ndim <= 1


def r_length(value) -> int:
    if value is None:
        return 0
    return int(np.asarray(value).size)


def as_float(value) -> np.ndarray:
    array = np.asarray(value, dtype=float)
    return array


def column_matrix(value) -> np.ndarray:
    """R as.matrix on a vector is one column."""
    array = np.asarray(value, dtype=float)
    if array.ndim == 0:
        return array.reshape(1, 1)
    if array.ndim == 1:
        return array.reshape(-1, 1)
    if array.ndim == 2:
        return np.array(array, dtype=float, copy=True)
    raise PracmaError("value must be a vector or a matrix")


def qr_solve(a, b):
    """Least squares, matching qr.solve on full-rank problems."""
    left = np.asarray(a, dtype=float)
    right = np.asarray(b, dtype=float)
    squeeze = right.ndim == 1
    solution, _, _, _ = np.linalg.lstsq(left, right, rcond=None)
    if squeeze:
        return np.asarray(solution, dtype=float).reshape(-1)
    return np.asarray(solution, dtype=float)


def r_svd(a):
    """Thin SVD with R's v, so A = U diag(d) t(v)."""
    matrix = np.asarray(a, dtype=float)
    u, singular, vh = np.linalg.svd(matrix, full_matrices=False)
    return u, singular, vh.T


def r_inv(a):
    matrix = np.asarray(a, dtype=float)
    if matrix.size == 0:
        return np.zeros((0, 0))
    if matrix.ndim != 2 or matrix.shape[0] != matrix.shape[1]:
        raise PracmaError("Matrix 'a' must be square.")
    try:
        return np.linalg.inv(matrix)
    except np.linalg.LinAlgError:
        warnings.warn("Matrix appears to be singular.", stacklevel=2)
        return np.full(matrix.shape, np.inf)


def r_rank(matrix) -> int:
    values = np.asarray(matrix, dtype=float)
    if values.size == 0:
        return 0
    if values.ndim == 1:
        values = values.reshape(-1, 1)
    singular = np.linalg.svd(values, compute_uv=False)
    if singular.size == 0:
        return 0
    tolerance = max(values.shape) * float(np.max(singular)) * _EPS
    return int(np.sum(singular > tolerance))


def distmat(x, y) -> np.ndarray:
    left = np.asarray(x, dtype=float)
    right = np.asarray(y, dtype=float)
    if left.ndim == 1:
        left = left.reshape(1, -1)
    if right.ndim == 1:
        right = right.reshape(1, -1)
    if left.shape[1] != right.shape[1]:
        raise PracmaError("X and Y must have the same number of columns.")
    product = left @ right.T
    left_sq = np.sum(left * left, axis=1)[:, None]
    right_sq = np.sum(right * right, axis=1)[None, :]
    return np.sqrt(np.maximum(left_sq + right_sq - 2.0 * product, 0.0))


def repmat(a, n, m=None) -> np.ndarray:
    if m is None:
        m = n
    if r_length(a) == 0:
        return np.array([])
    array = np.asarray(a)
    if np.iscomplexobj(array):
        array = np.array(array, dtype=complex)
    else:
        array = np.array(array, dtype=float)
    if array.ndim <= 1:
        array = array.reshape(1, -1)
    rows = max(math.floor(float(n)), 0)
    cols = max(math.floor(float(m)), 0)
    if rows <= 0 or cols <= 0:
        return np.zeros((rows, cols), dtype=array.dtype)
    return np.kron(np.ones((rows, cols), dtype=array.dtype), array)


def r_median(x) -> float:
    values = np.sort(np.asarray(x, dtype=float).reshape(-1))
    count = values.size
    if count == 0:
        return float("nan")
    mid = count // 2
    if count % 2:
        return float(values[mid])
    return float((values[mid - 1] + values[mid]) / 2.0)


def r_quantile(x, prob) -> float:
    """R quantile type 7 with fuzz 0."""
    values = np.sort(np.asarray(x, dtype=float).reshape(-1, order="F"))
    count = values.size
    probability = float(prob)
    if count == 0:
        return float("nan")
    if probability <= 0:
        return float(values[0])
    if probability >= 1:
        return float(values[-1])
    index = 1.0 + max(count - 1, 0) * probability
    lower = math.floor(index)
    fraction = index - lower
    if lower < 1:
        return float(values[0])
    if lower >= count:
        return float(values[-1])
    return float((1.0 - fraction) * values[lower - 1] + fraction * values[lower])


def r_diff(a, differences=1) -> np.ndarray:
    out = np.asarray(a, dtype=float)
    for _ in range(int(differences)):
        out = np.diff(out, axis=0)
    return out


def polyfit(x, y, n=1) -> np.ndarray:
    abscissa = np.asarray(x, dtype=float).reshape(-1)
    ordinate = np.asarray(y, dtype=float).reshape(-1)
    degree = int(n)
    powers = np.arange(degree, -1, -1)
    design = abscissa[:, None] ** powers[None, :]
    return qr_solve(design, ordinate)


def polyval(p, x) -> np.ndarray:
    coefficients = np.asarray(p, dtype=float).reshape(-1)
    abscissa = np.asarray(x, dtype=float)
    if abscissa.size == 0:
        return np.array([])
    if coefficients.size == 0:
        return np.zeros_like(abscissa, dtype=float)
    powers = np.arange(coefficients.size - 1, -1, -1)
    flat = abscissa.reshape(-1, order="F")
    values = (flat[:, None] ** powers[None, :]) @ coefficients
    if abscissa.ndim == 0:
        return values.reshape(())
    return values.reshape(abscissa.shape, order="F")


def r_mod(n, m):
    modulus = float(m)
    if modulus == 0:
        return np.asarray(n, dtype=float)
    return np.asarray(n, dtype=float) % modulus


def r_colon(start, end) -> np.ndarray:
    """R's colon operator, including the backward sequence."""
    left = float(start)
    right = float(end)
    if left == right:
        return np.array([left])
    step = 1.0 if left < right else -1.0
    count = int(math.floor((right - left) / step + 1e-10))
    return left + step * np.arange(count + 1)


def brent_fmin(func, ax, bx, tol) -> float:
    """R's Brent_fmin from src/appl/fmin.c."""
    golden = (3.0 - math.sqrt(5.0)) * 0.5
    eps = math.sqrt(_EPS)
    a = float(ax)
    b = float(bx)
    v = a + golden * (b - a)
    w = v
    x = v
    d = 0.0
    e = 0.0
    fx = float(func(x))
    fv = fx
    fw = fx
    tol3 = tol / 3.0
    while True:
        xm = (a + b) * 0.5
        tol1 = eps * abs(x) + tol3
        t2 = tol1 * 2.0
        if abs(x - xm) <= t2 - (b - a) * 0.5:
            break
        p = 0.0
        q = 0.0
        r = 0.0
        if abs(e) > tol1:
            r = (x - w) * (fx - fv)
            q = (x - v) * (fx - fw)
            p = (x - v) * q - (x - w) * r
            q = (q - r) * 2.0
            if q > 0.0:
                p = -p
            else:
                q = -q
            r = e
            e = d
        if abs(p) >= abs(q * 0.5 * r) or p <= q * (a - x) or p >= q * (b - x):
            e = (b - x) if x < xm else (a - x)
            d = golden * e
        else:
            d = p / q
            u = x + d
            if u - a < t2 or b - u < t2:
                d = tol1 if x < xm else -tol1
        if abs(d) >= tol1:
            u = x + d
        elif d > 0.0:
            u = x + tol1
        else:
            u = x - tol1
        fu = float(func(u))
        if fu <= fx:
            if u < x:
                b = x
            else:
                a = x
            v, w, x = w, x, u
            fv, fw, fx = fw, fx, fu
        else:
            if u < x:
                a = u
            else:
                b = u
            if fu <= fw or w == x:
                v, fv = w, fw
                w, fw = u, fu
            elif fu <= fv or v == x or v == w:
                v, fv = u, fu
    return x


def r_uniroot(func, lower, upper, tol=None, maxiter=1000) -> float:
    """R uniroot, Brent's zeroin with the default tolerance."""
    if tol is None:
        tol = _EPS ** 0.25
    a = float(lower)
    b = float(upper)
    fa = float(func(a))
    fb = float(func(b))
    if fa == 0.0:
        return a
    if fb == 0.0:
        return b
    c = a
    fc = fa
    left = maxiter + 1
    while left:
        left -= 1
        prev_step = b - a
        if abs(fc) < abs(fb):
            a = b
            b = c
            c = a
            fa = fb
            fb = fc
            fc = fa
        tol_act = 2.0 * _EPS * abs(b) + tol / 2.0
        new_step = (c - b) / 2.0
        if abs(new_step) <= tol_act or fb == 0.0:
            return b
        if abs(prev_step) >= tol_act and abs(fa) > abs(fb):
            cb = c - b
            if a == c:
                t1 = fb / fa
                p = cb * t1
                q = 1.0 - t1
            else:
                q = fa / fc
                t1 = fb / fc
                t2 = fb / fa
                p = t2 * (cb * q * (q - t1) - (b - a) * (t1 - 1.0))
                q = (q - 1.0) * (t1 - 1.0) * (t2 - 1.0)
            if p > 0.0:
                q = -q
            else:
                p = -p
            if p < (0.75 * cb * q - abs(tol_act * q) / 2.0) and p < abs(prev_step * q / 2.0):
                new_step = p / q
        if abs(new_step) < tol_act:
            new_step = tol_act if new_step > 0.0 else -tol_act
        a = b
        fa = fb
        b = b + new_step
        fb = float(func(b))
        if (fb > 0 and fc > 0) or (fb < 0 and fc < 0):
            c = a
            fc = fa
    return b


def r_optimize(func, lower, upper, maximum=False, tol=None):
    """R optimize. Returns the x and the original function value."""
    if tol is None:
        tol = _EPS ** 0.25

    def objective(x):
        value = float(func(x))
        return -value if maximum else value

    x = brent_fmin(objective, lower, upper, tol)
    return x, float(func(x))


def lm_slope(x, y) -> float:
    abscissa = np.asarray(x, dtype=float).reshape(-1)
    ordinate = np.asarray(y, dtype=float).reshape(-1)
    design = np.column_stack([np.ones(abscissa.size), abscissa])
    coefficients = qr_solve(design, ordinate)
    return float(coefficients[1])


def sample_sd(x) -> float:
    values = np.asarray(x, dtype=float).reshape(-1)
    if values.size < 2:
        return float("nan")
    centered = values - np.mean(values)
    return float(math.sqrt(np.sum(centered * centered) / (values.size - 1)))


def _merge_options(options, defaults):
    merged = dict(defaults)
    if not options:
        return merged
    for key, value in options.items():
        if key not in defaults:
            quoted = ", ".join(f"\u201c{name}\u201d" for name in defaults)
            raise PracmaError(f"'arg' should be one of {quoted}")
        merged[key] = value
    return merged


def lsqnonlin(fun, x0, options=None, *args, **kwargs):
    """Levenberg-Marquardt as in pracma lsqnonlin, including the xnew return."""
    from pracma.num_grad import jacobian

    defaults = {"tau": 1e-3, "tolx": 1e-8, "tolg": 1e-8, "maxeval": 700}
    opts = _merge_options(options, defaults)
    tau = float(opts["tau"])
    tolx = float(opts["tolx"])
    tolg = float(opts["tolg"])
    maxeval = int(opts["maxeval"])

    def residual(point):
        return np.asarray(fun(point, *args, **kwargs), dtype=float).reshape(-1)

    x = np.asarray(x0, dtype=float).reshape(-1)
    n = x.size
    r = residual(x)
    f = 0.5 * float(np.sum(r * r))
    jac = np.asarray(jacobian(lambda point: residual(point), x), dtype=float)
    if jac.ndim == 1:
        jac = jac.reshape(1, -1)
    g = jac.T @ r
    ng = Norm(g, math.inf)
    gram = jac.T @ jac
    mu = tau * float(np.max(np.diag(gram)))
    nu = 2.0
    nh = 0.0
    errno = 0
    k = 1
    xnew = x.copy()
    while k < maxeval:
        k += 1
        factor = np.linalg.cholesky(gram + mu * eye(n))
        h = -np.linalg.solve(factor.T, np.linalg.solve(factor, g))
        h = np.asarray(h, dtype=float).reshape(-1)
        nh = Norm(h)
        nx = tolx + Norm(x)
        if nh <= tolx * nx:
            errno = 1
            break
        xnew = x + h
        h = xnew - x
        d_l = float(np.sum(h * (mu * h - g))) / 2.0
        rn = residual(xnew)
        fn = 0.5 * float(np.sum(rn * rn))
        jac_n = np.asarray(jacobian(lambda point: residual(point), xnew), dtype=float)
        if jac_n.ndim == 1:
            jac_n = jac_n.reshape(1, -1)
        if rn.size != r.size:
            df = f - fn
        else:
            df = float(np.sum((r - rn) * (r + rn))) / 2.0
        if d_l > 0 and df > 0:
            x = xnew
            f = fn
            jac = jac_n
            r = rn
            gram = jac.T @ jac
            g = jac.T @ r
            ng = Norm(g, math.inf)
            mu = mu * max(1.0 / 3.0, 1.0 - (2.0 * df / d_l - 1.0) ** 3)
            nu = 2.0
        else:
            mu = mu * nu
            nu = 2.0 * nu
        if ng <= tolg:
            errno = 2
            break
    if k >= maxeval:
        errno = 3
    messages = (
        "Stopped by small x-step.",
        "Stopped by small gradient.",
        "No. of function evaluations exceeded.",
    )
    errmess = messages[errno - 1] if 1 <= errno <= 3 else None
    final = residual(xnew)
    return {
        "x": np.asarray(xnew, dtype=float).reshape(-1),
        "ssq": float(np.sum(final * final)),
        "ng": float(ng),
        "nh": float(nh),
        "mu": float(mu),
        "neval": int(k),
        "errno": int(errno),
        "errmess": errmess,
    }


def nullspace(matrix):
    values = np.asarray(matrix, dtype=float)
    if values.ndim == 1:
        values = values.reshape(-1, 1)
    _, singular, vh = np.linalg.svd(values, full_matrices=True)
    if singular.size == 0:
        return None
    tolerance = max(values.shape) * float(singular[0]) * _EPS
    rank = int(np.sum(singular > tolerance))
    if rank == values.shape[1]:
        return None
    return vh[rank:].T


def pinv(a, tol=None) -> np.ndarray:
    matrix = np.asarray(a, dtype=float)
    if tol is None:
        tol = _EPS ** (2.0 / 3.0)
    u, singular, vh = np.linalg.svd(matrix, full_matrices=True)
    if singular.size == 0:
        return np.zeros((matrix.shape[1], matrix.shape[0]))
    keep = singular > max(tol * float(singular[0]), 0.0)
    if not np.any(keep):
        return np.zeros((matrix.shape[1], matrix.shape[0]))
    # Thin factors: the first min(m, n) columns of u and rows of vh.
    u_keep = u[:, : singular.size][:, keep]
    v_keep = vh[: singular.size, :].T[:, keep]
    return v_keep @ ((1.0 / singular[keep])[:, None] * u_keep.T)


def lsqlin(a, b, c=None, d=None, tol=1e-13):
    design = np.asarray(a, dtype=float)
    if design.ndim != 2:
        raise PracmaError("Argument 'A' must be a numeric matrix.")
    right = np.asarray(b, dtype=float)
    if right.ndim == 1:
        if right.size != design.shape[0]:
            raise PracmaError("As vector argument 'b' must have 'nrow(A)' elements.")
        right = right.reshape(-1, 1)
    elif right.shape[0] != design.shape[0]:
        raise PracmaError("As Matrix argument 'b' must also have 'nrow(A)' rows.")
    if c is None and d is None:
        return qr_solve(design, right)
    if c is None or d is None:
        raise PracmaError("Condition 'C * x = d' not fully specified, 'C' or 'd' missing.")
    constraint = np.asarray(c, dtype=float)
    target = np.asarray(d, dtype=float)
    if target.ndim == 1:
        target = target.reshape(-1, 1)
    xc = pinv(constraint) @ target
    if np.any(np.abs(constraint @ xc - target) > tol):
        warnings.warn(
            "Precondition 'C * x = d' cannot be satisfied (within tolerance 'tol').",
            stacklevel=2,
        )
        return None
    basis = nullspace(constraint)
    columns = right.shape[1]
    if basis is None:
        return np.asarray(xc, dtype=float).reshape(-1)
    mapped = design @ basis
    residual = right - repmat(design @ xc, 1, columns)
    xn = pinv(mapped) @ residual
    return repmat(xc, 1, columns) + basis @ xn
