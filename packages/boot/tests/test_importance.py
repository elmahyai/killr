"""Importance sampling weights and estimates, checked against R boot 1.3-32."""

from __future__ import annotations

import shutil
import subprocess
import textwrap
import warnings

import numpy as np
import pytest

from boot.importance import imp_moments, imp_prob, imp_quantile, imp_weights


def test_constant_weights_use_the_sample_mean_and_variance():
    moments = imp_moments(t=np.arange(1, 21), w=np.repeat(2.0, 20))
    for piece in (moments["raw"], moments["rat"], moments["reg"]):
        assert piece[0] == pytest.approx(10.5)
        assert piece[1] == pytest.approx(35.0)


def test_supplied_weights_do_not_need_a_bootstrap():
    moments = imp_moments(t=[1.0, 2.0, 4.0], w=[1.0, 1.0, 3.0])
    assert moments["raw"].shape == (2,)
    with pytest.raises(ValueError, match="bootstrap replicates must be supplied"):
        imp_moments()
    with pytest.raises(ValueError, match="either 'boot.out' or 'w' must be specified"):
        imp_moments(t=[1.0, 2.0])
    with pytest.raises(ValueError, match="either 'boot.out' or 'w' must be specified"):
        imp_prob(t=[1.0, 2.0], t0=1.0)
    with pytest.raises(ValueError, match="either 'boot.out' or 'w' must be specified"):
        imp_quantile(t=[1.0, 2.0])


def test_argument_checks_and_the_first_index():
    boot_out = {
        "R": 2,
        "frequency": np.array([[1.0, 1.0], [2.0, 0.0]]),
        "strata": np.array([1, 1]),
        "weights": np.array([0.25, 0.75]),
        "t": np.array([[1.0, 10.0], [3.0, 30.0]]),
        "t0": np.array([1.5, 15.0]),
        "data": np.array([1.0, 2.0]),
    }
    with pytest.raises(ValueError, match="0 elements not allowed in 'q'"):
        imp_weights(boot_out, q=[0.0, 1.0])
    assert np.all(imp_weights(boot_out, q=[0.25, 0.75]) == 1.0)
    with pytest.warns(UserWarning, match="only first element of 'index' used"):
        from_both = imp_moments(boot_out, index=[1, 2])
    first = imp_moments(boot_out, index=1)
    assert np.allclose(from_both["raw"], first["raw"])
    second = imp_moments(boot_out, index=2)
    assert second["raw"][0] != pytest.approx(first["raw"][0])
    with pytest.warns(UserWarning, match="no non-missing arguments to max; returning -Inf"):
        quantiles = imp_quantile(t=[1.0, 2.0, 3.0], w=[1.0, 1.0, 1.0], alpha=[0.0])
    assert np.isneginf(quantiles["raw"][0])


def test_matches_r_boot_1_3_32():
    if shutil.which("Rscript") is None:
        pytest.skip("Rscript is unavailable")
    cases = _run_r(_R_SCRIPT)
    _compare_case("main", cases["main"], second=True, default_probability=True)
    _compare_case("mix", cases["mix"], second=False, default_probability=False)
    _compare_case("zero", cases["zero"], second=False, default_probability=False)
    _compare_case("factor", cases["factor"], second=False, default_probability=False)
    _compare_direct(cases["direct"])


