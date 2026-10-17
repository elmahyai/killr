"""Elliott, Rothenberg and Stock unit root test (``ur.ers``)."""

from __future__ import annotations

import math

import numpy as np

from urca.tests import _aic, _diff, _drop_missing, _embed, _match, _ols

_PCT = ("1pct", "5pct", "10pct")

# R array(..., dim = c(4, 3, 2)); last index is constant vs trend.
_CVALS_PTEST = (
    (
        (1.87, 2.97, 3.91),
        (1.95, 3.11, 4.17),
        (1.91, 3.17, 4.33),
        (1.99, 3.26, 4.48),
    ),
    (
        (4.22, 5.72, 6.77),
        (4.26, 5.64, 6.79),
        (4.05, 5.66, 6.86),
        (3.96, 5.62, 6.89),
    ),
)

# R matrix(..., nrow = 4, ncol = 3) fills column-first before negation in source.
_CVALS_DFGLS_TAU = (
    (3.77, 3.19, 2.89),
    (3.58, 3.03, 2.74),
    (3.46, 2.93, 2.64),
    (3.48, 2.89, 2.57),
)


class UrErs:
    def __init__(self, **fields):
        self.__dict__.update(fields)


def ur_ers(y, type="DF-GLS", model="constant", lag_max=4):
    """ERS unit root test. type is DF-GLS or P-test; model is constant or trend."""
    test_type = _match(type, ("DF-GLS", "P-test"))
    spec = _match(model, ("constant", "trend"))
    lag_max = int(lag_max)
    if lag_max < 0:
        lag_max = 4
    lag_max = lag_max + 1
    idx = list(range(2, lag_max + 1))
    series = _drop_missing(y)
    nobs = len(series)
    if nobs < 50:
        rowsel = 0
    elif nobs < 100:
        rowsel = 1
    elif nobs <= 200:
        rowsel = 2
    else:
        rowsel = 3

    if spec == "constant":
        ahat = 1.0 - 7.0 / nobs
        ya = [series[0]] + [
            series[i] - ahat * series[i - 1] for i in range(1, nobs)
        ]
        za1 = [1.0] + [1.0 - ahat] * (nobs - 1)
        yd_reg = _ols(ya, np.asarray(za1, dtype=float))
        yd = [value - yd_reg["coef"][0] for value in series]
    else:
        ahat = 1.0 - 13.5 / nobs
        ya = [series[0]] + [
            series[i] - ahat * series[i - 1] for i in range(1, nobs)
        ]
        za1 = [1.0] + [1.0 - ahat] * (nobs - 1)
        trd = list(range(1, nobs + 1))
        za2 = [1.0] + [
            trd[i] - ahat * trd[i - 1] for i in range(1, nobs)
        ]
        yd_reg = _ols(ya, np.column_stack((za1, za2)))
        yd = [
            series[i] - yd_reg["coef"][0] - yd_reg["coef"][1] * trd[i]
            for i in range(nobs)
        ]

    test_reg = None
    if test_type == "P-test":
        if spec == "constant":
            null_res = [0.0] + _diff(series)
            cvals = [list(_CVALS_PTEST[0][rowsel])]
            model_label = "with intercept"
        else:
            null_res = [0.0] + _diff(series)
            mean_null = float(np.mean(null_res))
            null_res = [value - mean_null for value in null_res]
            cvals = [list(_CVALS_PTEST[1][rowsel])]
            model_label = "with intercept and trend"
        sig_null = float(np.dot(null_res, null_res))
        sig_res = float(np.dot(yd_reg["residuals"], yd_reg["residuals"]))
        if lag_max > 1:
            bic_scores = [_what_bic(x, series, nobs) for x in idx]
            bic_opt = int(np.argmin(bic_scores)) + 2
            what_reg = _what_reg(bic_opt, series, nobs)
            npar = len(what_reg["coef"])
            sumlc = float(np.sum(what_reg["coef"][2:npar]))
            lag_out = bic_opt - 1
        else:
            y_diff = _diff(series)
            y_l = series[: nobs - 1]
            what_reg = _ols(y_diff, _with_intercept(np.asarray(y_l, dtype=float).reshape(-1, 1)))
            sumlc = 0.0
            lag_out = lag_max - 1
        df = what_reg["df"]
        sigma = math.sqrt(what_reg["rss"] / df) if df > 0 else math.nan
        what_sq = sigma**2 / (1.0 - sumlc) ** 2
        teststat = (sig_res - ahat * sig_null) / what_sq
    else:
        if spec == "constant":
            cvals = [
                [
                    -2.5658 - 1.960 / nobs - 10.04 / nobs**2,
                    -1.9393 - 0.398 / nobs,
                    -1.6156 - 0.181 / nobs,
                ]
            ]
            model_label = "with intercept"
        else:
            cvals = [[-value for value in _CVALS_DFGLS_TAU[rowsel]]]
            model_label = "with intercept and trend"
        yd_l = yd[: nobs - 1]
        yd_diff = _diff(yd)
        if lag_max > 1:
            embedded = _embed(yd_diff, lag_max)
            yd_dlags = [row[1:] for row in embedded]
            skip = lag_max - 1
            response = yd_diff[skip:]
            lag_level = yd_l[skip:]
            design_cols = [lag_level] + _transpose(yd_dlags)
            design = np.column_stack(design_cols)
            dfgls_reg = _ols(response, design)
            lag_out = lag_max - 1
        else:
            dfgls_reg = _ols(yd_diff, np.asarray(yd_l, dtype=float).reshape(-1, 1))
            lag_out = lag_max - 1
        teststat = float(dfgls_reg["t"][0])
        test_reg = dfgls_reg

    cval_rounded = [[round(value, 2) for value in row] for row in cvals]
    return UrErs(
        y=series,
        yd=yd,
        type=test_type,
        model=model_label,
        lag=int(lag_out),
        cval=cval_rounded,
        teststat=teststat,
        testreg=test_reg,
        test_name="Elliot, Rothenberg and Stock",
        _pct=_PCT,
    )


def _with_intercept(design):
    if design.size == 0:
        return np.ones((design.shape[0], 1))
    return np.column_stack((np.ones(design.shape[0]), design))


def _transpose(rows):
    if not rows:
        return []
    width = len(rows[0])
    return [[row[col] for row in rows] for col in range(width)]


def _what_bic(x, series, nobs):
    z_l = series[: nobs - 1]
    z_diff = _diff(series)
    embedded = _embed(z_diff, x)
    z_dlags = [row[1:] for row in embedded]
    skip = x - 1
    response = z_diff[skip:]
    lag_level = z_l[skip:]
    design = _with_intercept(
        np.column_stack([lag_level] + _transpose(z_dlags))
    )
    fit = _ols(response, design)
    return _aic(fit, math.log(len(response)))


def _what_reg(bic_opt, series, nobs):
    y_l = series[: nobs - 1]
    y_diff = _diff(series)
    embedded = _embed(y_diff, bic_opt)
    y_dlags = [row[1:] for row in embedded]
    skip = bic_opt - 1
    response = y_diff[skip:]
    lag_level = y_l[skip:]
    design = _with_intercept(
        np.column_stack([lag_level] + _transpose(y_dlags))
    )
    return _ols(response, design)
