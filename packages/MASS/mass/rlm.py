"""Robust linear models (MASS rlm)."""

from __future__ import annotations

import math
import warnings
from dataclasses import dataclass
from typing import Any, Callable

import numpy as np

from mass.errors import MassError


def _match_arg(value: str | None, choices: list[str]) -> str:
    if value is None:
        return choices[0]
    text = str(value)
    exact = [item for item in choices if item == text]
    if len(exact) == 1:
        return exact[0]
    hits = [item for item in choices if item.startswith(text)]
    if len(hits) == 1:
        return hits[0]
    if not hits:
        raise MassError("'arg' should be one of " + ", ".join(repr(item) for item in choices))
    raise MassError("'arg' matched more than one choice: " + ", ".join(hits))


def _pnorm(k: float) -> float:
    return 0.5 * (1.0 + math.erf(k / math.sqrt(2.0)))


def _dnorm(k: float) -> float:
    return math.exp(-0.5 * k * k) / math.sqrt(2.0 * math.pi)


def psi_huber(u, k: float = 1.345, deriv: int = 0):
    u_arr = np.asarray(u, dtype=float)
    if deriv:
        return (np.abs(u_arr) <= k).astype(float)
    with np.errstate(divide="ignore", invalid="ignore"):
        out = np.minimum(1.0, k / np.abs(u_arr))
    out = np.where(np.isfinite(out), out, 1.0)
    return out


def psi_bisquare(u, c: float = 4.685, deriv: int = 0):
    u_arr = np.asarray(u, dtype=float)
    if deriv:
        t = (u_arr / c) ** 2
        return np.where(t < 1, (1 - t) * (1 - 5 * t), 0.0)
    abs_u = np.abs(u_arr)
    ratio = np.minimum(1.0, abs_u / c)
    return (1.0 - ratio**2) ** 2


def _mad_center_zero(x: np.ndarray) -> float:
    """R ``mad(x, 0)``: center fixed at zero, default constant 1.4826."""
    values = np.abs(np.asarray(x, dtype=float).reshape(-1))
    return float(1.4826 * np.median(values))


def _wmad(x: np.ndarray, w: np.ndarray) -> float:
    order = np.argsort(np.abs(x), kind="mergesort")
    abs_x = np.abs(x)[order]
    weights = np.asarray(w, dtype=float).reshape(-1)[order]
    p = np.cumsum(weights) / np.sum(weights)
    n = int(np.sum(p < 0.5))
    if p[n] > 0.5:
        return float(abs_x[n] / 0.6745)
    return float((abs_x[n] + abs_x[n + 1]) / (2.0 * 0.6745))


def _lm_wfit(x: np.ndarray, y: np.ndarray, w: np.ndarray) -> dict[str, Any]:
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float).reshape(-1)
    w = np.asarray(w, dtype=float).reshape(-1)
    if w.shape[0] != x.shape[0]:
        raise MassError("length of 'weights' must equal number of observations")
    if np.any(w < 0):
        raise MassError("negative 'weights' value")
    scale = np.sqrt(w)
    q, r = np.linalg.qr(x * scale[:, None], mode="reduced")
    coef = np.linalg.solve(r, q.T @ (y * scale))
    resid = y - x @ coef
    rank = int(np.sum(np.abs(np.diag(r)) > np.max(x.shape) * np.finfo(float).eps))
    return {"coefficients": coef, "residuals": resid, "rank": rank}


def _irls_delta(old: np.ndarray, new: np.ndarray) -> float:
    old = np.asarray(old, dtype=float).reshape(-1)
    new = np.asarray(new, dtype=float).reshape(-1)
    denom = max(1.0e-20, float(np.sum(old**2)))
    return float(math.sqrt(float(np.sum((old - new) ** 2)) / denom))


def _split_formula(text: str) -> tuple[str, str]:
    if "~" not in text:
        raise MassError("formula needs a '~'")
    left, right = text.split("~", 1)
    return left.strip(), right.strip()


def _parse_rhs_terms(rhs: str) -> tuple[bool, list[str]]:
    intercept = True
    terms: list[str] = []
    for raw in rhs.split("+"):
        piece = raw.strip()
        if not piece:
            continue
        if piece in {"1", ""}:
            continue
        if piece in {"0", "-1"}:
            intercept = False
            continue
        if piece.startswith("-"):
            name = piece[1:].strip()
            if name == "1":
                intercept = False
            continue
        terms.append(piece)
    return intercept, terms


