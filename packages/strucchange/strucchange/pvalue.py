"""Boundary-crossing p-values for an empirical fluctuation process."""

import warnings

import numpy as np
from scipy.stats import norm

from strucchange.critvals import MAX_L2_P, MEAN_L2_P, SC_MAX_L2, SC_MEAN_L2, SC_ME

# Table 1 of Chu, Hornik, Kuan (1995), before the sqrt(h) rescaling in pvalue.efp.
_MOTION_INCREMENTS = np.array(
    [
        [3.2165, 3.3185, 3.4554, 3.6622, 3.8632, 4.1009],
        [2.9795, 3.0894, 3.2368, 3.4681, 3.6707, 3.9397],
        [2.8289, 2.9479, 3.1028, 3.3382, 3.5598, 3.8143],
        [2.7099, 2.8303, 2.9874, 3.2351, 3.4604, 3.7337],
        [2.6061, 2.7325, 2.8985, 3.1531, 3.3845, 3.6626],
        [2.5111, 2.6418, 2.8134, 3.0728, 3.3102, 3.5907],
        [2.4283, 2.5609, 2.7327, 3.0043, 3.2461, 3.5333],
        [2.3464, 2.4840, 2.6605, 2.9333, 3.1823, 3.4895],
        [2.2686, 2.4083, 2.5899, 2.8743, 3.1229, 3.4123],
        [2.2255, 2.3668, 2.5505, 2.8334, 3.0737, 3.3912],
    ],
    dtype=float,
)

_BM_ALT_P = np.array(
    [
        1, 0.997, 0.99, 0.975, 0.949, 0.912, 0.864, 0.806, 0.739, 0.666,
        0.589, 0.512, 0.437, 0.368, 0.307, 0.253, 0.205, 0.163, 0.129, 0.100,
        0.077, 0.058, 0.043, 0.032, 0.024, 0.018, 0.012, 0.009, 0.006, 0.004,
        0.003, 0.002, 0.001, 0.001, 0.001,
    ],
    dtype=float,
)
_BB_ALT_P = np.array(
    [
        1, 1, 0.997, 0.99, 0.977, 0.954, 0.919, 0.871, 0.812, 0.743,
        0.666, 0.585, 0.504, 0.426, 0.353, 0.288, 0.230, 0.182, 0.142, 0.109,
        0.082, 0.062, 0.046, 0.034, 0.025, 0.017, 0.011, 0.008, 0.005, 0.004,
        0.003, 0.002, 0.001, 0.001, 0.0001,
    ],
    dtype=float,
)


def r_approx(x, y, xout):
    """``approx(..., rule = 2)``: sort ``x``, average ties, hold the ends."""
    x = np.asarray(x, dtype=float).ravel()
    y = np.asarray(y, dtype=float).ravel()
    scalar = np.ndim(xout) == 0
    xout = np.asarray(xout, dtype=float).ravel()
    order = np.argsort(x, kind="mergesort")
    x = x[order]
    y = y[order]
    uniq_x = []
    uniq_y = []
    i = 0
    while i < x.size:
        j = i + 1
        while j < x.size and x[j] == x[i]:
            j += 1
        uniq_x.append(x[i])
        uniq_y.append(float(np.mean(y[i:j])))
        i = j
    xs = np.asarray(uniq_x, dtype=float)
    ys = np.asarray(uniq_y, dtype=float)
    if xs.size == 1:
        out = np.full(xout.shape, ys[0])
    else:
        out = np.interp(xout, xs, ys)
    if scalar:
        return float(out[0])
    return out


def _table_row_pvalue(stat, crit, levels):
    return r_approx(np.concatenate([[0.0], np.asarray(crit, dtype=float)]),
                    np.concatenate([[1.0], 1.0 - np.asarray(levels, dtype=float)]),
                    stat)


def _interpolated_tail(stat, crit_table, table_h, table_p, h):
    table_ipl = np.empty(crit_table.shape[1], dtype=float)
    for i in range(crit_table.shape[1]):
        table_ipl[i] = r_approx(table_h, crit_table[:, i], h)
    return r_approx(np.concatenate([[0.0], table_ipl]),
                    np.concatenate([[1.0], np.asarray(table_p, dtype=float)]),
                    stat)


