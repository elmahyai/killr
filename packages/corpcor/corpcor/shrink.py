"""Shrinkage estimators for variances, correlations, covariances, and partial correlations."""

from __future__ import annotations

import warnings

import numpy as np

from corpcor.matrix import EPS, Matrix, _MISSING, as_matrix, cov2cor, fast_svd, mpower, pseudoinverse, r_round

def check_weights(w, n: int) -> np.ndarray:
    if w is _MISSING:
        return np.full(n, 1.0 / n)
    w = np.asarray(w, dtype=float).reshape(-1)
    if w.size != n:
        raise ValueError("Weight vector has incompatible length")
    total = float(np.sum(w))
    if total != 1.0:
        w = w / total
    return w


def wt_moments(x, w=_MISSING):
    """Column means and bias-corrected weighted variances."""
    x = as_matrix(x)
    w = check_weights(w, x.shape[0])
    h1 = 1.0 / (1.0 - np.sum(w * w))
    mean = w @ x
    var = h1 * (w @ (x * x) - mean * mean)
    var = np.asarray(var, dtype=float).copy()
    var[var < EPS] = 0.0
    return {"mean": mean, "var": var}


def wt_var(xvec, w=_MISSING):
    """Bias-corrected weighted variance of one vector."""
    xvec = np.asarray(xvec, dtype=float).reshape(-1)
    w = check_weights(w, xvec.size)
    h1 = 1.0 / (1.0 - np.sum(w * w))
    center = np.sum(w * xvec)
    return float(h1 * np.sum(w * (xvec - center) ** 2))


def wt_scale(x, w=_MISSING, center=True, scale=True):
    """Center and scale columns with the weighted moments."""
    x = Matrix(as_matrix(x))
    w = check_weights(w, x.shape[0])
    moments = wt_moments(x, w)
    if center:
        x = Matrix(x - moments["mean"])
        x.scaled_center = moments["mean"]
    if scale:
        sc = np.sqrt(moments["var"])
        with np.errstate(divide="ignore", invalid="ignore"):
            scaled = np.asarray(x, dtype=float) / sc
        zeros = sc == 0.0
        scaled[:, zeros] = 0.0
        x = Matrix(scaled)
        x.scaled_center = moments["mean"] if center else None
        x.scaled_scale = sc
        if np.any(zeros):
            warnings.warn(
                f"{int(np.sum(zeros))} instances of variables with zero scale detected!",
                stacklevel=2,
            )
    return x


def _stamp(result, **attrs) -> Matrix:
    out = Matrix(result)
    for name, value in attrs.items():
        setattr(out, name, value)
    out.shrinkage = True
    return out


def estimate_lambda_var(x, w=_MISSING, verbose=True):
    """Optimal shrinkage intensity for the variance vector."""
    x = as_matrix(x)
    n = x.shape[0]
    if n < 3:
        raise ValueError("Sample size too small!")
    w = check_weights(w, n)
    w2 = float(np.sum(w * w))
    h1 = 1.0 / (1.0 - w2)
    h1w2 = w2 / (1.0 - w2)
    xc = np.asarray(wt_scale(x, w, center=True, scale=False))
    v = h1 * (w @ (xc * xc))
    target = float(np.median(v))
    if verbose:
        print("Estimating optimal shrinkage intensity lambda.var (variance vector): ", end="")
    zz = xc * xc
    q1 = w @ zz
    q2 = w @ (zz * zz) - q1 * q1
    numerator = float(np.sum(q2))
    denominator = float(np.sum((q1 - target / h1) ** 2))
    if denominator == 0:
        lambda_var = 1.0
    else:
        lambda_var = max(0.0, min(1.0, numerator / denominator * h1w2))
    if verbose:
        print(f"{r_round(lambda_var)} ")
    return lambda_var


def _offdiag_er2(xs2w: np.ndarray) -> float:
    """Twice the lower-triangle dot products, matching the cumsum form."""
    p = xs2w.shape[1]
    if p < 2:
        return 0.0
    cumulative = np.cumsum(xs2w[:, p - 1: 0: -1], axis=1)
    left = xs2w[:, p - 2:: -1]
    return float(2.0 * np.sum(left * cumulative))