def _model_matrix(data: dict, formula: str) -> tuple[np.ndarray, np.ndarray, list[str]]:
    resp, rhs = _split_formula(formula)
    intercept, terms = _parse_rhs_terms(rhs)
    y = np.asarray(data[resp], dtype=float).reshape(-1)
    n = y.shape[0]
    columns: list[np.ndarray] = []
    names: list[str] = []
    if intercept:
        columns.append(np.ones(n))
        names.append("(Intercept)")
    for term in terms:
        if term == ".":
            for key in data:
                if key == resp:
                    continue
                col = np.asarray(data[key], dtype=float).reshape(-1)
                if col.shape[0] != n:
                    raise MassError(f"column '{key}' has length {col.shape[0]}, not {n}")
                columns.append(col)
                names.append(key)
            continue
        if term not in data:
            raise MassError(f"object '{term}' not found")
        col = np.asarray(data[term], dtype=float).reshape(-1)
        if col.shape[0] != n:
            raise MassError(f"column '{term}' has length {col.shape[0]}, not {n}")
        columns.append(col)
        names.append(term)
    x = np.column_stack(columns) if columns else np.empty((n, 0))
    return x, y, names


@dataclass
class RlmFit:
    coefficients: np.ndarray
    residuals: np.ndarray
    fitted_values: np.ndarray
    wresid: np.ndarray
    w: np.ndarray
    s: float
    converged: bool
    conv: list[float]
    rank: int
    x: np.ndarray | None = None
    y: np.ndarray | None = None
    weights: np.ndarray | None = None
    call: Any = None
    terms: Any = None
    psi: Callable[..., Any] = psi_huber
    k2: float = 1.345


