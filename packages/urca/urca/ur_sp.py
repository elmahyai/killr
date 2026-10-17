"""Schmidt-Phillips unit root test (``ur.sp``)."""

from __future__ import annotations

import math
import warnings

import numpy as np

from urca.tests import _drop_missing, _match, _ols

_OBS_RANGES = (25, 50, 100, 200, 500, 1000, 1e30)
_SIGNIF = (0.01, 0.05, 0.1)

_CVS_TAU = tuple(
    -value
    for value in (
        3.9,
        3.73,
        3.63,
        3.61,
        3.59,
        3.58,
        3.56,
        3.18,
        3.11,
        3.06,
        3.04,
        3.04,
        3.02,
        3.02,
        2.85,
        2.8,
        2.77,
        2.76,
        2.76,
        2.75,
        2.75,
        4.52,
        4.28,
        4.16,
        4.12,
        4.08,
        4.06,
        4.06,
        3.78,
        3.77,
        3.65,
        3.6,
        3.55,
        3.55,
        3.53,
        3.52,
        3.41,
        3.34,
        3.31,
        3.28,
        3.26,
        3.26,
        3.26,
        5.07,
        4.73,
        4.59,
        4.53,
        4.5,
        4.49,
        4.44,
        4.26,
        4.08,
        4.03,
        3.99,
        3.96,
        3.95,
        3.93,
        3.89,
        3.77,
        3.72,
        3.69,
        3.68,
        3.68,
        3.67,
        5.57,
        5.13,
        4.99,
        4.9,
        4.85,
        4.83,
        4.81,
        4.7,
        4.47,
        4.39,
        4.33,
        4.31,
        4.31,
        4.29,
        4.3,
        4.15,
        4.1,
        4.06,
        4.03,
        4.03,
        4.01,
    )
)

_CVS_RHO = tuple(
    -value
    for value in (
        20.4,
        22.8,
        23.8,
        24.8,
        25.3,
        25.3,
        25.2,
        15.7,
        17.0,
        17.5,
        17.9,
        18.1,
        18.1,
        18.1,
        13.4,
        14.3,
        14.6,
        14.9,
        15.0,
        15.0,
        15.0,
        24.6,
        28.4,
        30.4,
        31.8,
        32.4,
        32.5,
        32.6,
        20.1,
        22.4,
        23.7,
        24.2,
        24.8,
        24.6,
        24.7,
        17.8,
        19.5,
        20.4,
        20.7,
        21.0,
        21.1,
        21.1,
        28.1,
        33.1,
        36.3,
        38.0,
        39.1,
        39.5,
        39.7,
        23.8,
        27.0,
        29.1,
        30.1,
        30.6,
        30.8,
        30.6,
        21.5,
        24.0,
        25.4,
        26.1,
        26.6,
        26.7,
        26.7,
        31.0,
        37.4,
        41.8,
        44.0,
        45.3,
        45.7,
        45.8,
        26.9,
        31.2,
        34.0,
        35.2,
        36.2,
        36.6,
        36.4,
        24.7,
        28.1,
        30.2,
        31.2,
        31.8,
        32.0,
        31.9,
    )
)


class UrSp:
    def __init__(self, **fields):
        self.__dict__.update(fields)


