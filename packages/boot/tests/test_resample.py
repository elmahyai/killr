"""Bootstrap resampling against the installed CRAN boot 1.3-32."""

from __future__ import annotations

import math
import shutil
import subprocess
import textwrap
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pytest

from boot.resample import boot, boot_array, c_boot, jack_after_boot, plot_boot, print_boot
from boot.rng import set_seed, unif

TOLERANCE = 1e-8
DATA = np.arange(1, 11, dtype=float)


def stat(d, i):
    """Mean of the resample. Indices are 1-based, as R passes them."""
    index = np.asarray(i, dtype=float)
    if not np.all(np.isfinite(index)):
        return np.nan
    return float(np.mean(np.asarray(d, dtype=float)[index.astype(int) - 1]))


def first_case(d, i):
    return float(np.asarray(d, dtype=float)[int(np.asarray(i, dtype=float)[0]) - 1])


@pytest.fixture(autouse=True)
def _close_figures():
    yield
    plt.close("all")


def _r_reference():
    if shutil.which("Rscript") is None:
        return None
    script = textwrap.dedent(
        r"""
        suppressPackageStartupMessages(library(boot))
        stopifnot(packageVersion("boot") == "1.3.32")
        stat <- function(d, i) mean(d[i])
        pos <- function(d, i) d[i[1]]
        emit <- function(name, v) {
          cat("## ", name, "\n", sep="")
          cat(sprintf("%.17g\n", as.numeric(v)), sep="")
        }
        set.seed(1)
        b <- boot(1:10, stat, R=50)
        emit("t0", b$t0)
        emit("t", b$t)
        emit("idx", boot.array(b, indices=TRUE))
        emit("freq", boot.array(b))
        t <- b$t[,1]
        t0 <- b$t0[1]
        rg <- range(t)
        rg <- rg + 0.05 * c(-1, 1) * diff(rg)
        nclass <- min(max(ceiling(length(t)/25), 10), 100)
        lc <- diff(rg)/(nclass - 2)
        n1 <- ceiling((t0 - rg[1])/lc)
        n2 <- ceiling((rg[2] - t0)/lc)
        bks <- t0 + (-n1:n2)*lc
        h <- hist(t, breaks=bks, plot=FALSE)
        emit("breaks", h$breaks)
        emit("counts", h$counts)
        emit("density", h$density)
        emit("qqx", qnorm((1:50)/51))
        emit("qqy", sort(t))
        emit("line", c(mean(t), sqrt(var(t))))
        f <- boot.array(b)
        alpha <- c(0.05, 0.1, 0.16, 0.5, 0.84, 0.9, 0.95)
        n <- 10
        J <- numeric(n)
        percentiles <- matrix(NA_real_, length(alpha), n)
        for (j in 1:n) {
          values <- t[f[, j] == 0]
          J[j] <- mean(values)
          percentiles[, j] <- quantile(values, alpha) - J[j]
        }
        Js <- ((n - 1) * (mean(J) - J)) / sqrt(var((n - 1) * (mean(J) - J)))
        ord <- order(Js)
        emit("J", sort(Js))
        emit("p1", percentiles[1, ord])
        emit("horiz", quantile(t, alpha) - mean(t))
        emit("order", ord)
        set.seed(1)
        b <- boot(1:10, stat, R=20, strata=rep(1:2, each=5))
        emit("st_t", b$t)
        emit("st_idx", boot.array(b, indices=TRUE))
        set.seed(1)
        b <- boot(1:10, stat, R=20, sim="balanced")
        emit("bal_t", b$t)
        emit("bal_idx", boot.array(b, indices=TRUE))
        set.seed(1)
        b <- boot(1:10, pos, R=20, sim="permutation")
        emit("perm_t", b$t)
        emit("perm_idx", boot.array(b, indices=TRUE))
        set.seed(1)
        b <- boot(1:10, stat, R=20, sim="antithetic")
        emit("anti_t", b$t)
        emit("anti_L", b$L)
        emit("anti_idx", boot.array(b, indices=TRUE))
        set.seed(1)
        b <- boot(1:10, stat, R=6, sim="antithetic", strata=rep(1:2, each=5))
        emit("anti_st", b$t)
        set.seed(1)
        rg <- function(d, mle) runif(length(d))
        st <- function(d) mean(d)
        b <- boot(1:10, st, R=20, sim="parametric", ran.gen=rg, mle=mean(1:10))
        emit("par_t0", b$t0)
        emit("par_t", b$t)
        set.seed(1)
        wts <- c(5, rep(1, 9))
        b <- boot(1:10, stat, R=10, weights=wts)
        emit("imp_t", b$t)
        emit("imp_idx", boot.array(b, indices=TRUE))
        set.seed(1)
        b <- boot(1:10, stat, R=8, simple=TRUE)
        emit("simple_t", b$t)
        set.seed(1)
        b1 <- boot(1:10, stat, R=10)
        set.seed(2)
        b2 <- boot(1:10, stat, R=15)
        emit("c_t", c(b1, b2)$t)
        cat("## c_R\n25\n")
        cat("## qn\n")
        cat(sprintf("%.17g\n", qnorm((1:20)/21)), sep="")
        cat("## qc\n")
        cat(sprintf("%.17g\n", qchisq((1:20)/21, 4)), sep="")
        """
    )
    completed = subprocess.run(
        ["Rscript", "-e", script],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        pytest.skip(completed.stderr.strip() or "Rscript failed")
    blocks = {}
    name = None
    for line in completed.stdout.splitlines():
        if line.startswith("## "):
            name = line[3:].strip()
            blocks[name] = []
        elif name is not None and line:
            blocks[name].append(math.nan if line == "NA" else float(line))
    return {key: np.asarray(value, dtype=float) for key, value in blocks.items()}


@pytest.fixture(scope="module")
def reference():
    return _r_reference()


def _max_diff(got, expected):
    got = np.asarray(got, dtype=float).reshape(-1)
    expected = np.asarray(expected, dtype=float).reshape(-1)
    both_nan = np.isnan(got) & np.isnan(expected)
    diff = np.abs(got - expected)
    diff[both_nan] = 0.0
    return float(np.nanmax(diff))


def test_ordinary_mean_matches_boot(reference):
    if reference is None:
        pytest.skip("Rscript is unavailable")
    set_seed(1)
    result = boot(DATA, stat, R=50)
    assert _max_diff(result.t0, reference["t0"]) <= TOLERANCE
    assert _max_diff(result.t, reference["t"]) <= TOLERANCE
    assert np.array_equal(boot_array(result, indices=True), reference["idx"].reshape(50, 10, order="F"))
    assert np.array_equal(boot_array(result), reference["freq"].reshape(50, 10, order="F"))
    text = str(result)
    assert text == print_boot(result)
    assert "ORDINARY NONPARAMETRIC BOOTSTRAP" in text
    assert "t1*" in text


def test_rng_is_restored_after_boot_array():
    set_seed(1)
    result = boot(DATA, stat, R=10)
    expected = unif()
    set_seed(1)
    result = boot(DATA, stat, R=10)
    boot_array(result)
    assert unif() == expected


def test_stratified_balanced_permutation_and_antithetic(reference):
    if reference is None:
        pytest.skip("Rscript is unavailable")
    set_seed(1)
    stratified = boot(DATA, stat, R=20, strata=np.repeat([1, 2], 5))
    assert _max_diff(stratified.t, reference["st_t"]) <= TOLERANCE
    assert np.array_equal(
        boot_array(stratified, indices=True),
        reference["st_idx"].reshape(20, 10, order="F"),
    )
    assert "STRATIFIED BOOTSTRAP" in str(stratified)

    set_seed(1)
    balanced = boot(DATA, stat, R=20, sim="balanced")
    assert _max_diff(balanced.t, reference["bal_t"]) <= TOLERANCE
    assert np.array_equal(
        boot_array(balanced, indices=True),
        reference["bal_idx"].reshape(20, 10, order="F"),
    )

    set_seed(1)
    permuted = boot(DATA, first_case, R=20, sim="permutation")
    assert _max_diff(permuted.t, reference["perm_t"]) <= TOLERANCE
    assert np.array_equal(
        boot_array(permuted, indices=True),
        reference["perm_idx"].reshape(20, 10, order="F"),
    )

    set_seed(1)
    antithetic = boot(DATA, stat, R=20, sim="antithetic")
    assert _max_diff(antithetic.t, reference["anti_t"]) <= TOLERANCE
    assert _max_diff(antithetic.L, reference["anti_L"]) <= TOLERANCE
    assert np.array_equal(
        np.nan_to_num(boot_array(antithetic, indices=True), nan=-1),
        np.nan_to_num(reference["anti_idx"].reshape(20, 10, order="F"), nan=-1),
    )

    set_seed(1)
    stratified_anti = boot(DATA, stat, R=6, sim="antithetic", strata=np.repeat([1, 2], 5))
    assert _max_diff(stratified_anti.t, reference["anti_st"]) <= TOLERANCE


def test_parametric_importance_and_simple(reference):
    if reference is None:
        pytest.skip("Rscript is unavailable")

    def ran_gen(data, _mle):
        return np.array([unif() for _ in range(len(np.asarray(data)))])

    def mean_only(data):
        return float(np.mean(data))

    set_seed(1)
    parametric = boot(DATA, mean_only, R=20, sim="parametric", ran_gen=ran_gen, mle=float(np.mean(DATA)))
    assert _max_diff(parametric.t0, reference["par_t0"]) <= TOLERANCE
    assert _max_diff(parametric.t, reference["par_t"]) <= TOLERANCE
    with pytest.raises(ValueError, match="parametric"):
        boot_array(parametric)

    set_seed(1)
    weights = np.ones(10)
    weights[0] = 5
    weighted = boot(DATA, stat, R=10, weights=weights)
    assert _max_diff(weighted.t, reference["imp_t"]) <= TOLERANCE
    assert np.array_equal(
        boot_array(weighted, indices=True),
        reference["imp_idx"].reshape(10, 10, order="F"),
    )

    set_seed(1)
    simple = boot(DATA, stat, R=8, simple=True)
    assert _max_diff(simple.t, reference["simple_t"]) <= TOLERANCE


def test_c_boot_stacks_replicates(reference):
    if reference is None:
        pytest.skip("Rscript is unavailable")
    set_seed(1)
    first = boot(DATA, stat, R=10)
    set_seed(2)
    second = boot(DATA, stat, R=15)
    combined = c_boot(first, second)
    assert combined.R == 25
    assert _max_diff(combined.t, reference["c_t"]) <= TOLERANCE
    other = boot(DATA, stat, R=4, sim="permutation")
    with pytest.raises(ValueError, match="same type"):
        c_boot(first, other)


def test_plot_and_jackknife_coordinates(reference):
    if reference is None:
        pytest.skip("Rscript is unavailable")
    set_seed(1)
    result = boot(DATA, stat, R=50)
    series = plot_boot(result)
    assert _max_diff(series["breaks"], reference["breaks"]) <= TOLERANCE
    assert np.array_equal(series["counts"], reference["counts"].astype(int))
    assert _max_diff(series["density"], reference["density"]) <= TOLERANCE
    assert _max_diff(series["qq_x"], reference["qqx"]) <= TOLERANCE
    assert _max_diff(series["qq_y"], reference["qqy"]) <= TOLERANCE
    assert _max_diff(
        [series["line_intercept"], series["line_slope"]],
        reference["line"],
    ) <= TOLERANCE
    assert len(series["figure"].axes) == 2

    jack = jack_after_boot(result)
    assert _max_diff(jack["J"], reference["J"]) <= TOLERANCE
    assert _max_diff(jack["percentiles"][0], reference["p1"]) <= TOLERANCE
    assert _max_diff(jack["horizontal"], reference["horiz"]) <= TOLERANCE
    assert np.array_equal(jack["order"], reference["order"].astype(int))
    assert len(jack["labels"]) == 10


def test_quantiles_match_r(reference):
    if reference is None:
        pytest.skip("Rscript is unavailable")
    from boot.resample import _qchisq, _qnorm

    probs = np.arange(1, 21) / 21
    assert _max_diff([_qnorm(float(p)) for p in probs], reference["qn"]) <= TOLERANCE
    assert _max_diff([_qchisq(float(p), 4) for p in probs], reference["qc"]) <= TOLERANCE


def test_constant_replicates_do_not_draw():
    def constant(_data, _index):
        return 3.0

    set_seed(1)
    result = boot(DATA, constant, R=5)
    series = plot_boot(result)
    assert series["constant"] is True
    assert series["mean"] == pytest.approx(3.0)
