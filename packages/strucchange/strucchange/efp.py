"""Empirical fluctuation processes."""

import warnings

import numpy as np
from scipy import linalg

from strucchange.model import design_from_formula, lm_fit, match_arg
from strucchange.recresid import recresid
from strucchange.root import root_matrix

EFP_TYPES = (
    "Rec-CUSUM",
    "OLS-CUSUM",
    "Rec-MOSUM",
    "OLS-MOSUM",
    "RE",
    "ME",
    "Score-CUSUM",
    "Score-MOSUM",
    "fluctuation",
)


class Efp:
    """Result of ``efp``. ``process`` is the numeric fluctuation process."""

    def __init__(self, process, type, nreg, nobs, par, type_name, lim_process,
                 coefficients, sigma, formula, rescale, q12=None, colnames=None,
                 datatsp=None, tsp=None):
        self.process = process
        self.type = type
        self.nreg = int(nreg)
        self.nobs = int(nobs)
        self.par = par
        self.type_name = type_name
        self.lim_process = lim_process
        self.coefficients = coefficients
        self.sigma = float(sigma)
        self.formula = formula
        self.rescale = bool(rescale)
        self.q12 = q12
        self.colnames = colnames
        self.datatsp = datatsp
        self.tsp = tsp

    def __repr__(self):
        return f"Efp(type={self.type!r}, nobs={self.nobs}, nreg={self.nreg})"


def _sample_sdev(x, df=None):
    """``sd(x) * sqrt((length(x) - 1) / df)``. ``sd`` divides by ``n - 1``."""
    x = np.asarray(x, dtype=float).ravel()
    n = x.shape[0]
    if df is None:
        df = n - 1
    if n < 2:
        sd = np.nan
    else:
        sd = np.sqrt(np.sum((x - np.mean(x)) ** 2) / (n - 1))
    return float(sd * np.sqrt((n - 1) / df))


def _lrvar_sdev(x, df, kind):
    try:
        from sandwich import lrvar
    except ImportError as exc:
        raise ImportError("lrvar=TRUE needs the translated sandwich package") from exc
    x = np.asarray(x, dtype=float).ravel()
    long_run = np.asarray(lrvar(x, type=kind), dtype=float).reshape(-1)[0]
    scale = np.sqrt(long_run * x.shape[0])
    if df is not None:
        scale = scale * np.sqrt(x.shape[0] / df)
    return float(scale)


def _make_sdev(lrvar):
    if lrvar is False:
        return _sample_sdev
    kind = lrvar if isinstance(lrvar, str) else "Andrews"
    return lambda x, df=None: _lrvar_sdev(x, df, kind)


def _whiten(q12, process):
    """``t(chol2inv(chol(Q12)) %*% t(process))``."""
    upper = linalg.cholesky(q12, lower=False)
    inv_upper = linalg.solve_triangular(upper, np.eye(upper.shape[0]), lower=False)
    return process @ (inv_upper @ inv_upper.T)


def _moving_diff(cumsum, nh, n):
    """Window sums ``C[i + nh] - C[i]`` for the length-``n + 1`` cumulative sum."""
    return cumsum[nh:] - cumsum[: n - nh + 1]


def _q_factor(x, sigma, n, vcov, fit):
    if vcov is None:
        return root_matrix(x.T @ x) / (sigma * np.sqrt(n))
    covariance = np.asarray(vcov(fit), dtype=float)
    return root_matrix(np.linalg.inv(covariance)) / np.sqrt(n)


def _attach_time(process):
    nrow = int(np.shape(process)[0])
    frequency = nrow - 1
    if frequency == 0:
        return (0.0, 0.0, 1.0)
    return (0.0, 1.0, float(frequency))


