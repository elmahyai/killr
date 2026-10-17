"""Empirical likelihood profiles and the nested correlation bootstrap.

``EL.profile`` and ``EEF.profile`` in boot 1.3-32 still use two S-PLUS
leftovers. ``nlm`` returns ``estimate``, not ``x``, and a bare ``NA`` is
logical, so the installed ``EL.profile`` aborts. The Poisson fit looks up
``zero``, which is a function in the package namespace, so ``EEF.profile``
aborts too. The profiles below are those same calculations with the estimate
and a numeric constraint value, and with a zero response vector. ``lik.CI``
follows the installed function: ``y ~ x + x^2`` is linear, and the missing
third coefficient makes an interior endpoint missing.
"""

from __future__ import annotations

import math

import numpy as np

__all__ = ["eef_profile", "el_profile", "lik_ci", "nested_corr"]

_XMAX = 1.7976931348623157e308
_EPS = float(np.finfo(np.float64).eps)


def _as_float_array(values) -> np.ndarray:
    return np.asarray(values, dtype=np.float64)


def _finite_float(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    return number


def _nlm(func, x: float) -> dict:
    """Scalar ``nlm`` with the defaults ``EL.profile`` uses.

    A non-finite objective is the largest finite double, which is how ``nlm``
    treats a numeric missing value. A missing value at the start returns
    immediately with code 1 and the start unchanged.
    """
    gradtol = 1e-6
    steptol = 1e-6
    iterlim = 100
    ndigit = 12
    fscale = 1.0
    typsize = 1.0
    eta = 10 ** (-ndigit / 2.0)
    stepmax = max(1000.0 * abs(x / typsize), 1000.0)

    def ev(z: float) -> float:
        number = _finite_float(func(z))
        if number is None:
            return _XMAX
        return number

    def grad(z: float, fz: float) -> float:
        step = max(abs(z), typsize) * eta
        return (ev(z + step) - fz) / step

    ev(x)
    ev(x)
    if _finite_float(func(x)) is None:
        return {
            "minimum": _XMAX,
            "estimate": x,
            "gradient": 0.0,
            "code": 1,
            "iterations": 0,
        }

    fx = ev(x)
    curvature = 1.0
    iterations = 0
    previous_gradient = None
    previous_x = None
    while iterations <= iterlim:
        gradient = grad(x, fx)
        relative = abs(gradient) * max(abs(x), typsize) / max(abs(fx), fscale)
        if iterations > 0 and relative <= gradtol:
            return {
                "minimum": fx,
                "estimate": x,
                "gradient": gradient,
                "code": 1,
                "iterations": iterations,
            }
        if previous_gradient is not None:
            step_x = x - previous_x
            step_g = gradient - previous_gradient
            if step_x != 0.0 and step_g * step_x > 0.0:
                curvature = step_g / step_x
        if curvature == 0.0 or not math.isfinite(curvature):
            curvature = 1.0
        direction = -gradient / curvature
        if abs(direction) > stepmax:
            direction = math.copysign(stepmax, direction)
        slope = gradient * direction
        if slope >= 0.0:
            curvature = 1.0
            direction = -gradient
            if abs(direction) > stepmax:
                direction = math.copysign(stepmax, direction)
            slope = gradient * direction

        alam = 1.0
        alam_prev = 1.0
        f_prev = fx
        alamin = steptol * max(abs(x), typsize) / max(abs(direction), 1e-30)
        accepted = False
        f_new = fx
        x_new = x
        for _ in range(40):
            x_new = x + alam * direction
            f_new = ev(x_new)
            if f_new <= fx + 1e-4 * alam * slope:
                accepted = True
                break
            if alam < alamin:
                break
            if alam == 1.0:
                denom = f_new - fx - slope
                alam2 = -slope / (2.0 * denom) if denom != 0.0 else 0.1
            else:
                rhs1 = f_new - fx - alam * slope
                rhs2 = f_prev - fx - alam_prev * slope
                span = alam - alam_prev
                a_coef = (rhs1 / (alam * alam) - rhs2 / (alam_prev * alam_prev)) / span
                b_coef = (
                    -alam_prev * rhs1 / (alam * alam) + alam * rhs2 / (alam_prev * alam_prev)
                ) / span
                if a_coef == 0.0:
                    alam2 = -slope / (2.0 * b_coef) if b_coef != 0.0 else 0.5 * alam
                else:
                    disc = b_coef * b_coef - 3.0 * a_coef * slope
                    if disc < 0.0:
                        alam2 = 0.5 * alam
                    elif b_coef <= 0.0:
                        alam2 = (-b_coef + math.sqrt(disc)) / (3.0 * a_coef)
                    else:
                        alam2 = -slope / (b_coef + math.sqrt(disc))
                if alam2 > 0.5 * alam:
                    alam2 = 0.5 * alam
            if not math.isfinite(alam2) or alam2 <= 0.0:
                alam2 = 0.1 * alam
            if alam2 < 0.1 * alam:
                alam2 = 0.1 * alam
            f_prev = f_new
            alam_prev = alam
            alam = alam2

        if not accepted:
            hc = max(abs(x), typsize) * (10 ** (-ndigit / 3.0))
            f_plus = ev(x + hc)
            f_minus = ev(x - hc)
            central_ok = (
                hc != 0.0
                and math.isfinite(f_plus)
                and math.isfinite(f_minus)
                and f_plus < _XMAX / 10.0
                and f_minus < _XMAX / 10.0
            )
            if central_ok:
                g_central = (f_plus - f_minus) / (2.0 * hc)
                hessian = (f_plus - 2.0 * fx + f_minus) / (hc * hc)
                if hessian > 0.0 and math.isfinite(g_central):
                    newton = -g_central / hessian
                    if abs(newton) > stepmax:
                        newton = math.copysign(stepmax, newton)
                    x2 = x + newton
                    f2 = ev(x2)
                    if f2 < fx:
                        x = x2
                        fx = f2
                        iterations += 1
                        f_plus = ev(x + hc)
                        f_minus = ev(x - hc)
                        gradient = (f_plus - f_minus) / (2.0 * hc)
                        relative = abs(gradient) * max(abs(x), typsize) / max(abs(fx), fscale)
                        code = 1 if relative <= gradtol else 2
                        return {
                            "minimum": fx,
                            "estimate": x,
                            "gradient": gradient,
                            "code": code,
                            "iterations": iterations,
                        }
            return {
                "minimum": fx,
                "estimate": x,
                "gradient": gradient,
                "code": 3,
                "iterations": iterations,
            }

        step_relative = abs(x_new - x) / max(abs(x_new), typsize)
        previous_gradient = gradient
        previous_x = x
        x = x_new
        fx = f_new
        iterations += 1
        if step_relative <= steptol:
            return {
                "minimum": fx,
                "estimate": x,
                "gradient": grad(x, fx),
                "code": 2,
                "iterations": iterations,
            }
        if iterations >= iterlim:
            return {
                "minimum": fx,
                "estimate": x,
                "gradient": grad(x, fx),
                "code": 4,
                "iterations": iterations,
            }
    return {
        "minimum": fx,
        "estimate": x,
        "gradient": grad(x, fx),
        "code": 4,
        "iterations": iterations,
    }


def _default_u(y, t):
    return _as_float_array(y) - t


def el_profile(y, tmin=None, tmax=None, n_t: int = 25, u=None) -> np.ndarray:
    """Profile empirical log likelihood on a grid from ``tmin`` to ``tmax``.

    Returns an ``n_t`` by 3 matrix: the parameter, the centered profile log
    likelihood, and the Lagrange multiplier. ``u`` defaults to ``y - t``.
    """
    values = _as_float_array(y)
    if tmin is None:
        tmin = float(np.min(values)) + 0.1
    if tmax is None:
        tmax = float(np.max(values)) - 0.1
    if u is None:
        u = _default_u
    n_t = int(n_t)
    profile = np.full((n_t, 3), np.nan, dtype=np.float64)
    lam = 0.001
    for it in range(n_t):
        t = tmin + ((tmax - tmin) * it) / (n_t - 1)
        constraint = _as_float_array(u(values, t)).reshape(-1)

        def objective(lamb, constraint=constraint):
            temp = 1.0 + lamb * constraint
            if np.any(temp <= 0.0) or not np.all(np.isfinite(temp)):
                return float("nan")
            return float(-np.sum(np.log(temp)))

        fit = _nlm(objective, lam)
        attempt = 1
        while fit["code"] > 2 and attempt < 20:
            attempt += 1
            lam = lam / 5.0
            fit = _nlm(objective, lam)
        estimate = float(fit["estimate"])
        profile[it, 0] = t
        profile[it, 1] = objective(estimate)
        profile[it, 2] = estimate
        lam = estimate
    profile[:, 1] = profile[:, 1] - np.max(profile[:, 1])
    return profile


def _poisson_zero(psi: np.ndarray) -> tuple[float, np.ndarray]:
    """No-intercept Poisson log-link fit of a zero response on ``psi``.

    This is ``glm(rep(0, n) ~ psi - 1, family = poisson(link = "log"))``.
    The log link floors the mean and its derivative at double epsilon.
    """
    psi = _as_float_array(psi).reshape(-1)
    if psi.size == 0 or float(np.dot(psi, psi)) == 0.0:
        return float("nan"), np.full(psi.size, np.nan, dtype=np.float64)
    eta = np.full(psi.size, math.log(0.1), dtype=np.float64)
    mu = np.maximum(np.exp(eta), _EPS)
    dev_old = float(2.0 * np.sum(mu))
    beta = float("nan")
    for _ in range(25):
        mu_eta = np.maximum(np.exp(eta), _EPS)
        z = eta + (0.0 - mu) / mu_eta
        weight = np.sqrt((mu_eta * mu_eta) / mu)
        xw = psi * weight
        sw = float(np.dot(xw, xw))
        if sw == 0.0 or not math.isfinite(sw):
            break
        beta = float(np.dot(xw, z * weight) / sw)
        eta = psi * beta
        mu = np.maximum(np.exp(eta), _EPS)
        deviance = float(2.0 * np.sum(mu))
        if abs(deviance - dev_old) / (0.1 + abs(deviance)) < 1e-8:
            break
        dev_old = deviance
    return beta, mu


def eef_profile(y, tmin=None, tmax=None, n_t: int = 25, u=None) -> np.ndarray:
    """Empirical exponential family profile on a grid from ``tmin`` to ``tmax``.

    Returns ``n_t + 1`` rows and 4 columns: the parameter, two centered
    log-likelihood versions, and the Lagrange multiplier. ``u`` defaults to
    ``y - t``.
    """
    values = _as_float_array(y)
    if tmin is None:
        tmin = float(np.min(values)) + 0.1
    if tmax is None:
        tmax = float(np.max(values)) - 0.1
    if u is None:
        u = _default_u
    n_t = int(n_t)
    profile = np.full((n_t + 1, 4), np.nan, dtype=np.float64)
    for it in range(n_t + 1):
        t = tmin + (tmax - tmin) * it / n_t
        psi = _as_float_array(u(values, t)).reshape(-1)
        beta, fitted = _poisson_zero(psi)
        total = float(np.sum(fitted))
        profile[it, 0] = t
        if total > 0.0 and np.all(np.isfinite(fitted)) and np.all(fitted > 0.0):
            profile[it, 1] = float(np.sum(np.log(fitted) - math.log(total)))
            profile[it, 2] = float(np.sum(fitted - 1.0))
        profile[it, 3] = beta
    profile[:, 1] = profile[:, 1] - np.max(profile[:, 1])
    profile[:, 2] = profile[:, 2] - np.max(profile[:, 2])
    return profile


def _sprintf_f(value) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "NA"
    if math.isnan(number):
        return "NA"
    return f"{number:.6f}"


def _extreme_index(mask_true: np.ndarray, mask_na: np.ndarray, take_max: bool):
    """``min`` or ``max`` of the 1-based indices selected by a logical test.

    A missing comparison makes the result missing. An empty selection is
    ``Inf`` for ``min`` and ``-Inf`` for ``max``.
    """
    if np.any(mask_na):
        return float("nan")
    hits = np.flatnonzero(mask_true)
    if hits.size == 0:
        return float("-inf") if take_max else float("inf")
    chosen = int(hits[-1] if take_max else hits[0]) + 1
    return float(chosen)


def _interior_end(theta: np.ndarray, likelihood: np.ndarray, lim, center: float) -> float:
    """Endpoint from ``lm(y ~ x + x^2)``, which has no squared term."""
    if not math.isfinite(center):
        raise ValueError("0 (non-NA) cases")
    n = theta.shape[0]
    positions = (int(center) - 2, int(center) - 1, int(center))
    x = np.empty(3, dtype=np.float64)
    y = np.empty(3, dtype=np.float64)
    for slot, position in enumerate(positions):
        if position < 0 or position >= n:
            x[slot] = np.nan
            y[slot] = np.nan
        else:
            x[slot] = theta[position]
            y[slot] = likelihood[position] - lim
    if not np.any(np.isfinite(x) & np.isfinite(y)):
        raise ValueError("0 (non-NA) cases")
    return float("nan")


def lik_ci(like, lim) -> np.ndarray:
    """Interval where the profile likelihood exceeds ``lim``.

    ``like`` is a matrix with the parameter in column 1 and the likelihood in
    column 2. The installed formula does not fit a square, so an interior
    endpoint is missing. The result is ``-Inf`` or ``Inf`` when the likelihood
    is still above ``lim`` at that end of the grid.
    """
    grid = _as_float_array(like)
    if grid.ndim != 2:
        raise ValueError("incorrect number of dimensions")
    theta = grid[:, 0]
    likelihood = grid[:, 1]
    n = int(likelihood.shape[0])
    try:
        limit = float(lim)
    except (TypeError, ValueError):
        limit = float("nan")
    if math.isnan(limit) or (n > 0 and bool(np.any(np.isnan(likelihood)))):
        raise ValueError(f"likelihood never exceeds {_sprintf_f(limit)}")
    if n == 0:
        left = float("inf")
        right = float("-inf")
    else:
        above = likelihood > limit
        none = np.zeros(n, dtype=bool)
        left = _extreme_index(above, none, take_max=False)
        right = _extreme_index(above, none, take_max=True)
    if left == right:
        raise ValueError(f"likelihood exceeds {_sprintf_f(limit)} at only one point")
    if left == 1.0:
        lower = float("-inf")
    else:
        lower = _interior_end(theta, likelihood, limit, left)
    if right == float(n):
        upper = float("inf")
    else:
        upper = _interior_end(theta, likelihood, limit, right)
    return np.array([lower, upper], dtype=np.float64)


def _repeat_rows(n: int, weights: np.ndarray) -> np.ndarray:
    times = np.rint(n * weights).astype(np.int64)
    return np.repeat(np.arange(n, dtype=np.int64), times)


def _corr_fun(data: np.ndarray, weights=None) -> np.ndarray:
    """Weighted correlation and the nested-bootstrap variance piece."""
    rows = data.shape[0]
    if weights is None:
        weights = np.full(rows, 1.0 / rows, dtype=np.float64)
    else:
        weights = _as_float_array(weights).reshape(-1)
    weights = weights / np.sum(weights)
    x = data[:, 0]
    y = data[:, 1]
    mean_x = float(np.sum(x * weights))
    mean_y = float(np.sum(y * weights))
    var_x = float(np.sum(x * x * weights) - mean_x * mean_x)
    var_y = float(np.sum(y * y * weights) - mean_y * mean_y)
    scale = math.sqrt(var_x * var_y) if var_x > 0.0 and var_y > 0.0 else float("nan")
    if not math.isfinite(scale) or scale == 0.0:
        return np.array([float("nan"), float("nan")], dtype=np.float64)
    rho = float((np.sum(x * y * weights) - mean_x * mean_y) / scale)
    chosen = _repeat_rows(rows, weights)
    scale_x = math.sqrt(var_x)
    scale_y = math.sqrt(var_y)
    us = (x[chosen] - mean_x) / scale_x
    xs = (y[chosen] - mean_y) / scale_y
    influence = us * xs - 0.5 * rho * (us * us + xs * xs)
    return np.array([rho, float(np.sum(influence * influence) / (rows * rows))], dtype=np.float64)


def nested_corr(data, w, t0, M) -> np.ndarray:
    """Nested bootstrap pivot and its tail probability for a correlation.

    ``data`` is used as a numeric matrix. ``w`` is the outer weight vector,
    ``t0`` is the correlation under test, and ``M`` is the number of inner
    bootstrap replicates. The inner bootstrap is ``boot(..., stype="w")``.
    """
    matrix = _as_float_array(data)
    if matrix.ndim == 1:
        matrix = matrix.reshape(-1, 1)
    weights = _as_float_array(w).reshape(-1)
    rows = _repeat_rows(matrix.shape[0], weights)
    statistic = _corr_fun(matrix, weights)
    z = (float(statistic[0]) - float(t0)) / math.sqrt(float(statistic[1]))
    from boot.resample import boot as resample_boot

    nested = resample_boot(matrix[rows], _corr_fun, R=M, stype="w")
    replicates = np.asarray(nested.t if hasattr(nested, "t") else nested["t"], dtype=np.float64)
    z_nested = (replicates[:, 0] - statistic[0]) / np.sqrt(replicates[:, 1])
    if np.any(~np.isfinite(z_nested)):
        probability = float("nan")
    else:
        probability = float(np.sum(z_nested < z) / (int(M) + 1))
    return np.array([z, probability], dtype=np.float64)