def estimate_lambda(x, w=_MISSING, verbose=True):
    """Optimal shrinkage intensity for the correlation matrix."""
    x = as_matrix(x)
    n, p = x.shape
    if p == 1:
        return 1.0
    if n < 3:
        raise ValueError("Sample size too small!")
    w = check_weights(w, n)
    xs = wt_scale(x, w, center=True, scale=True)
    w2 = float(np.sum(w * w))
    h1w2 = w2 / (1.0 - w2)
    if verbose:
        print("Estimating optimal shrinkage intensity lambda (correlation matrix): ", end="")
    sw = np.sqrt(w)
    xsw = np.asarray(xs) * sw[:, None]
    factors = fast_svd(xsw)
    if factors["d"].size == 0:
        rebuilt = np.zeros_like(xsw)
    else:
        rebuilt = (factors["u"] * (factors["d"] ** 3)) @ factors["v"].T
    s_e2r = float(np.sum(xsw * rebuilt) - np.sum(np.sum(xsw * xsw, axis=0) ** 2))
    xs2w = (np.asarray(xs) ** 2) * sw[:, None]
    s_er2 = _offdiag_er2(xs2w)
    denominator = s_e2r
    numerator = s_er2 - s_e2r
    if denominator == 0:
        lambda_value = 1.0
    else:
        lambda_value = max(0.0, min(1.0, numerator / denominator * h1w2))
    if verbose:
        print(f"{r_round(lambda_value)} ")
    return lambda_value


def _resolve_lambda(x, lambda_value, w, verbose):
    if lambda_value is _MISSING:
        return estimate_lambda(x, w, verbose), True
    if lambda_value < 0:
        lambda_value = 0.0
    if lambda_value > 1:
        lambda_value = 1.0
    if verbose:
        print(
            "Specified shrinkage intensity lambda (correlation matrix): "
            f"{r_round(lambda_value)} "
        )
    return float(lambda_value), False


def _resolve_lambda_var(x, lambda_var, w, verbose):
    if lambda_var is _MISSING:
        return estimate_lambda_var(x, w, verbose), True
    if lambda_var < 0:
        lambda_var = 0.0
    if lambda_var > 1:
        lambda_var = 1.0
    if verbose:
        print(
            "Specified shrinkage intensity lambda.var (variance vector): "
            f"{r_round(lambda_var)} "
        )
    return float(lambda_var), False


def _power_from_svd(xs: Matrix, alpha, lambda_value, w, h1):
    zeros = np.asarray(xs.scaled_scale) == 0.0
    factors = fast_svd(np.asarray(xs))
    d = factors["d"]
    m = d.size
    p = xs.shape[1]
    if m == 0:
        utwu = np.zeros((0, 0))
    else:
        weighted_u = factors["u"] * w[:, None]
        utwu = factors["u"].T @ weighted_u
    c = d[:, None] * utwu * d[None, :]
    c = (1.0 - lambda_value) * h1 * c
    if c.size:
        c = (c + c.T) / 2.0
    if lambda_value == 0.0:
        if m < p - int(np.sum(zeros)):
            warnings.warn(
                "Estimated correlation matrix doesn't have full rank - pseudoinverse used for inversion.",
                stacklevel=3,
            )
        if m == 0:
            powr = np.zeros((p, p))
        else:
            powered = mpower(c, alpha)
            powr = factors["v"] @ powered @ factors["v"].T
    else:
        if m == 0:
            f = np.zeros((0, 0))
            powr = np.eye(p) * (lambda_value ** alpha)
        else:
            f = np.eye(m) - mpower(c / lambda_value + np.eye(m), alpha)
            powr = (np.eye(p) - factors["v"] @ f @ factors["v"].T) * (lambda_value ** alpha)
    np.fill_diagonal(powr, np.where(zeros, 1.0, np.diag(powr)))
    return powr, factors, zeros


