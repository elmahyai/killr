"""Checks for signTabulate, including a comparison with matrixStats 1.5.0."""

from __future__ import annotations

import os
import shutil
import subprocess

import numpy as np
import pytest

from matrixstats.signtabulate import signTabulate

NA_INTEGER = -2147483648


def test_double_counts_include_infinities_in_the_sign_bins():
    counts = signTabulate(np.array([-2.0, -np.inf, -0.0, 0.0, 1.0, np.inf, np.nan, np.nan]))
    assert counts.ndim == 1
    assert counts.dtype == np.int64
    assert counts.tolist() == [2, 2, 2, 2, 1, 1]


def test_integer_vector_has_no_infinity_counts():
    counts = signTabulate(np.array([-2, -1, 0, 1, NA_INTEGER, 5], dtype=np.int32))
    assert counts.shape == (4,)
    assert counts.tolist() == [2, 1, 2, 1]
    assert signTabulate([1, None, -2, 0]).tolist() == [1, 1, 1, 1]


def test_empty_and_subset():
    assert signTabulate(np.array([], dtype=np.float64)).tolist() == [0, 0, 0, 0, 0, 0]
    assert signTabulate(np.array([], dtype=np.int32)).tolist() == [0, 0, 0, 0]
    values = np.array([-5.0, 0.0, 4.0, np.nan, 8.0])
    assert signTabulate(values, idxs=[1, 1, 0, 3]).tolist() == [2, 0, 1, 0, 0, 0]
    assert signTabulate(values, idxs=[-1, 0]).tolist() == [0, 1, 2, 1, 0, 0]


def test_logical_x_is_rejected():
    with pytest.raises(ValueError, match="cannot be logical"):
        signTabulate(np.array([True, False]))
    with pytest.raises(ValueError, match="only 0's may be mixed with negative subscripts"):
        signTabulate(np.array([1.0, 2.0, 3.0]), idxs=[1, -1])