def _rlm_default(
    x,
    y,
    weights=None,
    *,
    w: np.ndarray | None = None,
    init: str | list | np.ndarray = "ls",
    psi=psi_huber,
    scale_est: str | None = None,
    k2: float = 1.345,
    method: str | None = None,
    wt_method: str | None = None,
    maxit: int = 20,
    acc: float = 1e-4,
    test_vec: str | None = "resid",
    lqs_control: dict | None = None,
    **psi_kwargs,
) -> RlmFit:
    method = _match_arg(method, ["M", "MM"])
    wt_method = _match_arg(wt_method, ["inv.var", "case"])
    x = np.asarray(x, dtype=float)
    if x.ndim == 1:
        x = x.reshape(-1, 1)
    y = np.asarray(y, dtype=float).reshape(-1)
    xx = x.copy()
    yy = y.copy()
    nrow, ncol = x.shape
    if w is None:
        w = np.ones(nrow, dtype=float)
    else:
        w = np.asarray(w, dtype=float).reshape(-1)
    rank_x = int(np.linalg.matrix_rank(x))
    if rank_x < ncol:
        raise MassError("'x' is singular: singular fits are not implemented in 'rlm'")
    if test_vec is not None and test_vec not in {"resid", "coef", "w", "NULL"}:
        raise MassError("invalid 'test.vec'")
    wt: np.ndarray | None = None
    if weights is not None:
        weights = np.asarray(weights, dtype=float).reshape(-1)
        if weights.shape[0] != nrow:
            raise MassError("length of 'weights' must equal number of observations")
        if np.any(weights < 0):
            raise MassError("negative 'weights' value")
        if wt_method == "inv.var":
            fac = np.sqrt(weights)
            y = y * fac
            x = x * fac[:, None]
            wt = None
        else:
            w = w * weights
            wt = weights
    if method == "M":
        scale_est = _match_arg(scale_est, ["MAD", "Huber", "proposal 2"])
        if not callable(psi):
            raise MassError("psi must be a callable")
        if isinstance(init, str):
            if init == "ls":
                temp = _lm_wfit(x, y, w)
                coef = temp["coefficients"]
                resid = temp["residuals"]
            elif init == "lts":
                raise MassError("init 'lts' requires lqs, which is not translated")
            else:
                raise MassError("'init' method is unknown")
        elif isinstance(init, dict):
            coef = np.asarray(init["coef"], dtype=float).reshape(-1)
            resid = y - x @ coef
        else:
            coef = np.asarray(init, dtype=float).reshape(-1)
            resid = y - x @ coef
    elif method == "MM":
        raise MassError("method 'MM' requires lqs, which is not translated")
    else:
        raise MassError("'method' is unknown")

    n1 = (nrow if wt is None else float(np.sum(wt))) - ncol
    theta = 2 * _pnorm(k2) - 1
    gamma = theta + k2**2 * (1 - theta) - 2 * k2 * _dnorm(k2)
    if scale_est != "MM":
        scale = _mad_center_zero(resid) if wt is None else _wmad(resid, wt)
    conv: list[float] = []
    done = False
    temp: dict[str, Any] = {}
    w_iter = np.asarray(w, dtype=float).copy()
    for _ in range(maxit):
        testpv = None
        if test_vec is not None:
            if test_vec == "resid":
                testpv = resid.copy()
            elif test_vec == "coef":
                testpv = coef.copy()
            elif test_vec == "w":
                testpv = w.copy()
        if scale_est != "MM":
            if scale_est == "MAD":
                scale = (
                    float(np.median(np.abs(resid)) / 0.6745)
                    if wt is None
                    else _wmad(resid, wt)
                )
            elif wt is None:
                numer = float(np.sum(np.minimum(resid**2, (k2 * scale) ** 2)))
                scale = float(math.sqrt(numer / (n1 * gamma)))
            else:
                numer = float(np.sum(wt * np.minimum(resid**2, (k2 * scale) ** 2)))
                scale = float(math.sqrt(numer / (n1 * gamma)))
            if scale == 0:
                done = True
                break
        iw = psi(resid / scale, **psi_kwargs)
        w_iter = np.asarray(iw, dtype=float).reshape(-1)
        if wt is not None:
            w_iter = w_iter * weights
        temp = _lm_wfit(x, y, w_iter)
        coef = temp["coefficients"]
        resid = temp["residuals"]
        if test_vec is not None:
            if test_vec == "resid":
                convi = _irls_delta(testpv, resid)
            elif test_vec == "coef":
                convi = _irls_delta(testpv, coef)
            else:
                convi = _irls_delta(testpv, w_iter)
        else:
            convi = 0.0
        conv.append(convi)
        done = convi <= acc
        if done:
            break
    if not done:
        warnings.warn(f"'rlm' failed to converge in {maxit} steps", stacklevel=2)
    fitted = xx @ coef
    return RlmFit(
        coefficients=coef,
        residuals=yy - fitted,
        fitted_values=fitted,
        wresid=resid,
        w=w_iter,
        s=float(scale),
        converged=done,
        conv=conv,
        rank=temp.get("rank", rank_x),
        x=xx,
        y=yy,
        weights=weights,
        psi=psi,
        k2=k2,
    )


def rlm(
    x,
    y=None,
    weights=None,
    *,
    data: dict | None = None,
    method: str | None = None,
    wt_method: str | None = None,
    model: bool = True,
    x_ret: bool = True,
    y_ret: bool = False,
    **kwargs,
) -> RlmFit | dict:
    """Fit a linear model by robust regression."""
    if y is None and isinstance(x, str):
        formula = x
        if data is None:
            raise MassError("'data' must be supplied for a formula")
        method = _match_arg(method, ["M", "MM", "model.frame"])
        if method == "model.frame":
            x_mat, y_vec, _names = _model_matrix(data, formula)
            return {"x": x_mat, "y": y_vec, "data": data, "formula": formula}
        x_mat, y_vec, names = _model_matrix(data, formula)
        fit = _rlm_default(x_mat, y_vec, weights, method=method, wt_method=wt_method, **kwargs)
        fit.terms = formula
        fit.call = ("rlm", formula)
        if not x_ret:
            fit.x = None
        if y_ret:
            fit.y = y_vec
        if not model:
            pass
        coef_names = names
        fit.coefficients = np.asarray(fit.coefficients, dtype=float)
        if coef_names and fit.coefficients.shape[0] == len(coef_names):
            fit.coef_names = coef_names
        return fit
    if y is None:
        raise MassError("'y' is missing")
    return _rlm_default(x, y, weights, method=method, wt_method=wt_method, **kwargs)