def powcor_shrink(x, alpha=_MISSING, lambda_value=_MISSING, w=_MISSING, verbose=True):
    """Power of the shrinkage correlation matrix."""
    if alpha is _MISSING:
        raise ValueError("Please specify the exponent alpha!")
    x = as_matrix(x)
    lambda_value, estimated = _resolve_lambda(x, lambda_value, w, verbose)
    n = x.shape[0]
    w = check_weights(w, n)
    xs = wt_scale(x, w, center=True, scale=True)
    h1 = 1.0 / (1.0 - np.sum(w * w))
    p = xs.shape[1]
    if lambda_value == 1 or alpha == 0:
        powr = np.eye(p)
    elif alpha == 1:
        r0 = h1 * (np.asarray(xs) * np.sqrt(w)[:, None]).T @ (np.asarray(xs) * np.sqrt(w)[:, None])
        powr = (1.0 - lambda_value) * r0
        np.fill_diagonal(powr, 1.0)
    else:
        powr, _factors, _zeros = _power_from_svd(xs, alpha, lambda_value, w, h1)
    if verbose:
        print()
    return _stamp(powr, lambda_value=lambda_value, lambda_estimated=estimated)


def cor_shrink(x, lambda_value=_MISSING, w=_MISSING, verbose=True):
    """Shrinkage correlation matrix."""
    return powcor_shrink(x, alpha=1, lambda_value=lambda_value, w=w, verbose=verbose)


def invcor_shrink(x, lambda_value=_MISSING, w=_MISSING, verbose=True):
    """Inverse of the shrinkage correlation matrix."""
    return powcor_shrink(x, alpha=-1, lambda_value=lambda_value, w=w, verbose=verbose)


def var_shrink(x, lambda_var=_MISSING, w=_MISSING, verbose=True):
    """Shrinkage variance vector."""
    x = as_matrix(x)
    lambda_var, estimated = _resolve_lambda_var(x, lambda_var, w, verbose)
    v = wt_moments(x, w)["var"]
    target = float(np.median(v))
    vs = lambda_var * target + (1.0 - lambda_var) * v
    if verbose:
        print()
    return _stamp(vs, lambda_var=lambda_var, lambda_var_estimated=estimated)


def cov_shrink(x, lambda_value=_MISSING, lambda_var=_MISSING, w=_MISSING, verbose=True):
    """Shrinkage covariance matrix."""
    x = as_matrix(x)
    variances = var_shrink(x, lambda_var=lambda_var, w=w, verbose=verbose)
    scale = np.sqrt(np.asarray(variances))
    corr = powcor_shrink(x, alpha=1, lambda_value=lambda_value, w=w, verbose=verbose)
    result = scale[:, None] * np.asarray(corr) * scale[None, :]
    return _stamp(
        result,
        lambda_value=corr.lambda_value,
        lambda_estimated=corr.lambda_estimated,
        lambda_var=variances.lambda_var,
        lambda_var_estimated=variances.lambda_var_estimated,
    )


def invcov_shrink(x, lambda_value=_MISSING, lambda_var=_MISSING, w=_MISSING, verbose=True):
    """Inverse of the shrinkage covariance matrix."""
    x = as_matrix(x)
    variances = var_shrink(x, lambda_var=lambda_var, w=w, verbose=verbose)
    scale = np.sqrt(np.asarray(variances))
    invc = powcor_shrink(x, alpha=-1, lambda_value=lambda_value, w=w, verbose=verbose)
    with np.errstate(divide="ignore", invalid="ignore"):
        result = (1.0 / scale)[:, None] * np.asarray(invc) * (1.0 / scale)[None, :]
    return _stamp(
        result,
        lambda_value=invc.lambda_value,
        lambda_estimated=invc.lambda_estimated,
        lambda_var=variances.lambda_var,
        lambda_var_estimated=variances.lambda_var_estimated,
    )