def efp(formula, data=None, type="Rec-CUSUM", h=0.15, dynamic=False, rescale=True,
        lrvar=False, vcov=None):
    """Empirical fluctuation process for a linear regression formula.

    ``type`` accepts a unique prefix of the R choices. ``"fluctuation"`` is
    the recursive-estimates process. The default ``lrvar=False`` scales the
    ordinary sample standard deviation and does not call sandwich.
    """
    if isinstance(formula, str):
        y, x, x_names = design_from_formula(formula, data)
    elif hasattr(formula, "x") and hasattr(formula, "y"):
        x = np.asarray(formula.x, dtype=float)
        y = np.asarray(formula.y, dtype=float).ravel()
        x_names = [f"x{j + 1}" for j in range(x.shape[1])]
    else:
        raise TypeError("formula must be a string such as 'y ~ x'")

    type = match_arg(type, EFP_TYPES)
    if type == "fluctuation":
        type = "RE"
    sdev = _make_sdev(lrvar)
    n = int(x.shape[0])
    if dynamic:
        x = np.column_stack([y[:-1], x[1:, :]])
        x_names = ["lag", *x_names]
        y = y[1:]
        n = n - 1
    k = int(x.shape[1])
    h = float(h)
    par = None
    q12 = None
    colnames = None

    if type == "Rec-CUSUM":
        w = recresid(x, y)
        sigma = sdev(w)
        process = np.cumsum(np.concatenate([[0.0], w])) / (sigma * np.sqrt(n - k))
        type_name = "Recursive CUSUM test"
        lim_process = "Brownian motion"
    elif type == "OLS-CUSUM":
        fit = lm_fit(x, y)
        sigma = sdev(fit.residuals, df=fit.df_residual)
        process = np.cumsum(np.concatenate([[0.0], fit.residuals])) / (sigma * np.sqrt(n))
        type_name = "OLS-based CUSUM test"
        lim_process = "Brownian bridge"
    elif type == "Rec-MOSUM":
        w = recresid(x, y)
        nw = n - k
        nh = int(np.floor(nw * h))
        # rep(0, nw - nh) is one short; assigning the last index extends it.
        process = np.empty(nw - nh + 1, dtype=float)
        for i in range(process.shape[0]):
            process[i] = np.sum(w[i:i + nh])
        sigma = sdev(w, df=nw - k)
        process = process / (sigma * np.sqrt(nw))
        par = h
        type_name = "Recursive MOSUM test"
        lim_process = "Brownian motion increments"
    elif type == "OLS-MOSUM":
        fit = lm_fit(x, y)
        sigma = sdev(fit.residuals, df=fit.df_residual)
        nh = int(np.floor(n * h))
        cumsum = np.cumsum(np.concatenate([[0.0], fit.residuals]))
        process = _moving_diff(cumsum, nh, n) / (sigma * np.sqrt(n))
        par = h
        type_name = "OLS-based MOSUM test"
        lim_process = "Brownian bridge increments"
    elif type == "RE":
        fit = lm_fit(x, y)
        beta_hat = fit.coefficients
        sigma = sdev(fit.residuals, df=fit.df_residual)
        raw = np.zeros((k, n - k + 1), dtype=float)
        q12 = _q_factor(x, sigma, n, vcov, fit)
        warned = False
        if rescale:
            for i in range(k, n):
                if vcov is not None and not warned:
                    warnings.warn("custom vcov not implemented yet if rescale = TRUE")
                    warned = True
                window = x[:i, :]
                mi = lm_fit(window, y[:i])
                qi = root_matrix(window.T @ window) / (sigma * np.sqrt(i))
                raw[:, i - k] = qi @ (mi.coefficients - beta_hat)
        else:
            for i in range(k, n):
                mi = lm_fit(x[:i, :], y[:i])
                raw[:, i - k] = q12 @ (mi.coefficients - beta_hat)
        wide = np.column_stack([np.zeros(k), raw])
        scale = np.arange(k - 1, n + 1, dtype=float)
        process = wide.T * scale[:, None] / np.sqrt(n)
        colnames = list(x_names)
        type_name = "RE test (recursive estimates test)"
        lim_process = "Brownian bridge"
    elif type == "ME":
        fit = lm_fit(x, y)
        beta_hat = fit.coefficients
        sigma = sdev(fit.residuals, df=fit.df_residual)
        nh = int(np.floor(n * h))
        raw = np.zeros((k, n - nh + 1), dtype=float)
        q12 = _q_factor(x, sigma, n, vcov, fit)
        for i in range(0, n - nh + 1):
            window_x = x[i:i + nh, :]
            window_y = y[i:i + nh]
            mi = lm_fit(window_x, window_y)
            if rescale:
                if vcov is None:
                    factor = root_matrix(window_x.T @ window_x) / (sigma * np.sqrt(nh))
                else:
                    covariance = np.asarray(vcov(mi), dtype=float)
                    factor = root_matrix(np.linalg.inv(covariance)) / np.sqrt(nh)
            else:
                factor = q12
            raw[:, i] = factor @ (mi.coefficients - beta_hat)
        process = nh * raw.T / np.sqrt(n)
        par = h
        colnames = list(x_names)
        type_name = "ME test (moving estimates test)"
        lim_process = "Brownian bridge increments"
    elif type == "Score-CUSUM":
        fit = lm_fit(x, y)
        e = np.asarray(fit.residuals, dtype=float).ravel()
        sigma2 = float(np.sum(e ** 2) / n)
        increments = np.column_stack([x * e[:, None], e ** 2 - sigma2]) / np.sqrt(n)
        q12 = root_matrix(increments.T @ increments)
        cumsum = np.cumsum(np.vstack([np.zeros((1, increments.shape[1])), increments]), axis=0)
        process = _whiten(q12, cumsum)
        colnames = list(x_names) + ["(Variance)"]
        type_name = "Score-based CUSUM test"
        lim_process = "Brownian bridge"
    elif type == "Score-MOSUM":
        fit = lm_fit(x, y)
        e = np.asarray(fit.residuals, dtype=float).ravel()
        sigma2 = float(np.sum(e ** 2) / n)
        nh = int(np.floor(n * h))
        increments = np.column_stack([x * e[:, None], e ** 2 - sigma2]) / np.sqrt(n)
        q12 = root_matrix(increments.T @ increments)
        cumsum = np.cumsum(np.vstack([np.zeros((1, increments.shape[1])), increments]), axis=0)
        window = _moving_diff(cumsum, nh, n)
        process = _whiten(q12, window)
        par = h
        colnames = list(x_names) + ["(Variance)"]
        type_name = "Score-based MOSUM test"
        lim_process = "Brownian bridge increments"
    else:
        raise ValueError(f"unknown efp type {type!r}")

    full = lm_fit(x, y)
    sigma_hat = float(np.sqrt(np.sum(full.residuals ** 2) / full.df_residual))
    return Efp(
        process=np.asarray(process, dtype=float),
        type=type,
        nreg=k,
        nobs=n,
        par=par,
        type_name=type_name,
        lim_process=lim_process,
        coefficients=full.coefficients,
        sigma=sigma_hat,
        formula=formula if isinstance(formula, str) else None,
        rescale=rescale,
        q12=q12,
        colnames=colnames,
        datatsp=(0.0, 1.0, float(n)),
        tsp=_attach_time(process),
    )
