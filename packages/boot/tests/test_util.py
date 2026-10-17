"""Checks for boot's small numeric helpers against installed boot 1.3-32."""

from __future__ import annotations

import math
import shutil
import subprocess
import textwrap

import numpy as np
import pytest

from boot.util import corr, cum3, freq_array, inv_logit, k3_linear, logit, var_linear

TOLERANCE = 1e-8

_R_SCRIPT = textwrap.dedent(
    """
    suppressPackageStartupMessages(library(boot))
    stopifnot(packageDescription("boot")$Version == "1.3-32")

    emit <- function(name, value) {
      if (is.matrix(value)) {
        flat <- as.vector(t(value))
        body <- if (length(flat)) paste(sprintf("%.17g", flat), collapse = " ") else ""
        cat(name, "matrix", nrow(value), ncol(value), body, "\\n", sep = " ")
      } else if (length(value) > 1L) {
        cat(name, "vector", length(value), paste(sprintf("%.17g", value), collapse = " "), "\\n", sep = " ")
      } else if (length(value) == 0L) {
        cat(name, "empty", "\\n", sep = " ")
      } else if (is.na(value) && !is.nan(value)) {
        cat(name, "scalar", "NA", "\\n", sep = " ")
      } else {
        cat(name, "scalar", sprintf("%.17g", value), "\\n", sep = " ")
      }
    }

    d <- cbind(c(1, 2, 3, 4, 5), c(2, 4, 5, 4, 5))
    emit("corr_eq", corr(d))
    emit("corr_w", corr(d, c(1, 1, 1, 1, 5)))
    emit("corr_w1", corr(d, 2))
    d_na <- d
    d_na[1, 1] <- NA
    emit("corr_na", corr(d_na))
    emit("corr_const", corr(cbind(1:4, c(1, 1, 1, 1))))
    emit("corr_extra", corr(cbind(1:4, 2:5, 8:11)))
    emit("corr_empty", corr(matrix(numeric(0), 0, 2)))
    emit("corr_w0", suppressWarnings(corr(cbind(1:4, 2:5), numeric(0))))

    n <- 5000
    x <- seq_len(n)
    y <- (x %% 7) + (x %/% 3) / 10
    emit("corr_big", corr(cbind(x, y), x))

    i <- matrix(c(1, 2, 1, 3, 4, 2, 2, 1, 4, 3, 1, 2), 3, 4, byrow = TRUE)
    emit("freq", freq.array(i))
    emit("freq_one_col", freq.array(matrix(c(1, 1, 1), ncol = 1)))
    emit("freq_one", freq.array(matrix(1, 1, 1)))
    emit("freq_empty_r", freq.array(matrix(integer(0), 0, 3)))
    emit("freq_empty_c", freq.array(matrix(integer(0), 3, 0)))
    emit("freq_frac", freq.array(matrix(c(-1, 0.9, 3.9, 4, NA, 2), nrow = 2)))
    emit("freq_trunc", freq.array(matrix(c(1, 4, 4.2, 0), nrow = 1)))
    R <- 200L
    cols <- 40L
    rr <- matrix(rep(seq_len(R), cols), R, cols)
    cc <- matrix(rep(seq_len(cols), each = R), R, cols)
    emit("freq_big", freq.array(((rr + 3L * cc) %% cols) + 1L))

    L <- c(1, 2, 3, 4, 5)
    emit("var", var.linear(L))
    emit("var_st", var.linear(L, c(1, 1, 2, 2, 2)))
    emit("var_gap", var.linear(L, c(2, 2, 5, 5, 5)))
    emit("var_fac", var.linear(L, factor(c("b", "b", "a", "a", "a"))))
    emit("var_na", var.linear(L, c(1, 1, NA, 2, 2)))
    emit("var_empty", var.linear(numeric(0)))
    emit("k3", k3.linear(L))
    emit("k3_st", k3.linear(L, c(1, 1, 2, 2, 2)))
    emit("k3_one", k3.linear(3))

    big <- sin(seq_len(n)) + 0.25
    strata <- rep(1:4, length.out = n)
    emit("var_big", var.linear(big, strata))
    emit("k3_big", k3.linear(big, strata))

    a <- c(1, 2, 4, 7, 11)
    emit("cum", cum3(a))
    emit("cum_bias", cum3(a, unbiased = FALSE))
    emit("cum_b", cum3(a, c(1, 3, 2, 5, 8)))
    emit("cum_abc", cum3(1:5, c(1, 3, 2, 0, 4), c(2, 2, 1, 5, 3)))
    emit("cum_short", suppressWarnings(cum3(a, c(1, 2))))
    emit("cum_empty", cum3(numeric(0)))
    emit("cum_n1", cum3(1))
    emit("cum_n2", cum3(c(1, 2)))
    emit("cum_n1f", cum3(1, unbiased = FALSE))
    aa <- (seq_len(n) %% 5) + 1
    bb <- (seq_len(n) %% 3) + 0.5
    cc <- (seq_len(n) %/% 4) + 1
    emit("cum_big", cum3(aa, bb, cc))

    emit("logit", logit(c(0, 0.25, 0.5, 0.75, 1)))
    emit("logit_bad", suppressWarnings(logit(c(-0.1, 0.2, 1.2, NA))))
    emit("logit_mat", logit(matrix(c(0.2, 0.8), nrow = 2)))
    emit("logit_empty", logit(numeric(0)))
    emit("logit_big", logit(seq_len(n) / (n + 1)))
    emit("inv", inv.logit(c(-Inf, -1, 0, 1, Inf)))
    emit("inv_na", inv.logit(c(NA, NaN)))
    xx <- -20 + (seq_len(n) - 1) * 40 / (n - 1)
    emit("inv_big", inv.logit(xx))

    ratio <- function(d, w) sum(d$x * w) / sum(d$u * w)
    influence <- empinf(data = city, statistic = ratio)
    emit("city_var", var.linear(influence))
    emit("city_k3", k3.linear(influence))
    """
)