def crossprod_powcor_shrink(x, y, alpha=_MISSING, lambda_value=_MISSING, w=_MISSING, verbose=True):
    """The shrinkage correlation to the power alpha, times y."""
    if alpha is _MISSING:
        raise ValueError("Please specify the exponent alpha!")
    x = as_matrix(x)
    y = as_matrix(y)
    p = x.shape[1]
    if y.shape[0] != p:
        raise ValueError(f"Matrix y must have {p} rows!")
    lambda_value, estimated = _resolve_lambda(x, lambda_value, w, verbose)
    n = x.shape[0]
    w = check_weights(w, n)
    xs = wt_scale(x, w, center=True, scale=True)
    h1 = 1.0 / (1.0 - np.sum(w * w))
    if lambda_value == 1 or alpha == 0:
        result = y.copy()
    else:
        zeros = np.asarray(xs.scaled_scale) == 0.0
        factors = fast_svd(np.asarray(xs))
        d = factors["d"]
        m = d.size
        if m == 0:
            utwu = np.zeros((0, 0))
        else:
            utwu = factors["u"].T @ (factors["u"] * w[:, None])
        c = (1.0 - lambda_value) * h1 * (d[:, None] * utwu * d[None, :])
        if c.size:
            c = (c + c.T) / 2.0
        if lambda_value == 0.0:
            if m < p - int(np.sum(zeros)):
                warnings.warn(
                    "Estimated correlation matrix doesn't have full rank - pseudoinverse used for inversion.",
                    stacklevel=2,
                )
            if m == 0:
                result = np.zeros_like(y)
            else:
                result = factors["v"] @ (mpower(c, alpha) @ (factors["v"].T @ y))
        else:
            if m == 0:
                result = y * (lambda_value ** alpha)
            else:
                f = np.eye(m) - mpower(c / lambda_value + np.eye(m), alpha)
                result = (y - factors["v"] @ (f @ (factors["v"].T @ y))) * (lambda_value ** alpha)
        result = np.array(result, dtype=float, copy=True)
        result[zeros, :] = y[zeros, :]
    if verbose:
        print()
    return _stamp(result, lambda_value=lambda_value, lambda_estimated=estimated)


def cor2pcor(m, tol=_MISSING):
    """Partial correlations from a covariance or correlation matrix."""
    precision = -pseudoinverse(m, tol)
    np.fill_diagonal(precision, -np.diag(precision))
    return cov2cor(precision)


def pcor2cor(m, tol=_MISSING):
    """Correlation matrix from partial correlations."""
    m = -as_matrix(m)
    np.fill_diagonal(m, -np.diag(m))
    inverted = pseudoinverse(m, tol)
    return cov2cor(inverted)


def pcor_shrink(x, lambda_value=_MISSING, w=_MISSING, verbose=True):
    """Shrinkage partial correlations. Standardized partial variances are attached."""
    inv = invcor_shrink(x, lambda_value=lambda_value, w=w, verbose=verbose)
    pc = -np.asarray(inv)
    np.fill_diagonal(pc, -np.diag(pc))
    spv = 1.0 / np.diag(pc)
    result = cov2cor(pc)
    return _stamp(
        result,
        lambda_value=inv.lambda_value,
        lambda_estimated=inv.lambda_estimated,
        spv=spv,
    )


def pvar_shrink(x, lambda_value=_MISSING, lambda_var=_MISSING, w=_MISSING, verbose=True):
    """Shrinkage partial variances."""
    precision = invcov_shrink(x, lambda_value=lambda_value, lambda_var=lambda_var, w=w, verbose=verbose)
    pvar = 1.0 / np.diag(np.asarray(precision))
    return _stamp(
        pvar,
        lambda_value=precision.lambda_value,
        lambda_estimated=precision.lambda_estimated,
        lambda_var=precision.lambda_var,
        lambda_var_estimated=precision.lambda_var_estimated,
    )


def format_shrinkage(value: Matrix) -> str:
    """The extra lines print.shrinkage adds after the matrix."""
    lines = [np.array2string(np.asarray(value), precision=7, suppress_small=False)]
    lines.append("")
    if value.lambda_estimated is not None:
        word = "(estimated)" if value.lambda_estimated else "(specified)"
        lines.append(
            f"Shrinkage intensity lambda (correlation matrix): {r_round(value.lambda_value)} {word}"
        )
    if value.lambda_var_estimated is not None:
        word = "(estimated)" if value.lambda_var_estimated else "(specified)"
        lines.append(
            "Shrinkage intensity lambda.var (variance vector): "
            f"{r_round(value.lambda_var)} {word}"
        )
    if value.spv is not None:
        lines.append('Standardized partial variances (i.e. PVAR/VAR) are attached (attribute "spv").')
    return "\n".join(lines)
