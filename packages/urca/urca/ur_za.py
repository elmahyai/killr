"""Zivot and Andrews unit root test (``ur.za``)."""

from __future__ import annotations

import math
import warnings

import numpy as np
from scipy.linalg import qr

from urca.tests import _drop_missing, _match


class UrZa:
    def __init__(self, **fields):
        self.__dict__.update(fields)


def ur_za(y, model="intercept", lag=None):
    """Zivot-Andrews unit root test with an unknown break in intercept, trend, or both."""
    spec = _match(model, ("intercept", "trend", "both"))
    series = _drop_missing(y)
    n = len(series)
    if lag is None:
        lag = 0
    try:
        lag_len = len(lag)
    except TypeError:
        lag_len = 1
    lag = int(lag)
    if lag_len > 1 or lag < 0:
        warnings.warn(
            "\nPlease, specify maximal number of lags for differenced series as positive integer; lag=1 is now used.",
            stacklevel=2,
        )
        lag = 1
    ncol = lag + 3
    if n < ncol + 2:
        raise ValueError("\nInsufficient number of obeservations.")
    diffs = [series[i] - series[i - 1] for i in range(1, n)]
    y_l1 = [math.nan] + series[:-1]
    trend = list(range(1, n + 1))
    lag_cols = []
    if lag > 0:
        for i in range(1, lag + 1):
            padded = [math.nan] * (i + 1) + diffs
            lag_cols.append(padded[:n])

    if spec == "intercept":
        cval = [-5.34, -4.8, -4.58]

        def roll_stat(z):
            du = [0.0] * z + [1.0] * (n - z)
            return _y_l1_tstat(series, y_l1, trend, lag_cols, du)

        roll_stats = [roll_stat(z) for z in range(1, n)]
        bpoint = int(np.argmin(roll_stats)) + 1
        du = [0.0] * bpoint + [1.0] * (n - bpoint)
        test_fit = _za_lm(series, y_l1, trend, lag_cols, [du])
    elif spec == "trend":
        cval = [-4.93, -4.42, -4.11]

        def roll_stat(z):
            dt = [0.0] * z + list(range(1, n - z + 1))
            return _y_l1_tstat(series, y_l1, trend, lag_cols, dt)

        roll_stats = [roll_stat(z) for z in range(1, n)]
        bpoint = int(np.argmin(roll_stats)) + 1
        dt = [0.0] * bpoint + list(range(1, n - bpoint + 1))
        test_fit = _za_lm(series, y_l1, trend, lag_cols, [dt])
    else:
        cval = [-5.57, -5.08, -4.82]
        test_fit = _za_lm(series, y_l1, trend, lag_cols, [])

        def roll_stat(z):
            du = [0.0] * z + [1.0] * (n - z)
            dt = [0.0] * z + list(range(1, n - z + 1))
            return _y_l1_tstat(series, y_l1, trend, lag_cols, du, dt)

        roll_stats = [roll_stat(z) for z in range(1, n)]
        bpoint = int(np.argmin(roll_stats)) + 1
        du = [0.0] * bpoint + [1.0] * (n - bpoint)
        dt = [0.0] * bpoint + list(range(1, n - bpoint + 1))
        test_fit = _za_lm(series, y_l1, trend, lag_cols, [du, dt])

    teststat = roll_stats[bpoint - 1]
    return UrZa(
        y=series,
        model=spec,
        lag=lag,
        teststat=teststat,
        cval=cval,
        bpoint=bpoint,
        tstats=roll_stats,
        res=test_fit["residuals"],
        testreg=test_fit,
        test_name="Zivot-Andrews",
    )


def _y_l1_tstat(y, y_l1, trend, lag_cols, *extra_cols):
    fit = _za_lm(y, y_l1, trend, lag_cols, list(extra_cols))
    coef = fit["coef"][1]
    se = fit["se"][1]
    return (coef - 1.0) / se


def _za_lm(y, y_l1, trend, lag_cols, extra_cols):
    columns = [y_l1, trend] + list(lag_cols) + list(extra_cols)
    mask = np.ones(len(y), dtype=bool)
    for col in columns:
        for index, value in enumerate(col):
            if value is None or (isinstance(value, float) and math.isnan(value)):
                mask[index] = False
    response = np.asarray([y[i] for i in range(len(y)) if mask[i]], dtype=float)
    design_parts = [[col[i] for i in range(len(col)) if mask[i]] for col in columns]
    design = np.column_stack(design_parts) if design_parts else np.zeros((len(response), 0))
    if len(response) > 0:
        design = np.column_stack((np.ones(len(response)), design))
    return _r_lm(response, design)


def _r_lm(response, design):
    """Least squares with R ``lm`` rank handling (QR pivoting)."""
    n, p = design.shape
    if p == 0:
        residuals = response.copy()
        return {
            "coef": np.array([]),
            "se": np.array([]),
            "t": np.array([]),
            "residuals": residuals,
            "rss": float(np.dot(residuals, residuals)),
            "df": n,
        }
    q, r, pivot = qr(design, mode="economic", pivoting=True)
    tol = np.finfo(float).eps * max(n, p) * np.max(np.abs(np.diag(r)))
    rank = int(np.sum(np.abs(np.diag(r)) > tol))
    piv = pivot[:rank]
    r1 = r[:rank, :rank]
    qt_y = q.T @ response
    coef_p = np.linalg.solve(r1, qt_y[:rank])
    coef = np.zeros(p)
    coef[piv] = coef_p
    residuals = response - design @ coef
    df = n - rank
    sigma2 = float(np.dot(residuals, residuals)) / df
    rinv = np.linalg.inv(r1)
    cov = np.zeros((p, p))
    cov[np.ix_(piv, piv)] = sigma2 * (rinv @ rinv.T)
    se = np.sqrt(np.diag(cov))
    with np.errstate(divide="ignore", invalid="ignore"):
        tstats = coef / se
    return {
        "coef": coef,
        "se": se,
        "t": tstats,
        "residuals": residuals,
        "rss": float(np.dot(residuals, residuals)),
        "df": df,
    }