@pytest.fixture(scope="module")
def reference():
    if shutil.which("Rscript") is None:
        pytest.fail("Rscript is not installed")
    result = subprocess.run(
        ["Rscript", "-e", _R_SCRIPT],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        pytest.fail(result.stderr)
    return _parse(result.stdout)


def test_corr(reference):
    d = np.array([[1, 2], [2, 4], [3, 5], [4, 4], [5, 5]], dtype=np.float64)
    assert_close(corr(d), reference["corr_eq"])
    assert_close(corr(d, [1, 1, 1, 1, 5]), reference["corr_w"])
    assert_close(corr(d, 2), reference["corr_w1"])
    missing = d.copy()
    missing[0, 0] = np.nan
    assert_nan(corr(missing), reference["corr_na"])
    assert_nan(corr(np.column_stack([np.arange(1, 5), np.ones(4)])), reference["corr_const"])
    assert_close(corr(np.column_stack([np.arange(1, 5), np.arange(2, 6), np.arange(8, 12)])), reference["corr_extra"])
    assert_nan(corr(np.zeros((0, 2))), reference["corr_empty"])
    assert_nan(corr(np.column_stack([np.arange(1, 5), np.arange(2, 6)]), np.array([])), reference["corr_w0"])
    with pytest.raises(ValueError, match="subscript out of bounds"):
        corr(np.arange(4).reshape(4, 1))
    with pytest.raises(ValueError, match="incorrect number of dimensions"):
        corr(np.arange(4))
    n = 5000
    x = np.arange(1, n + 1, dtype=np.float64)
    y = (x % 7) + np.floor(x / 3) / 10
    assert_close(corr(np.column_stack([x, y]), x), reference["corr_big"])


def test_freq_array(reference):
    indices = np.array(
        [[1, 2, 1, 3], [4, 2, 2, 1], [4, 3, 1, 2]],
        dtype=np.int32,
    )
    assert_matrix(freq_array(indices), reference["freq"])
    assert freq_array(indices).dtype == np.int32
    assert_matrix(freq_array(np.array([[1], [1], [1]])), reference["freq_one_col"])
    assert_matrix(freq_array(np.array([[1]])), reference["freq_one"])
    assert_matrix(freq_array(np.zeros((0, 3), dtype=np.int32)), reference["freq_empty_r"])
    assert_matrix(freq_array(np.zeros((3, 0), dtype=np.int32)), reference["freq_empty_c"])
    fractional = np.array([[-1.0, 3.9, np.nan], [0.9, 4.0, 2.0]])
    assert_matrix(freq_array(fractional), reference["freq_frac"])
    assert_matrix(freq_array(np.array([[1.0, 4.0, 4.2, 0.0]])), reference["freq_trunc"])
    with pytest.raises(ValueError, match="dim\\(X\\) must have a positive length"):
        freq_array(np.array([1, 2, 3]))
    replicates, cols = 200, 40
    row = np.arange(1, replicates + 1)[:, None]
    col = np.arange(1, cols + 1)[None, :]
    big = ((row + 3 * col) % cols) + 1
    assert_matrix(freq_array(big), reference["freq_big"])


def test_var_linear(reference):
    values = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    assert_close(var_linear(values), reference["var"])
    assert_close(var_linear(values, [1, 1, 2, 2, 2]), reference["var_st"])
    assert_close(var_linear(values, [2, 2, 5, 5, 5]), reference["var_gap"])
    assert_close(var_linear(values, ["b", "b", "a", "a", "a"]), reference["var_fac"])
    assert_nan(var_linear(values, [1, 1, np.nan, 2, 2]), reference["var_na"])
    assert_close(var_linear(np.array([])), reference["var_empty"])
    with pytest.raises(ValueError, match="arguments must have same length"):
        var_linear(values, [1, 1])
    n = 5000
    big = np.sin(np.arange(1, n + 1, dtype=np.float64)) + 0.25
    strata = np.resize(np.arange(1, 5), n)
    assert_close(var_linear(big, strata), reference["var_big"])
    assert_close(var_linear(_CITY_INFLUENCE), reference["city_var"])


def test_k3_linear(reference):
    values = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    assert_close(k3_linear(values), reference["k3"])
    assert_close(k3_linear(values, [1, 1, 2, 2, 2]), reference["k3_st"])
    assert_close(k3_linear(3), reference["k3_one"])
    n = 5000
    big = np.sin(np.arange(1, n + 1, dtype=np.float64)) + 0.25
    strata = np.resize(np.arange(1, 5), n)
    assert_close(k3_linear(big, strata), reference["k3_big"])
    assert_close(k3_linear(_CITY_INFLUENCE), reference["city_k3"])


def test_cum3(reference):
    a = np.array([1.0, 2.0, 4.0, 7.0, 11.0])
    assert_close(cum3(a), reference["cum"])
    assert_close(cum3(a, unbiased=False), reference["cum_bias"])
    assert_close(cum3(a, [1, 3, 2, 5, 8]), reference["cum_b"])
    assert_close(cum3(np.arange(1, 6), [1, 3, 2, 0, 4], [2, 2, 1, 5, 3]), reference["cum_abc"])
    with pytest.warns(RuntimeWarning, match="not a multiple"):
        assert_close(cum3(a, [1, 2]), reference["cum_short"])
    assert_close(cum3(np.array([])), reference["cum_empty"])
    assert_nan(cum3(1), reference["cum_n1"])
    assert_nan(cum3([1, 2]), reference["cum_n2"])
    assert_close(cum3(1, unbiased=False), reference["cum_n1f"])
    with pytest.raises(ValueError, match="length > 1"):
        cum3(a, unbiased=[True, False])
    n = 5000
    index = np.arange(1, n + 1, dtype=np.float64)
    assert_close(
        cum3(index % 5 + 1, index % 3 + 0.5, np.floor(index / 4) + 1),
        reference["cum_big"],
    )


def test_logit(reference):
    assert_vector(logit([0, 0.25, 0.5, 0.75, 1]), reference["logit"])
    with pytest.warns(RuntimeWarning, match="NaNs produced"):
        assert_vector(logit([-0.1, 0.2, 1.2, np.nan]), reference["logit_bad"])
    assert_matrix(logit(np.array([[0.2], [0.8]])), reference["logit_mat"])
    assert_vector(logit(np.array([])), reference["logit_empty"])
    assert logit(0.5) == 0.0
    assert math.isinf(logit(0.0)) and logit(0.0) < 0
    assert math.isinf(logit(1.0)) and logit(1.0) > 0
    n = 5000
    assert_vector(logit((np.arange(1, n + 1, dtype=np.float64)) / (n + 1)), reference["logit_big"])


def test_inv_logit(reference):
    assert_vector(inv_logit([-np.inf, -1.0, 0.0, 1.0, np.inf]), reference["inv"])
    assert_vector(inv_logit([np.nan, np.nan]), reference["inv_na"])
    assert inv_logit(0) == 0.5
    assert inv_logit(-np.inf) == 0.0
    assert inv_logit(np.inf) == 1.0
    n = 5000
    grid = -20 + np.arange(n, dtype=np.float64) * 40 / (n - 1)
    assert_vector(inv_logit(grid), reference["inv_big"])
    sample = np.array([0.05, 0.2, 0.5, 0.8, 0.95])
    assert_vector(inv_logit(logit(sample)), sample)


_CITY_INFLUENCE = np.array(
    [
        -1.0436781528389005,
        -0.5841776310155922,
        -0.37092459027388003,
        -0.1895899564963166,
        0.031641416033956205,
        0.10544878455531759,
        0.09236344956198295,
        0.20365074168582353,
        1.0217827978342697,
        0.733811322344291,
    ]
)


def assert_close(actual, expected):
    assert_vector(np.asarray(actual, dtype=np.float64).reshape(-1), np.asarray(expected, dtype=np.float64).reshape(-1))


def assert_nan(actual, expected):
    assert math.isnan(float(expected))
    assert math.isnan(float(actual))


def assert_vector(actual, expected):
    actual = np.asarray(actual, dtype=np.float64).reshape(-1)
    expected = np.asarray(expected, dtype=np.float64).reshape(-1)
    assert actual.shape == expected.shape
    for got, want in zip(actual, expected, strict=True):
        if math.isnan(want):
            assert math.isnan(got)
        elif math.isinf(want):
            assert got == want
        else:
            assert got == pytest.approx(want, abs=TOLERANCE, rel=0)


def assert_matrix(actual, expected):
    actual = np.asarray(actual)
    assert actual.shape == expected.shape
    assert_vector(np.ravel(actual), np.ravel(expected))


def _parse(text: str) -> dict:
    parsed = {}
    for line in text.splitlines():
        if not line.strip():
            continue
        parts = line.split()
        name, kind = parts[0], parts[1]
        rest = " ".join(parts[2:])
        if kind == "scalar":
            parsed[name] = _number(rest.strip())
        elif kind == "empty":
            parsed[name] = np.array([])
        elif kind == "vector":
            length, raw = rest.split(maxsplit=1) if rest.strip() else ("0", "")
            values = _numbers(raw) if int(length) else np.array([])
            assert values.size == int(length)
            parsed[name] = values
        elif kind == "matrix":
            rows, cols, *raw = rest.split()
            values = np.array([_number(item) for item in raw], dtype=np.float64)
            parsed[name] = values.reshape(int(rows), int(cols))
        else:
            raise AssertionError(line)
    return parsed


def _numbers(text: str) -> np.ndarray:
    if not text.strip():
        return np.array([], dtype=np.float64)
    return np.array([_number(item) for item in text.split()], dtype=np.float64)


def _number(text: str) -> float:
    if text in {"NA", "NaN"}:
        return float("nan")
    if text == "Inf":
        return float("inf")
    if text == "-Inf":
        return float("-inf")
    return float(text)