def pvalue_efp(x, lim_process, alt_boundary, functional="max", h=None, k=None):
    """P-value of a fluctuation functional. ``x`` is the scalar statistic."""
    lim_process = str(lim_process)
    choices = (
        "Brownian motion",
        "Brownian bridge",
        "Brownian motion increments",
        "Brownian bridge increments",
    )
    if lim_process not in choices:
        raise ValueError(f"lim.process should be one of {choices}")
    functional = str(functional)
    if functional not in ("max", "range", "meanL2", "maxL2"):
        raise ValueError("functional should be one of 'max', 'range', 'meanL2', 'maxL2'")
    stat = float(np.asarray(x, dtype=float))
    if k is None:
        raise ValueError("k is required")
    k = int(k)

    if lim_process == "Brownian motion":
        if functional != "max":
            raise ValueError("only max functional implemented for Brownian motion")
        if alt_boundary:
            p = r_approx(np.arange(10, 45) / 10.0, _BM_ALT_P, stat)
        elif stat < 0.3:
            p = 1.0 - 0.1465 * stat
        else:
            p = 2.0 * (
                1.0 - norm.cdf(3.0 * stat)
                + np.exp(-4.0 * stat ** 2) * (norm.cdf(stat) + norm.cdf(5.0 * stat) - 1.0)
                - np.exp(-16.0 * stat ** 2) * (1.0 - norm.cdf(stat))
            )
        return float(1.0 - (1.0 - p) ** k)

    if lim_process == "Brownian bridge":
        if functional == "max":
            if alt_boundary:
                p = r_approx(np.arange(12, 47) / 10.0, _BB_ALT_P, stat)
                return float(1.0 - (1.0 - p) ** k)
            if stat < 0.1:
                return 1.0
            series = 0.0
            for i in range(1, 101):
                series += np.exp(-2.0 * (i ** 2) * (stat ** 2)) * ((-1) ** i)
            return float(1.0 - (1.0 + 2.0 * series) ** k)
        if functional == "range":
            if stat < 0.4:
                return 1.0
            series = 0.0
            for i in range(1, 11):
                series += (4.0 * i ** 2 * stat ** 2 - 1.0) * np.exp(-2.0 * i ** 2 * stat ** 2)
            return float(1.0 - (1.0 - 2.0 * series) ** k)
        if k > 25:
            warnings.warn("number of parameters > 25, critical values for 25 parameters used")
            k = 25
        if functional == "maxL2":
            return float(_table_row_pvalue(stat, SC_MAX_L2[k - 1, :], MAX_L2_P))
        return float(_table_row_pvalue(stat, SC_MEAN_L2[k - 1, :], MEAN_L2_P))

    if lim_process == "Brownian motion increments":
        if alt_boundary:
            raise ValueError("alternative boundaries for Brownian motion increments not available")
        if functional != "max":
            raise ValueError("only max functional for Brownian motion increments available")
        table_h = np.arange(1, 11) * 0.05
        crit = _MOTION_INCREMENTS * np.sqrt(table_h)[:, None]
        table_p = np.array([0.2, 0.15, 0.1, 0.05, 0.025, 0.01])
        p = _interpolated_tail(stat, crit, table_h, table_p, h)
        return float(1.0 - (1.0 - p) ** k)

    # Brownian bridge increments. The moving-estimates table stops at 6 parameters.
    if k > 6:
        k = 6
    if functional == "max":
        crit = SC_ME[((k - 1) * 10):(k * 10), :]
        table_h = np.arange(1, 11) * 0.05
        table_p = np.array([0.1, 0.05, 0.025, 0.01])
        return float(_interpolated_tail(stat, crit, table_h, table_p, h))
    if functional == "range":
        if stat < 0.53:
            return 1.0
        series = 0.0
        for i in range(1, 11):
            series += ((-1) ** (i - 1)) * i * norm.cdf(-i * stat)
        return float(1.0 - (1.0 - 8.0 * series) ** k)
    raise ValueError("only max and range functionals for Brownian bridge increments available")
