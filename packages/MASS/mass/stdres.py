"""Standardized residuals from a linear model (MASS stdres)."""

from __future__ import annotations

import warnings
from typing import Any

import numpy as np

from mass.errors import MassError


def _hat_influence(object: Any) -> np.ndarray:
    """Diagonal hat values like ``lm.influence(..., do.coef = FALSE)$hat``."""
    x = getattr(object, "x", None)
    if x is None:
        raise MassError("model matrix 'x' is required for stdres")
    x = np.asarray(x, dtype=float)
    if x.ndim == 1:
        x = x.reshape(-1, 1)
    weights = getattr(object, "weights", None)
    rank = getattr(object, "rank", None)
    if weights is not None:
        sw = np.sqrt(np.asarray(weights, dtype=float).reshape(-1))
        x = x * sw[:, None]
    q, r = np.linalg.qr(x, mode="reduced")
    if rank is None:
        rank = int(np.sum(np.abs(np.diag(r)) > np.max(x.shape) * np.finfo(float).eps))
    q = q[:, :rank]
    return np.sum(q * q, axis=1)


def _naresid(na_action: Any, values: np.ndarray) -> np.ndarray:
    if na_action is None:
        return values
    if isinstance(na_action, dict):
        omitted = na_action.get("omit")
        if omitted is None:
            return values
        n = int(na_action.get("n", len(values) + len(omitted)))
        out = np.full(n, np.nan, dtype=float)
        keep = np.ones(n, dtype=bool)
        for idx in omitted:
            keep[int(idx)] = False
        out[keep] = np.asarray(values, dtype=float).reshape(-1)
        return out
    return values


def _lmwork_stdres(object: Any) -> np.ndarray:
    resid = np.asarray(object.residuals, dtype=float).reshape(-1)
    hat = _hat_influence(object)
    hat = hat[hat > 0]
    ok = ~np.isnan(resid)
    n_miss = int(np.sum(~ok))
    if n_miss:
        warnings.warn(
            f"{n_miss} missing observation{'s' if n_miss != 1 else ''} deleted",
            stacklevel=3,
        )
    resid = resid[ok]
    n = int(resid.shape[0])
    p = int(object.rank)
    rdf = getattr(object, "df_residual", None)
    if rdf is None:
        rdf_attr = getattr(object, "df_resid", None)
        rdf = n - p if rdf_attr is None else rdf_attr
    weights = getattr(object, "weights", None)
    if weights is not None:
        wt = np.asarray(weights, dtype=float).reshape(-1)[ok]
        resid = resid * np.sqrt(wt)
        excl = wt == 0
        if np.any(excl):
            n_excl = int(np.sum(excl))
            warnings.warn(
                f"{n_excl} row{'s' if n_excl != 1 else ''} with zero weights not counted",
                stacklevel=3,
            )
            resid = resid[~excl]
            if getattr(object, "df_resid", None) is None:
                rdf = rdf - n_excl
    stdres_out = resid.copy()
    if n > p:
        stddev = float(np.sqrt(np.sum(resid**2) / rdf))
        sr = resid / (np.sqrt(1.0 - hat) * stddev)
        stdres_out = sr
        na_action = getattr(object, "na_action", None)
        if na_action is not None:
            stdres_out = _naresid(na_action, stdres_out)
    else:
        stdres_out = np.full_like(resid, np.nan, dtype=float)
    return stdres_out


def stdres(object: Any) -> np.ndarray:
    """Extract standardized residuals from a linear model."""
    return _lmwork_stdres(object)
