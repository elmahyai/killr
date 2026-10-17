"""Checks for binMeans, including a comparison with matrixStats 1.5.0."""

from __future__ import annotations

import subprocess

import numpy as np
import pytest

from matrixstats.binmeans import binMeans


def test_break_lands_on_the_closed_side():
    y = np.array([10.0, 20.0, 30.0])
    x = np.array([1.0, 1.0, 2.0])
    breaks = np.array([0.0, 1.0, 2.0])
    closed = binMeans(y, x, breaks, right=True, count=True)
    assert closed.tolist() == [15.0, 30.0]
    assert closed.count.tolist() == [2, 1]
    opened = binMeans(y, x, breaks, right=False, count=True)
    assert np.isnan(opened[0])
    assert opened[1] == 15.0
    assert opened.count.tolist() == [0, 2]


def test_right_defaults_to_true_and_count_is_optional():
    y = np.array([10.0, 20.0, 30.0])
    x = np.array([1.0, 1.0, 2.0])
    breaks = np.array([0.0, 1.0, 2.0])
    assert binMeans(y, x, breaks).tolist() == binMeans(y, x, breaks, right=True).tolist()
    plain = binMeans(y, x, breaks, count=False)
    assert not hasattr(plain, "count")
    assert plain.dtype == np.float64


def test_missing_values_and_logical_y():
    y = np.array([1.0, np.nan, 3.0, 4.0])
    x = np.array([1.0, 2.0, 3.0, 4.0])
    breaks = np.array([0.5, 2.5, 4.5])
    dropped = binMeans(y, x, breaks, na_rm=True, right=False)
    assert dropped.tolist() == [1.0, 3.5]
    assert dropped.count.tolist() == [1, 2]
    kept = binMeans(y, x, breaks, na_rm=False, right=False)
    assert np.isnan(kept[0]) and kept[1] == 3.5
    assert kept.count.tolist() == [2, 2]
    logical = binMeans([True, False, True], [1, 2, 3], [0.5, 2.5, 3.5], right=False)
    assert logical.tolist() == [0.5, 1.0]
    assert logical.count.tolist() == [2, 1]


def test_errors():
    with pytest.raises(ValueError, match="infinite"):
        binMeans([1.0, np.inf], [1.0, 2.0], [0.0, 3.0])
    with pytest.raises(ValueError, match="different lengths"):
        binMeans([1.0], [1.0, 2.0], [0.0, 3.0])
    with pytest.raises(ValueError, match="missing"):
        binMeans([1.0, 2.0], [1.0, 2.0], [0.0, np.nan])
    integer = binMeans(np.array([1, 2, 3], dtype=np.int32), [1.0, 2.0, 3.0], [0.5, 3.5], right=False)
    assert integer.tolist() == [2.0]


def test_bin_means_matches_r():
    script = r"""
library(matrixStats)
fmt <- function(v) ifelse(is.na(v), "NA", sprintf("%.17g", v))
emit <- function(tag, expr) {
  val <- tryCatch(expr, error = function(e) NULL)
  if (is.null(val)) {
    cat(tag, "ERR", "\n", sep = "\t")
    return()
  }
  cat(tag, paste(fmt(val), collapse = " "), paste(attr(val, "count"), collapse = " "), "\n", sep = "\t")
}
y <- c(10, 20, 30)
x <- c(1, 1, 2)
emit("break_t", binMeans(y, x = x, bx = c(0, 1, 2), right = TRUE))
emit("break_f", binMeans(y, x = x, bx = c(0, 1, 2), right = FALSE))
emit("na_t", binMeans(c(1, NA, 3, 4), x = 1:4, bx = c(0.5, 2.5, 4.5), na.rm = TRUE, right = FALSE))
emit("na_f", binMeans(c(1, NA, 3, 4), x = 1:4, bx = c(0.5, 2.5, 4.5), na.rm = FALSE, right = FALSE))
emit("log", binMeans(c(TRUE, FALSE, TRUE), x = 1:3, bx = c(0.5, 2.5, 3.5), right = FALSE))
emit("idx", binMeans(c(1, 4, 2, 8, 3, 5), x = 1:6, idxs = c(3, 5, 1), bx = c(0, 3, 7), right = TRUE))
emit("empty", binMeans(c(1, 2), x = c(6, 7), bx = c(0, 5, 10), right = FALSE))
set.seed(1)
xr <- c(runif(2000, 0, 10), 5)
yr <- c(runif(2000, 0, 10), 1)
emit("rand_t", binMeans(yr, x = xr, bx = 0:10, right = TRUE, na.rm = TRUE))
emit("rand_f", binMeans(yr, x = xr, bx = 0:10, right = FALSE, na.rm = TRUE))
cat("X\t")
cat(sprintf("%.17g", xr), sep = " ")
cat("\nY\t")
cat(sprintf("%.17g", yr), sep = " ")
cat("\n")
"""
    rows = _r_rows(script)
    y = np.array([10.0, 20.0, 30.0])
    x = np.array([1.0, 1.0, 2.0])
    _assert_means(binMeans(y, x, [0, 1, 2], right=True), rows["break_t"])
    _assert_means(binMeans(y, x, [0, 1, 2], right=False), rows["break_f"])
    _assert_means(
        binMeans([1.0, np.nan, 3.0, 4.0], [1, 2, 3, 4], [0.5, 2.5, 4.5], na_rm=True, right=False),
        rows["na_t"],
    )
    _assert_means(
        binMeans([1.0, np.nan, 3.0, 4.0], [1, 2, 3, 4], [0.5, 2.5, 4.5], na_rm=False, right=False),
        rows["na_f"],
    )
    _assert_means(binMeans([True, False, True], [1, 2, 3], [0.5, 2.5, 3.5], right=False), rows["log"])
    _assert_means(
        binMeans([1, 4, 2, 8, 3, 5], [1, 2, 3, 4, 5, 6], [0, 3, 7], idxs=[3, 5, 1], right=True),
        rows["idx"],
    )
    _assert_means(binMeans([1.0, 2.0], [6.0, 7.0], [0, 5, 10], right=False), rows["empty"])
    random_x = np.fromstring(rows["X"][0], sep=" ")
    random_y = np.fromstring(rows["Y"][0], sep=" ")
    _assert_means(binMeans(random_y, random_x, np.arange(11), right=True), rows["rand_t"])
    _assert_means(binMeans(random_y, random_x, np.arange(11), right=False), rows["rand_f"])


def _assert_means(actual, row):
    means = [_nan(item) for item in row[0].split()]
    counts = [int(item) for item in row[1].split()]
    got = np.asarray(actual, dtype=float)
    assert got.shape == (len(means),)
    for left, right in zip(got, means):
        if np.isnan(right):
            assert np.isnan(left)
        else:
            assert left == pytest.approx(right, abs=1e-8)
    assert actual.count.tolist() == counts


def _nan(text: str) -> float:
    if text == "NA":
        return np.nan
    return float(text)


def _r_rows(script: str) -> dict[str, list[str]]:
    result = subprocess.run(
        ["Rscript", "-"],
        input=script,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        pytest.skip(result.stderr.strip() or "Rscript failed")
    rows = {}
    for line in result.stdout.splitlines():
        if line.startswith("X\t"):
            rows["X"] = [line[2:]]
            continue
        if line.startswith("Y\t"):
            rows["Y"] = [line[2:]]
            continue
        parts = line.split("\t")
        rows[parts[0]] = parts[1:]
    return rows