def test_matches_r_matrixstats():
    if shutil.which("Rscript") is None:
        pytest.skip("Rscript is unavailable")
    script = r"""
library(matrixStats)
emit <- function(name, expr) {
  val <- tryCatch(expr, error = function(e) paste0("ERR ", conditionMessage(e)))
  if (is.numeric(val)) val <- paste(sprintf("%.0f", val), collapse = " ")
  cat(name, "\t", val, "\n", sep = "")
}
emit("dbl", signTabulate(c(-2, -Inf, -0, 0, 1, Inf, NA, NaN)))
emit("int", signTabulate(c(-2L, -1L, 0L, 1L, NA_integer_, 5L)))
emit("int_names", paste(names(signTabulate(c(-1L, 0L, 1L))), collapse = " "))
emit("dbl_names", paste(names(signTabulate(c(-1, 0, Inf))), collapse = " "))
emit("empty_d", signTabulate(numeric(0)))
emit("empty_i", signTabulate(integer(0)))
emit("empty_idx", signTabulate(numeric(0), idxs = 1))
emit("dup", signTabulate(c(-5, 0, 4, NA, 8), idxs = c(1, 1, 0, 3)))
emit("neg", signTabulate(c(-5, 0, 4, NA, 8), idxs = c(-1, 0)))
emit("oob", signTabulate(c(-1, 0, 1), idxs = c(1, 9)))
emit("naidx", signTabulate(c(-1, 0, 1), idxs = c(NA_real_, 2)))
emit("lgl", signTabulate(c(-1, 0, 1, NA), idxs = c(TRUE, FALSE)))
emit("lgl_na", signTabulate(1:3, idxs = NA))
emit("frac", signTabulate(c(10, NA, 30), idxs = 2.9))
emit("frac_oob", signTabulate(c(1, 2, 3), idxs = 3.2))
emit("half", signTabulate(c(1, NA, 3), idxs = 0.5))
emit("long", signTabulate(1:2, idxs = c(FALSE, FALSE, TRUE)))
emit("none", signTabulate(c(-1L, 0L, 2L)))
emit("mat", signTabulate(matrix(c(-1, 0, 1, NA), nrow = 2)))
emit("int_big", signTabulate(c(-2147483647L, 2147483647L, NA_integer_)))
emit("logical", signTabulate(c(TRUE, FALSE)))
emit("mix", signTabulate(1:3, idxs = c(1L, -1L)))
set.seed(1)
x <- rnorm(100000)
x[c(1, 10, 100, 1000, 10000)] <- 0
x[c(2, 20, 200)] <- NA
x[3] <- Inf
x[4] <- -Inf
x[5] <- NaN
path <- "/tmp/signTabulate-timing.bin"
writeBin(x, path)
emit("timed", signTabulate(x))
emit("int_timed", signTabulate(c(-2L, 0L, 1L, NA_integer_, 4L, -7L)))
cat("PATH\t", path, "\n", sep = "")
"""
    completed = subprocess.run(
        ["Rscript", "-e", script],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        pytest.skip(f"matrixStats is unavailable: {completed.stderr}")
    rows = {}
    for line in completed.stdout.splitlines():
        name, value = line.split("\t", 1)
        rows[name] = value

    def counts(value, idxs=None):
        return signTabulate(value, idxs=idxs).tolist()

    assert counts(np.array([-2.0, -np.inf, -0.0, 0.0, 1.0, np.inf, np.nan, np.nan])) == _ints(rows["dbl"])
    assert counts(np.array([-2, -1, 0, 1, NA_INTEGER, 5], dtype=np.int32)) == _ints(rows["int"])
    assert rows["int_names"].split() == ["-1", "0", "+1", "NA"]
    assert rows["dbl_names"].split() == ["-1", "0", "+1", "NA", "-Inf", "+Inf"]
    assert len(_ints(rows["int"])) == 4
    assert len(_ints(rows["dbl"])) == 6
    assert counts(np.array([], dtype=np.float64)) == _ints(rows["empty_d"])
    assert counts(np.array([], dtype=np.int32)) == _ints(rows["empty_i"])
    assert counts(np.array([], dtype=np.float64), idxs=1) == _ints(rows["empty_idx"])
    values = np.array([-5.0, 0.0, 4.0, np.nan, 8.0])
    assert counts(values, idxs=[1, 1, 0, 3]) == _ints(rows["dup"])
    assert counts(values, idxs=[-1, 0]) == _ints(rows["neg"])
    assert counts(np.array([-1.0, 0.0, 1.0]), idxs=[1, 9]) == _ints(rows["oob"])
    assert counts(np.array([-1.0, 0.0, 1.0]), idxs=[np.nan, 2]) == _ints(rows["naidx"])
    assert counts(np.array([-1.0, 0.0, 1.0, np.nan]), idxs=[True, False]) == _ints(rows["lgl"])
    assert counts(np.array([1, 2, 3], dtype=np.int32), idxs=[None]) == _ints(rows["lgl_na"])
    assert counts(np.array([10.0, np.nan, 30.0]), idxs=2.9) == _ints(rows["frac"])
    assert counts(np.array([1.0, 2.0, 3.0]), idxs=3.2) == _ints(rows["frac_oob"])
    assert counts(np.array([1.0, np.nan, 3.0]), idxs=0.5) == _ints(rows["half"])
    assert counts(np.array([1, 2], dtype=np.int32), idxs=[False, False, True]) == _ints(rows["long"])
    assert counts(np.array([-1, 0, 2], dtype=np.int32)) == _ints(rows["none"])
    matrix = np.array([[-1.0, 1.0], [0.0, np.nan]])
    assert counts(matrix) == _ints(rows["mat"])
    assert counts(np.array([-2147483647, 2147483647, NA_INTEGER], dtype=np.int32)) == _ints(rows["int_big"])
    assert rows["logical"].startswith("ERR")
    assert rows["mix"].startswith("ERR")
    with pytest.raises(ValueError):
        signTabulate(np.array([1, 2, 3], dtype=np.int32), idxs=[1, -1])
    path = rows["PATH"].strip()
    timed = np.fromfile(path, dtype=np.float64)
    os.remove(path)
    assert counts(timed) == _ints(rows["timed"])
    assert len(_ints(rows["timed"])) == 6
    assert counts(np.array([-2, 0, 1, NA_INTEGER, 4, -7], dtype=np.int32)) == _ints(rows["int_timed"])
    assert len(_ints(rows["int_timed"])) == 4


def _ints(text):
    return [int(part) for part in text.split()]
