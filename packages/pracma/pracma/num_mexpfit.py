"""Separable multi-exponential and basis fits."""

from __future__ import annotations

import numpy as np

from pracma._util import PracmaError
from pracma.num_helpers import is_r_numeric, lsqnonlin, qr_solve


def mexpfit(x, y, p0, w=None, const=True, options=None):
    if not is_r_numeric(x) or not is_r_numeric(y) or not is_r_numeric(p0):
        raise PracmaError("is.numeric(x) is not TRUE")
    abscissa = np.asarray(x, dtype=float).reshape(-1)
    ordinate = np.asarray(y, dtype=float).reshape(-1)
    if ordinate.size != abscissa.size:
        raise PracmaError("Arguments 'x', 'y' must be of the same length.")
    start = np.asarray(p0, dtype=float).reshape(-1)
    _, first = np.unique(start, return_index=True)
    start = start[np.sort(first)]
    if abscissa.size <= 2 * start.size + 1:
        raise PracmaError("Not enough data points available for fitting exponential sums.")
    opts = {"tau": 1e-4, "tolx": 1e-7, "tolg": 1e-9, "maxeval": 1000}
    if options:
        for key, value in options.items():
            if key not in opts:
                raise PracmaError("'arg' should be one of \u201ctau\u201d, \u201ctolx\u201d, \u201ctolg\u201d, \u201cmaxeval\u201d")
            opts[key] = value
    if np.any(start == 0):
        raise PracmaError("All entries in 'p0' must be different and not equal to zero.")

    def residual(b):
        design = np.exp(abscissa[:, None] * np.asarray(b, dtype=float).reshape(1, -1))
        if const:
            design = np.column_stack([np.ones(abscissa.size), design])
        coeff = qr_solve(design, ordinate)
        return design @ coeff - ordinate

    fit = lsqnonlin(residual, start, options=opts)
    rates = fit["x"]
    design = np.exp(abscissa[:, None] * rates.reshape(1, -1))
    if const:
        design = np.column_stack([np.ones(abscissa.size), design])
    coeff = qr_solve(design, ordinate)
    if const:
        a0 = float(coeff[0])
        amplitudes = coeff[1:]
    else:
        a0 = 0.0
        amplitudes = coeff
    return {
        "a0": a0,
        "a": np.asarray(amplitudes, dtype=float).reshape(-1),
        "b": rates,
        "ssq": fit["ssq"],
        "iter": fit["neval"],
        "errmess": fit["errmess"],
    }


def lsqsep(flist, p0, xdata, ydata, const=True):
    if not is_r_numeric(xdata) or not is_r_numeric(ydata) or not is_r_numeric(p0):
        raise PracmaError("is.numeric(xdata) is not TRUE")
    abscissa = np.asarray(xdata, dtype=float).reshape(-1)
    ordinate = np.asarray(ydata, dtype=float).reshape(-1)
    if ordinate.size != abscissa.size:
        raise PracmaError("Numeric arguments 'xdata', 'ydata' must have the same length.")
    start = np.asarray(p0, dtype=float).reshape(-1)
    bases = list(flist)

    def columns(b):
        design = np.ones((abscissa.size, len(bases) + 1))
        for index, func in enumerate(bases):
            design[:, index + 1] = np.asarray(func(b[index], abscissa), dtype=float).reshape(-1)
        if not const:
            design = design[:, 1:]
        return design

    def residual(b):
        design = columns(b)
        coeff = qr_solve(design, ordinate)
        return design @ coeff - ordinate

    fit = lsqnonlin(residual, start)
    rates = fit["x"]
    design = columns(rates)
    coeff = qr_solve(design, ordinate)
    if const:
        a0 = float(coeff[0])
        amplitudes = coeff[1:]
    else:
        a0 = 0.0
        amplitudes = coeff
    return {"a0": a0, "a": np.asarray(amplitudes, dtype=float).reshape(-1), "b": rates, "ssq": fit["ssq"]}