def _compare_case(name, case, second, default_probability):
    boot_out = {
        "data": case["data"],
        "strata": case["strata"],
        "R": case["R"],
        "t0": case["t0"],
        "t": case["t"],
        "weights": case["weights"],
        "frequency": case["frequency"],
    }
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        weights = imp_weights(boot_out)
        defensive = imp_weights(boot_out, def_=True)
        separate = imp_weights(boot_out, def_=False)
        moments = imp_moments(boot_out, index=1)
        quantiles = imp_quantile(boot_out, index=1)
        supplied = imp_moments(t=case["t"][:, 0], w=weights)
        held = case["t"][:, 0].copy()
        held[0] = np.nan
        held[1] = np.inf
        without_nonfinite = imp_moments(t=held, w=weights)
        if default_probability:
            probability = imp_prob(boot_out, index=1)
        else:
            thresholds = np.array(
                [case["t0"][0] - 10.0, case["t0"][0], case["t0"][0] + 10.0]
            )
            probability = imp_prob(boot_out, index=1, t0=thresholds)
    pairs = {
        "imp.weights": weights,
        "imp.weights.def": defensive,
        "imp.weights.nodef": separate,
        "moments.raw": moments["raw"],
        "moments.rat": moments["rat"],
        "moments.reg": moments["reg"],
        "quantile.raw": quantiles["raw"],
        "quantile.rat": quantiles["rat"],
        "quantile.reg": quantiles["reg"],
        "moments.supplied.raw": supplied["raw"],
        "moments.na.raw": without_nonfinite["raw"],
        "moments.na.reg": without_nonfinite["reg"],
        "prob.raw": probability["raw"],
        "prob.rat": probability["rat"],
        "prob.reg": probability["reg"],
    }
    if "imp.weights.q" in case:
        pairs["imp.weights.q"] = imp_weights(boot_out, q=case["weights"].reshape(-1))
    if name == "mix":
        target = np.resize(np.array([1.0, 2.0]), case["data"].shape[0])
        pairs["imp.weights.qcustom"] = imp_weights(boot_out, def_=False, q=target)
    elif "imp.weights.qcustom" in case:
        target = np.ones(case["data"].shape[0])
        target[0] = 3.0
        pairs["imp.weights.qcustom"] = imp_weights(boot_out, q=target)
    if second:
        second_moments = imp_moments(boot_out, index=2)
        pairs["moments2.raw"] = second_moments["raw"]
        pairs["moments2.rat"] = second_moments["rat"]
        pairs["moments2.reg"] = second_moments["reg"]
    for key, got in pairs.items():
        assert _max_abs_diff(got, case[key]) <= 1e-8, (name, key)


def _compare_direct(case):
    replicates = np.array([1, 1, 1, 2, 2, 3, 4, 8, np.nan, np.inf])
    weights = np.array([0.1, 5, 0.2, 0.3, 4, 0.4, 1, 1, 2, 3])
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        moments = imp_moments(t=replicates, w=weights)
        quantiles = imp_quantile(
            t=replicates, w=weights, alpha=[0.05, 0.2, 0.5, 0.8, 0.95]
        )
        probability = imp_prob(t=replicates, w=weights, t0=[-1, 1, 2, 8, 100])
        constant = imp_moments(t=np.arange(1, 21), w=np.repeat(2.0, 20))
        capped = imp_prob(t=np.array([1.0, 2.0, 3.0]), w=np.array([10.0, 10.0, 10.0]), t0=[0, 2, 3])
    pairs = {
        "direct.moments.raw": moments["raw"],
        "direct.moments.rat": moments["rat"],
        "direct.moments.reg": moments["reg"],
        "direct.q.raw": quantiles["raw"],
        "direct.q.rat": quantiles["rat"],
        "direct.q.reg": quantiles["reg"],
        "direct.p.raw": probability["raw"],
        "direct.p.rat": probability["rat"],
        "direct.p.reg": probability["reg"],
        "const.moments": np.concatenate([constant["raw"], constant["rat"], constant["reg"]]),
        "cap.raw": capped["raw"],
        "cap.rat": capped["rat"],
        "cap.reg": capped["reg"],
    }
    for key, got in pairs.items():
        assert _max_abs_diff(got, case[key]) <= 1e-8, key


