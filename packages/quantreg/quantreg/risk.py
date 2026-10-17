"""Markowitz sigma-risk portfolio. The mean constraint is one extra least-squares row."""

from __future__ import annotations

import numpy as np


def srisk(x, mu=0.07, lambda_=100000000, alpha=0.1, eps=0.0001):
    """Optimal sigma-risk weights. alpha is unused, matching the R argument list."""
    del alpha
    returns = np.asarray(x, dtype=float)
    n, _p = returns.shape
    means = returns.mean(axis=0)
    design = np.vstack([returns, means])
    response = design[:, 0].copy()
    response[n] = lambda_ * (response[n] - mu)
    design = design[:, 0:1] - design[:, 1:]
    ones = np.concatenate([np.ones(n), [0.0]])
    design = np.column_stack([ones, design])
    design[n, :] *= lambda_
    coefficients, _residuals, _rank, _singular = np.linalg.lstsq(design, response, rcond=None)
    fitted_row = float(design[n, :] @ coefficients)
    residual = response[n] - fitted_row
    if abs(residual) > eps:
        return "lambda too small?"
    weights = np.concatenate([[1.0 - np.sum(coefficients[1:])], coefficients[1:]])
    portfolio = returns @ weights
    mean = float(np.mean(portfolio))
    # R var() divides by n - 1.
    sigma = float(np.sqrt(np.var(portfolio, ddof=1)))
    return {"pihat": weights, "muhat": mean, "sigma": sigma}


def qrisk(x, alpha=(0.1, 0.3), w=(0.7, 0.3), mu=0.07, constraints=None, bound=None, lambda_=10000):
    """Choquet-risk portfolio. The mean constraint is two rows passed to rq.fit.hogg."""
    from quantreg.interior import rq_fit_hogg
    from quantreg.orderstats import kuantile

    returns = np.asarray(x, dtype=float)
    if returns.ndim == 1:
        returns = returns.reshape(-1, 1)
    alpha = np.atleast_1d(np.asarray(alpha, dtype=float))
    w = np.atleast_1d(np.asarray(w, dtype=float))
    if w.size != alpha.size:
        raise ValueError("length of w doesn't match length of alpha")
    n = returns.shape[0]
    means = returns.mean(axis=0)
    extra = np.array([lambda_ * (means[0] - mu), -lambda_ * (means[0] - mu)])
    bound = extra if bound is None else np.concatenate([np.asarray(bound, dtype=float).reshape(-1), extra])
    slope = lambda_ * (means[0] - means[1:])
    rows = np.vstack([slope, -slope])
    if constraints is not None:
        rows = np.vstack([np.asarray(constraints, dtype=float), rows])
    padded = np.column_stack([np.zeros((rows.shape[0], alpha.size)), rows])
    spread = returns[:, 0:1] - returns[:, 1:]
    fit = rq_fit_hogg(spread, returns[:, 0], taus=alpha, weights=w, constraints=padded, bound=bound)
    free = fit["coefficients"][alpha.size :]
    pihat = np.concatenate([[1.0 - free.sum()], free])
    fitted = returns @ pihat
    cutoff = kuantile(fitted, alpha)["y"]
    risk = 0.0
    for weight, level, prob in zip(w, cutoff, alpha):
        risk += float(weight) * float(np.sum(fitted[fitted < level])) / (n * float(prob))
    return {"pihat": pihat, "muhat": float(fitted.mean()), "qrisk": float(risk)}