def ur_sp(y, type="tau", pol_deg=1, signif=0.01):
    """Schmidt-Phillips unit root test. type is tau or rho; pol_deg is 1 through 4."""
    test_type = _match(type, ("tau", "rho"))
    signif = float(signif)
    if signif not in _SIGNIF:
        warnings.warn(
            "\nPlease, provide as signif one of c(0.01, 0.05, 0.1); signif=0.01 used",
            stacklevel=2,
        )
        signif = 0.01
    pol_deg = int(pol_deg)
    if pol_deg not in (1, 2, 3, 4):
        warnings.warn(
            "\nPlease, provide as polynomial degree one of c(1, 2, 3, 4); po.deg=1 used",
            stacklevel=2,
        )
        pol_deg = 1

    series = _drop_missing(y)
    n = len(series)
    lag = math.trunc(12 * (n / 100) ** 0.25)
    idx = list(range(1, lag + 1))
    trend1 = np.arange(1, n + 1, dtype=float)
    y_diff = np.diff(series)
    trend2 = trend1**2

    if pol_deg == 1:
        yi_hat = (series[-1] - series[0]) / (n - 1)
        phi_y = series[0] - yi_hat
        s_hat = np.asarray(series, dtype=float) - phi_y - yi_hat * trend1
        s_hat_l1 = s_hat[:-1]
        test_reg = _ols(y_diff, np.column_stack((np.ones(n - 1), s_hat_l1)))
        corr_reg = _ols(
            series[1:],
            np.column_stack((np.ones(n - 1), series[:-1], trend1[1:])),
        )
    elif pol_deg == 2:
        detrend = _ols(y_diff, np.column_stack((np.ones(n - 1), trend1[1:])))
        s_hat = np.concatenate(([0.0], np.cumsum(detrend["residuals"])))
        test_reg = _ols(
            y_diff,
            np.column_stack((np.ones(n - 1), s_hat[:-1], trend1[1:])),
        )
        corr_reg = _ols(
            series[1:],
            np.column_stack(
                (np.ones(n - 1), series[:-1], trend1[1:], trend2[1:])
            ),
        )
    elif pol_deg == 3:
        trend3 = trend1**3
        detrend = _ols(
            y_diff, np.column_stack((np.ones(n - 1), trend1[1:], trend2[1:]))
        )
        s_hat = np.concatenate(([0.0], np.cumsum(detrend["residuals"])))
        test_reg = _ols(
            y_diff,
            np.column_stack(
                (np.ones(n - 1), s_hat[:-1], trend1[1:], trend2[1:])
            ),
        )
        corr_reg = _ols(
            series[1:],
            np.column_stack(
                (
                    np.ones(n - 1),
                    series[:-1],
                    trend1[1:],
                    trend2[1:],
                    trend3[1:],
                )
            ),
        )
    else:
        trend3 = trend1**3
        trend4 = trend1**4
        detrend = _ols(
            y_diff,
            np.column_stack(
                (np.ones(n - 1), trend1[1:], trend2[1:], trend3[1:])
            ),
        )
        s_hat = np.concatenate(([0.0], np.cumsum(detrend["residuals"])))
        test_reg = _ols(
            y_diff,
            np.column_stack(
                (
                    np.ones(n - 1),
                    s_hat[:-1],
                    trend1[1:],
                    trend2[1:],
                    trend3[1:],
                )
            ),
        )
        corr_reg = _ols(
            series[1:],
            np.column_stack(
                (
                    np.ones(n - 1),
                    series[:-1],
                    trend1[1:],
                    trend2[1:],
                    trend3[1:],
                    trend4[1:],
                )
            ),
        )
    res = corr_reg["residuals"]
    sig_eps = float(np.dot(res, res)) / n
    coprods = [_sp_coproduct(res, n, x) for x in idx]
    weights = [(2 * (lag - x) / lag) ** 2 for x in idx]
    sig = sig_eps + (2 / n) * float(np.dot(weights, coprods))
    omega2_hat = sig_eps / sig

    if test_type == "rho":
        rho = n * test_reg["coef"][1]
        teststat = rho / omega2_hat
    else:
        tau = test_reg["t"][1]
        teststat = tau / math.sqrt(omega2_hat)

    cval = _spcv(n, test_type, pol_deg, signif)
    return UrSp(
        y=series,
        type=test_type,
        polynomial=pol_deg,
        teststat=float(teststat),
        cval=float(cval),
        signif=signif,
        res=res,
        testreg=corr_reg,
        test_name="Schmidt-Phillips",
    )


def _sp_coproduct(residuals, n, lag):
    values = np.asarray(residuals, dtype=float)
    left = values[lag:]
    right = values[: n - lag - 1]
    return float(np.dot(left, right))


def _spcv(obs, test_type, pol_deg, signif):
    dim1 = next(i for i, bound in enumerate(_OBS_RANGES) if obs <= bound)
    dim2 = _SIGNIF.index(signif)
    table = _CVS_TAU if test_type == "tau" else _CVS_RHO
    return table[dim1 + 7 * dim2 + 21 * (pol_deg - 1)]
