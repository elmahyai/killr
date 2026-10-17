"""Rubin multiple-imputation inference."""

from __future__ import annotations

from dataclasses import dataclass
from math import inf
import numpy as np


@dataclass
class MIResult:
    coefficients: np.ndarray
    variance: np.ndarray
    call: object = None
    nimp: int = 0
    df: np.ndarray | float = inf
    missinfo: np.ndarray | float = 0.0


def MIcombine(
    results,
    variances=None,
    call=None,
    df_complete=inf,
    **kwargs,
) -> MIResult:
    """Combine estimates and within-imputation variances."""
    if isinstance(results, MIResult):
        return results
    if variances is None and results and hasattr(results[0], "coefficients"):
        variances = [x.variance for x in results]
        results = [x.coefficients for x in results]
    values = [np.asarray(x, dtype=float) for x in results]
    if not values:
        raise ValueError("results must contain at least one imputation")
    if variances is None:
        raise ValueError("variances is required for numeric results")
    within = [np.asarray(x, dtype=float) for x in variances]
    m = len(values)
    cbar = np.mean(values, axis=0)
    vbar = np.mean(within, axis=0)
    if m > 1:
        evar = np.cov(np.stack(values), rowvar=False, ddof=1)
        if np.ndim(evar) == 0:
            evar = np.asarray([[evar]])
    else:
        evar = np.zeros((cbar.size, cbar.size))
    total = vbar + evar * (m + 1) / m
    with np.errstate(divide="ignore", invalid="ignore"):
        relative = (1 + 1 / m) * evar / vbar
        df = (m - 1) * (1 + 1 / relative) ** 2
    if np.ndim(df) == 2:
        df = np.diag(df)
    if np.isfinite(df_complete):
        dfobs = ((df_complete + 1) / (df_complete + 3)) * df_complete * vbar / (vbar + evar)
        if np.ndim(dfobs) == 2:
            dfobs = np.diag(dfobs)
        df = 1 / (1 / dfobs + 1 / df)
    if np.ndim(relative) == 2:
        relative = np.diag(relative)
    missinfo = (relative + 2 / (df + 3)) / (relative + 1)
    return MIResult(cbar, total, call=call, nimp=m, df=df, missinfo=missinfo)
