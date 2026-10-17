"""Generalized least squares linear models (MASS lm.gls)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from mass.addterm import _model_matrix, _parse_rhs_terms, _qr_coef, _split_formula
from mass.errors import MassError
from mass.rlm import _match_arg


def _expand_dot_formula(formula: str, data: dict) -> str:
    resp, rhs = _split_formula(formula)
    intercept, terms = _parse_rhs_terms(rhs)
    if "." not in terms:
        return formula
    predictors = [key for key in data if key != resp]
    expanded: list[str] = []
    for term in terms:
        if term == ".":
            expanded.extend(predictors)
        else:
            expanded.append(term)
    rhs_out = " + ".join(expanded)
    if intercept:
        rhs_out = ("1 + " + rhs_out) if rhs_out else "1"
    elif not rhs_out:
        rhs_out = "0"
    return f"{resp} ~ {rhs_out}"


def _lm_fit(x: np.ndarray, y: np.ndarray) -> dict[str, Any]:
    """QR least squares matching ``stats::lm.fit`` on a full-rank design."""
    x = np.asarray(x, dtype=float)
    if x.ndim == 1:
        x = x.reshape(-1, 1)
    y = np.asarray(y, dtype=float).reshape(-1)
    n, p = x.shape
    if y.shape[0] != n:
        raise MassError("incompatible dimensions in lm.fit")
    q, r = np.linalg.qr(x, mode="reduced")
    coef, rank = _qr_coef(x, y)
    fitted = x @ coef
    resid = y - fitted
    df_res = int(n - rank)
    return {
        "coefficients": coef,
        "residuals": resid,
        "fitted.values": fitted,
        "rank": rank,
        "df.residual": df_res,
        "qr": (q, r),
    }


def _gls_transform(w: np.ndarray, *, inverse: bool) -> tuple[np.ndarray, np.ndarray]:
    w = np.asarray(w, dtype=float)
    if w.ndim != 2 or w.shape[0] != w.shape[1]:
        raise MassError("dim(W) is not correct")
    n = w.shape[0]
    values, vectors = np.linalg.eigh(w)
    if np.any(values <= 0):
        raise MassError("'W' is not positive definite")
    if inverse:
        root = values ** (-0.5)
        inv_root = values ** 0.5
    else:
        root = values ** 0.5
        inv_root = values ** (-0.5)
    a = (root[:, None] * vectors.T)
    ainv = vectors @ (inv_root[:, None] * np.eye(n))
    return a, ainv


@dataclass
class LmGlsFit:
    coefficients: np.ndarray
    residuals: np.ndarray
    fitted_values: np.ndarray
    rank: int
    df_residual: int
    terms: Any = None
    call: Any = None
    model: dict | None = None
    x: np.ndarray | None = None
    y: np.ndarray | None = None
    na_action: Any = None
    xlevels: Any = None
    contrasts: Any = None
    effects: np.ndarray | None = None
    qr: Any = None


def lm_gls(
    formula: str,
    data: dict | None = None,
    W: np.ndarray | None = None,
    *,
    subset: Any = None,
    na_action: Any = None,
    inverse: bool = False,
    method: str | None = "qr",
    model: bool = False,
    x: bool = False,
    y: bool = False,
    contrasts: Any = None,
    **kwargs: Any,
) -> LmGlsFit | dict[str, Any]:
    """Fit a linear model by generalized least squares."""
    if data is None:
        raise MassError("'data' must be supplied")
    if W is None:
        raise MassError("'W' is missing")
    method = _match_arg(method, ["qr", "model.frame"])
    if subset is not None or na_action is not None:
        raise MassError("subset and na.action are not implemented for lm.gls")
    if contrasts is not None:
        raise MassError("contrasts are not implemented for lm.gls")
    if kwargs:
        raise MassError("extra arguments to lm.fit are not implemented")
    formula = _expand_dot_formula(formula, data)
    x_mat, y_vec, names, _labels = _model_matrix(data, formula)
    n = x_mat.shape[0]
    w = np.asarray(W, dtype=float)
    if w.shape != (n, n):
        raise MassError("dim(W) is not correct")
    if method == "model.frame":
        return {"data": data, "formula": formula, "x": x_mat, "y": y_vec}
    a, ainv = _gls_transform(w, inverse=inverse)
    ax = a @ x_mat
    ay = a @ y_vec
    fit = _lm_fit(ax, ay)
    fitted = np.asarray(ainv @ fit["fitted.values"], dtype=float).reshape(-1)
    resid = np.asarray(ainv @ fit["residuals"], dtype=float).reshape(-1)
    coef = np.asarray(fit["coefficients"], dtype=float).reshape(-1)
    out = LmGlsFit(
        coefficients=coef,
        residuals=resid,
        fitted_values=fitted,
        rank=int(fit["rank"]),
        df_residual=int(fit["df.residual"]),
        terms=formula,
        call=("lm.gls", formula),
        effects=fit["residuals"],
        qr=fit["qr"],
    )
    if model:
        out.model = dict(data)
    if x:
        out.x = x_mat
    if y:
        out.y = y_vec
    if names and coef.shape[0] == len(names):
        out.coef_names = names  # type: ignore[attr-defined]
    return out
