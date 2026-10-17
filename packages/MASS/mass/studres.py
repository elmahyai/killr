"""Studentized residuals from a linear model (MASS studres)."""

from __future__ import annotations

import warnings
from typing import Any

import numpy as np

from mass.stdres import _hat_influence, _naresid


def _lmwork_studres(object: Any) -> np.ndarray:
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
    studres_out = resid.copy()
    if n > p:
        stddev = float(np.sqrt(np.sum(resid**2) / rdf))
        sr = resid / (np.sqrt(1.0 - hat) * stddev)
        studres_out = sr / np.sqrt((n - p - sr**2) / (n - p - 1))
        na_action = getattr(object, "na_action", None)
        if na_action is not None:
            studres_out = _naresid(na_action, studres_out)
    else:
        studres_out = np.full_like(resid, np.nan, dtype=float)
    return studres_out


def studres(object: Any) -> np.ndarray:
    """Extract studentized residuals from a linear model."""
    return _lmwork_studres(object)
