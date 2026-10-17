"""Formula design matrices and a QR least-squares fit.

``lm_fit`` follows ``stats::lm.fit``: column-pivoted QR, rank from the
leading diagonal against ``tol * |R[1, 1]|``, and ``NA`` coefficients
where the column is not in the rank. ``recresid`` turns those ``NA``
values into zeros before the residual update.
"""

from __future__ import annotations

import inspect

import numpy as np
from scipy import linalg


def match_arg(arg, choices):
    """``match.arg``: an exact match wins, otherwise one unique prefix.

    ``None`` is R's ``NULL`` and selects the first choice.
    """
    choices = tuple(choices)
    if arg is None:
        return choices[0]
    if isinstance(arg, (list, tuple)) and tuple(arg) == choices:
        return choices[0]
    if not isinstance(arg, str):
        raise TypeError("'arg' must be NULL or a character vector")
    exact = [choice for choice in choices if choice == arg]
    if len(exact) == 1:
        return exact[0]
    if len(exact) > 1:
        raise ValueError("there is more than one match in 'match.arg'")
    partial = [choice for choice in choices if choice.startswith(arg)]
    if len(partial) == 1:
        return partial[0]
    if not partial:
        quoted = ", ".join(repr(choice) for choice in choices)
        raise ValueError(f"'arg' should be one of {quoted}")
    raise ValueError("there is more than one match in 'match.arg'")


class LmFit:
    def __init__(self, coefficients, residuals, rank, df_residual, r, pivot):
        self.coefficients = coefficients
        self.residuals = residuals
        self.rank = int(rank)
        self.df_residual = int(df_residual)
        self.r = r
        self.pivot = pivot


def lm_fit(x, y, tol=1e-7):
    """Column-pivoted least squares, with deficient coefficients left missing."""
    x = np.asarray(x, dtype=float)
    if x.ndim == 1:
        x = x.reshape(-1, 1)
    y = np.asarray(y, dtype=float).ravel()
    n, p = x.shape
    if y.shape[0] != n:
        raise ValueError("incompatible dimensions")
    q, r, piv = linalg.qr(x, mode="economic", pivoting=True)
    piv = np.asarray(piv, dtype=int)
    rank = 0
    m = min(n, p)
    if m > 0 and r[0, 0] != 0.0:
        thresh = tol * abs(r[0, 0])
        for i in range(m):
            if abs(r[i, i]) > thresh:
                rank = i + 1
    coef_p = np.full(p, np.nan)
    if rank:
        qty = q[:, :rank].T @ y
        coef_p[:rank] = linalg.solve_triangular(r[:rank, :rank], qty, lower=False)
    coefficients = np.full(p, np.nan)
    coefficients[piv] = coef_p
    beta = np.where(np.isnan(coefficients), 0.0, coefficients)
    residuals = y - x @ beta
    return LmFit(coefficients, residuals, rank, n - rank, r, piv)


def coef_zero(coefficients):
    """Replace QR ``NA`` coefficients with 0, as ``recresid`` does."""
    cf = np.array(coefficients, dtype=float, copy=True).ravel()
    cf[np.isnan(cf)] = 0.0
    return cf


def x_inverse(fit: LmFit, k: int):
    """``chol2inv`` of the leading R factor, scattered back by the pivot."""
    rval = np.zeros((k, k), dtype=float)
    rank = fit.rank
    if rank == 0:
        return rval
    wi = fit.pivot[:rank]
    factor = fit.r[:rank, :rank]
    inv = linalg.solve_triangular(factor, np.eye(rank), lower=False)
    rval[np.ix_(wi, wi)] = inv @ inv.T
    return rval


def _caller_namespace():
    frame = inspect.currentframe()
    try:
        while frame is not None:
            module = frame.f_globals.get("__name__", "")
            if not str(module).startswith("strucchange"):
                return frame.f_locals
            frame = frame.f_back
        return {}
    finally:
        del frame


def _lookup(name, data):
    if data is not None and name in data:
        return data[name]
    env = _caller_namespace()
    if name in env:
        return env[name]
    raise NameError(f"object '{name}' not found")


def _parse_rhs(rhs):
    compact = "".join(rhs.split())
    if compact == "":
        raise ValueError("formula has no regressors")
    parts = [part for part in compact.replace("-", "+-").split("+") if part != ""]
    intercept = True
    terms = []
    for tok in parts:
        if tok in ("1", "+1"):
            intercept = True
        elif tok == "-1":
            intercept = False
        elif tok in ("0", "+0", "-0"):
            intercept = False
        elif tok.startswith("-"):
            raise ValueError(f"removing term '{tok[1:]}' is not supported")
        else:
            terms.append(tok)
    return terms, intercept


def design_from_formula(formula, data=None):
    """Build ``y`` and the model matrix for a linear formula such as ``y ~ x``."""
    if not isinstance(formula, str) or "~" not in formula:
        raise ValueError("formula must be a string such as 'y ~ x'")
    left, right = formula.split("~", 1)
    response = left.strip()
    if response == "":
        raise ValueError("formula has no response")
    y = np.asarray(_lookup(response, data), dtype=float).ravel()
    terms, intercept = _parse_rhs(right.strip())
    columns = []
    names = []
    if intercept:
        columns.append(np.ones(y.shape[0], dtype=float))
        names.append("(Intercept)")
    for term in terms:
        values = np.asarray(_lookup(term, data), dtype=float)
        if values.ndim == 0:
            values = np.full(y.shape[0], float(values))
        if values.ndim == 1:
            if values.shape[0] != y.shape[0]:
                raise ValueError("variable lengths differ")
            columns.append(values)
            names.append(term)
        elif values.ndim == 2:
            if values.shape[0] != y.shape[0]:
                raise ValueError("variable lengths differ")
            for j in range(values.shape[1]):
                columns.append(values[:, j])
                names.append(f"{term}{j + 1}")
        else:
            raise ValueError(f"cannot use '{term}' in a formula")
    if not columns:
        raise ValueError("formula has no regressors")
    return y, np.column_stack(columns), names
