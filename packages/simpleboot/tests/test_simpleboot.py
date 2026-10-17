"""Comparisons against one run of CRAN simpleboot 1.1-8."""

from pathlib import Path

import numpy as np
from boot.rng import set_seed, unif

from simpleboot import (
    fitted_lm_simpleboot,
    lm,
    lm_boot,
    loess,
    loess_boot,
    model_frame_lm_simpleboot,
    one_boot,
    pairs_boot,
    perc,
    samples,
    summary_lm_simpleboot,
    two_boot,
)


def _grab(tag):
    for line in Path(__file__).with_name("ref.txt").read_text().splitlines():
        if line.startswith(tag + " "):
            return np.array([np.nan if part == "NA" else float(part) for part in line.split()[1:]])
    raise KeyError(tag)


def _max(left, right):
    left = np.asarray(left, dtype=float).reshape(-1)
    right = np.asarray(right, dtype=float).reshape(-1)
    return float(np.nanmax(np.abs(left - right)))


def test_one_two_and_pairs():
    x, y = _grab("X"), _grab("Y")
    set_seed(2)
    one = one_boot(x, "mean", 25)
    assert _max(one.t0, _grab("ONE_T0")) < 1e-8
    assert _max(one.t, _grab("ONE_T")) < 1e-8
    assert _max(perc(one), _grab("PERC")) < 1e-8
    set_seed(3)
    two = two_boot(x, y, "median", 20)
    assert _max(two.t0, _grab("TWO_T0")) < 1e-8
    assert _max(two.t, _grab("TWO_T")) < 1e-8
    set_seed(4)
    paired = pairs_boot(x, y, "cor", 15)
    assert _max(paired.t0, _grab("PAIRS_T0")) < 1e-8
    assert _max(paired.t, _grab("PAIRS_T")) < 1e-8


def test_weighted_median_follows_the_probability_sampler():
    x, weights = _grab("X"), _grab("W")
    set_seed(5)
    for _ in range(12):
        unif()
    weighted = one_boot(x, "median", 12, weights=weights)
    assert _max(weighted.t, _grab("WT")) < 1e-8


def test_lm_bootstrap_rows_and_residuals():
    fit = lm("yy ~ xx", {"yy": _grab("LY"), "xx": _grab("LX")})
    set_seed(7)
    boot = lm_boot(fit, 12, ngrid=8)
    assert _max(samples(boot, "coef").ravel(order="F"), _grab("LMCOEF")) < 1e-8
    assert _max(samples(boot, "fitted").ravel(order="F"), _grab("LMFIT")) < 1e-8
    assert _max(summary_lm_simpleboot(boot).stdev_params, _grab("SD")) < 1e-8
    assert _max(fitted_lm_simpleboot(boot).ravel(order="F"), _grab("LMFIT")) < 1e-8
    frame = model_frame_lm_simpleboot(boot)
    assert _max(frame["xx"], _grab("LX")) < 1e-15
    set_seed(8)
    residual = lm_boot(fit, 8, rows=False, ngrid=5)
    assert _max(samples(residual, "coef").ravel(order="F"), _grab("LMRES")) < 1e-8


def test_direct_loess_matches_surface_direct():
    fit = loess("ly ~ lx", {"ly": _grab("OY"), "lx": _grab("OX")}, span=0.5)
    assert _max(fit.fitted_values, _grab("DIRECT")) < 1e-8


def test_studentized_mean():
    xs = np.array(
        [
            -1.480567594919364,
            1.5771694715586291,
            -0.95674447908426852,
            -0.92000524755864099,
            -1.9976420969313426,
            -0.27229604424922993,
            -0.31534871146778415,
            -0.62825523651753756,
        ]
    )
    expected = np.array(
        [
            -0.43211614324158421,
            -0.73334045418122817,
            -0.72871597335398752,
            -1.1810354769703642,
            0.0033225418040739962,
            0.14499377626891771,
            0.0092772660528492451,
            0.027875895268192268,
        ]
    )
    set_seed(13)
    result = one_boot(xs, "mean", 4, student=True, M=3)
    assert _max(result.t.ravel(order="F"), expected) < 1e-8