def _max_abs_diff(got, expected) -> float:
    got = np.asarray(got, dtype=np.float64).reshape(-1)
    expected = np.asarray(expected, dtype=np.float64).reshape(-1)
    assert got.shape == expected.shape
    both_infinite = np.isinf(got) & np.isinf(expected) & (np.sign(got) == np.sign(expected))
    both_missing = np.isnan(got) & np.isnan(expected)
    difference = np.zeros(got.shape, dtype=np.float64)
    comparable = ~(both_infinite | both_missing)
    difference[comparable] = np.abs(got[comparable] - expected[comparable])
    assert np.all(np.isfinite(difference))
    if difference.size == 0:
        return 0.0
    return float(np.max(difference))


def _run_r(script: str) -> dict:
    completed = subprocess.run(
        ["Rscript", "-e", script],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        pytest.fail(f"Rscript failed: {completed.stderr}")
    lines = completed.stdout.splitlines()
    if not lines or lines[0] != "1.3-32":
        pytest.fail(f"expected boot 1.3-32, got {completed.stdout[:200]!r}")
    return _parse_cases(lines[1:])


def _parse_cases(lines: list[str]) -> dict:
    cases = {}
    current = None
    index = 0
    while index < len(lines):
        parts = lines[index].split()
        if not parts:
            index += 1
            continue
        if parts[0] == "END":
            break
        if parts[0] == "CASE":
            current = {}
            cases[parts[1]] = current
            index += 1
            continue
        if parts[0] == "VEC":
            name, count = parts[1], int(parts[2])
            current[name] = np.array(
                [float(lines[index + 1 + item]) for item in range(count)],
                dtype=np.float64,
            )
            index += 1 + count
            continue
        if parts[0] == "MAT":
            name, rows, cols = parts[1], int(parts[2]), int(parts[3])
            values = [float(lines[index + 1 + item]) for item in range(rows * cols)]
            current[name] = np.array(values, dtype=np.float64).reshape(rows, cols)
            index += 1 + rows * cols
            continue
        pytest.fail(f"unexpected R output: {lines[index]!r}")
    return cases


_R_SCRIPT = textwrap.dedent(
    r"""
    suppressPackageStartupMessages(library(boot))
    cat(packageDescription("boot")$Version, "\n", sep = "")
    dump_vec <- function(name, x) {
      x <- as.vector(x)
      cat("VEC", name, length(x), "\n", sep = " ")
      cat(sprintf("%.17g", x), sep = "\n")
    }
    dump_mat <- function(name, x) {
      x <- as.matrix(x)
      cat("MAT", name, nrow(x), ncol(x), "\n", sep = " ")
      cat(sprintf("%.17g", as.vector(t(x))), sep = "\n")
    }
    emit_case <- function(tag, b, second = FALSE, default_prob = FALSE) {
      cat("CASE", tag, "\n", sep = " ")
      f <- boot.array(b)
      dump_vec("data", b$data)
      dump_vec("strata", as.numeric(b$strata))
      dump_vec("R", b$R)
      dump_vec("t0", b$t0)
      dump_mat("t", b$t)
      dump_mat("weights", b$weights)
      dump_mat("frequency", f)
      w <- imp.weights(b)
      dump_vec("imp.weights", w)
      dump_vec("imp.weights.def", imp.weights(b, def = TRUE))
      dump_vec("imp.weights.nodef", imp.weights(b, def = FALSE))
      if (length(b$R) == 1L && all(b$weights > 0))
        dump_vec("imp.weights.q", imp.weights(b, q = as.vector(b$weights)))
      if (length(b$R) == 1L) {
        qcustom <- rep(1, length(b$data))
        qcustom[1] <- 3
        dump_vec("imp.weights.qcustom", imp.weights(b, q = qcustom))
      } else {
        dump_vec("imp.weights.qcustom", imp.weights(b, def = FALSE, q = rep(c(1, 2), length.out = length(b$data))))
      }
      mom <- imp.moments(b, index = 1)
      dump_vec("moments.raw", mom$raw)
      dump_vec("moments.rat", mom$rat)
      dump_vec("moments.reg", mom$reg)
      if (second) {
        mom2 <- imp.moments(b, index = 2)
        dump_vec("moments2.raw", mom2$raw)
        dump_vec("moments2.rat", mom2$rat)
        dump_vec("moments2.reg", mom2$reg)
      }
      if (default_prob) {
        pr <- imp.prob(b, index = 1)
      } else {
        pr <- imp.prob(b, index = 1, t0 = c(b$t0[1] - 10, b$t0[1], b$t0[1] + 10))
      }
      dump_vec("prob.raw", pr$raw)
      dump_vec("prob.rat", pr$rat)
      dump_vec("prob.reg", pr$reg)
      qq <- suppressWarnings(imp.quantile(b, index = 1))
      dump_vec("quantile.raw", qq$raw)
      dump_vec("quantile.rat", qq$rat)
      dump_vec("quantile.reg", qq$reg)
      momw <- imp.moments(t = b$t[, 1], w = w)
      dump_vec("moments.supplied.raw", momw$raw)
      tt <- b$t[, 1]
      tt[1] <- NA
      tt[2] <- Inf
      momna <- imp.moments(t = tt, w = w)
      dump_vec("moments.na.raw", momna$raw)
      dump_vec("moments.na.reg", momna$reg)
    }
    set.seed(1)
    n <- 40
    x <- rnorm(n)
    strata <- rep(1:2, each = n / 2)
    wts <- runif(n)
    stat <- function(d, w) c(sum(d * w) / sum(w), sum(d * d * w) / sum(w))
    b1 <- boot(x, stat, R = 200, stype = "w", strata = strata, weights = wts)
    emit_case("main", b1, TRUE, TRUE)
    set.seed(2)
    n <- 16
    x <- rnorm(n)
    strata <- rep(1:2, each = n / 2)
    W <- rbind(runif(n), runif(n))
    stat1 <- function(d, w) sum(d * w) / sum(w)
    b2 <- boot(x, stat1, R = c(12, 8), stype = "w", strata = strata, weights = W)
    emit_case("mix", b2, FALSE, FALSE)
    set.seed(3)
    x <- rnorm(8)
    wts <- c(0, runif(7))
    b3 <- boot(x, stat1, R = 15, stype = "w", weights = wts)
    emit_case("zero", b3, FALSE, FALSE)
    set.seed(4)
    x <- rnorm(8)
    strata <- factor(c(7, 7, 7, 7, 8, 8, 8, 8))
    wts <- runif(8)
    b4 <- boot(x, stat1, R = 12, stype = "w", strata = strata, weights = wts)
    emit_case("factor", b4, FALSE, FALSE)
    cat("CASE direct\n")
    tt <- c(1, 1, 1, 2, 2, 3, 4, 8, NA, Inf)
    ww <- c(0.1, 5, 0.2, 0.3, 4, 0.4, 1, 1, 2, 3)
    mom <- imp.moments(t = tt, w = ww)
    dump_vec("direct.moments.raw", mom$raw)
    dump_vec("direct.moments.rat", mom$rat)
    dump_vec("direct.moments.reg", mom$reg)
    qq <- suppressWarnings(imp.quantile(t = tt, w = ww, alpha = c(0.05, 0.2, 0.5, 0.8, 0.95)))
    dump_vec("direct.q.raw", qq$raw)
    dump_vec("direct.q.rat", qq$rat)
    dump_vec("direct.q.reg", qq$reg)
    pr <- imp.prob(t = tt, w = ww, t0 = c(-1, 1, 2, 8, 100))
    dump_vec("direct.p.raw", pr$raw)
    dump_vec("direct.p.rat", pr$rat)
    dump_vec("direct.p.reg", pr$reg)
    momc <- imp.moments(t = 1:20, w = rep(2, 20))
    dump_vec("const.moments", unlist(momc))
    prcap <- imp.prob(t = c(1, 2, 3), w = c(10, 10, 10), t0 = c(0, 2, 3))
    dump_vec("cap.raw", prcap$raw)
    dump_vec("cap.rat", prcap$rat)
    dump_vec("cap.reg", prcap$reg)
    cat("END\n")
    """
)
