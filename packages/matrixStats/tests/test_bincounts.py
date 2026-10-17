"""Checks for binCounts, including a comparison with matrixStats 1.5.0."""

from __future__ import annotations

import subprocess

import numpy as np
import pytest

from matrixstats.bincounts import binCounts


def test_break_lands_on_the_closed_side():
    sample = np.array([0.0, 1.0, 2.0, 5.0, 10.0])
    breaks = np.arange(11, dtype=float)
    assert binCounts(sample, breaks, right=True).tolist() == [1, 1, 0, 0, 1, 0, 0, 0, 0, 1]
    assert binCounts(sample, breaks, right=False).tolist() == [1, 1, 1, 0, 0, 1, 0, 0, 0, 0]


def test_right_defaults_to_true():
    sample = np.array([1.0, 2.0])
    breaks = np.array([1.0, 2.0, 3.0])
    assert binCounts(sample, breaks).tolist() == binCounts(sample, breaks, right=True).tolist()
    assert binCounts(sample, breaks).dtype == np.int32


def test_missing_x_is_dropped():
    counts = binCounts([1.0, np.nan, 2.0, np.nan, 3.0], [0.5, 1.5, 2.5, 3.5], right=False)
    assert counts.tolist() == [1, 1, 1]


def test_duplicate_breaks_and_points_outside_the_range():
    sample = np.arange(1, 11, dtype=float)
    breaks = np.repeat(sample, 2)
    assert binCounts(sample, breaks, right=False).tolist() == [i % 2 for i in range(19)]
    assert binCounts([1.0, 2.0, 3.0], [-9.0, 0.0]).tolist() == [0]
    assert binCounts([], [0.0, 1.0, 2.0]).tolist() == [0, 0]


def test_idxs_follow_r_rules():
    sample = np.arange(1, 7, dtype=float)
    breaks = np.array([0.0, 2.0, 4.0, 7.0])
    assert binCounts(sample, breaks, idxs=[3, 0, 0, 5, 1, 5, 5], right=False).tolist() == [1, 1, 3]
    assert binCounts(sample, breaks, idxs=[-4, 0, -3, -1], right=False).tolist() == binCounts(
        sample[[1, 4, 5]], breaks, right=False
    ).tolist()
    assert binCounts(sample, breaks, idxs=[False, True], right=True).tolist() == binCounts(
        sample[1::2], breaks, right=True
    ).tolist()
    with pytest.raises(ValueError, match="negative subscripts"):
        binCounts(sample, breaks, idxs=[1, -1])


def test_bx_errors():
    with pytest.raises(ValueError, match="infinite"):
        binCounts([1.0, 2.0], [1.0, np.inf])
    with pytest.raises(ValueError, match="missing"):
        binCounts([1.0, 2.0], [1.0, np.nan])
    with pytest.raises(ValueError, match="ordered"):
        binCounts([1.0, 2.0], [3.0, 1.0])
    with pytest.raises(ValueError, match="at least two"):
        binCounts([1.0, 2.0], [1.0])


def test_bin_counts_matches_r():
    script = r"""
library(matrixStats)
x <- c(-3, -1, 0, 2, 5, 8)
bx <- c(-6, 0, 3, 4, 10)
emit <- function(tag, expr) {
  val <- tryCatch(expr, error = function(e) "ERR")
  cat(tag, paste(val, collapse = " "), "\n", sep = "\t")
}
emit("all_f", binCounts(x, bx = bx, right = FALSE))
emit("all_t", binCounts(x, bx = bx, right = TRUE))
emit("pos", binCounts(x, idxs = c(3, 0, 0, 5, 1, 5, 5), bx = bx, right = FALSE))
emit("neg", binCounts(x, idxs = c(-4, 0, 0, -3, -1, -3, -1), bx = bx, right = TRUE))
emit("oob", binCounts(x, idxs = 4:9, bx = bx, right = FALSE))
emit("naidx", binCounts(x, idxs = c(NA_real_, 0, 2, Inf), bx = bx, right = TRUE))
emit("log", binCounts(x, idxs = c(FALSE, TRUE, NA), bx = bx, right = FALSE))
emit("long", binCounts(x, idxs = c(FALSE, TRUE, FALSE, TRUE, TRUE, TRUE, FALSE, TRUE), bx = bx, right = TRUE))
emit("empty", binCounts(x, idxs = integer(), bx = bx, right = FALSE))
emit("mix", binCounts(x, idxs = c(-Inf, -1), bx = bx))
emit("miss", binCounts(c(1, NA, 2, NaN, 3), bx = c(0.5, 1.5, 2.5, 3.5), right = FALSE))
emit("break_t", binCounts(c(0, 1, 2, 5, 10), bx = 0:10, right = TRUE))
emit("break_f", binCounts(c(0, 1, 2, 5, 10), bx = 0:10, right = FALSE))
set.seed(1)
xr <- c(runif(2000, 0, 10), 5)
emit("rand_t", binCounts(xr, bx = 0:10, right = TRUE))
emit("rand_f", binCounts(xr, bx = 0:10, right = FALSE))
cat("RAND\t")
cat(sprintf("%.17g", xr), sep = " ")
cat("\n")
"""
    rows = _r_rows(script)
    sample = np.array([-3.0, -1.0, 0.0, 2.0, 5.0, 8.0])
    breaks = np.array([-6.0, 0.0, 3.0, 4.0, 10.0])
    assert _counts(sample, breaks, right=False) == _ints(rows["all_f"])
    assert _counts(sample, breaks, right=True) == _ints(rows["all_t"])
    assert _counts(sample, breaks, idxs=[3, 0, 0, 5, 1, 5, 5], right=False) == _ints(rows["pos"])
    assert _counts(sample, breaks, idxs=[-4, 0, 0, -3, -1, -3, -1], right=True) == _ints(rows["neg"])
    assert _counts(sample, breaks, idxs=list(range(4, 10)), right=False) == _ints(rows["oob"])
    assert _counts(sample, breaks, idxs=[np.nan, 0, 2, np.inf], right=True) == _ints(rows["naidx"])
    assert _counts(sample, breaks, idxs=[False, True, None], right=False) == _ints(rows["log"])
    assert (
        _counts(
            sample,
            breaks,
            idxs=[False, True, False, True, True, True, False, True],
            right=True,
        )
        == _ints(rows["long"])
    )
    assert _counts(sample, breaks, idxs=[], right=False) == _ints(rows["empty"])
    assert rows["mix"] == ["ERR"]
    with pytest.raises(ValueError):
        binCounts(sample, breaks, idxs=[float("-inf"), -1])
    assert binCounts([1.0, np.nan, 2.0, np.nan, 3.0], [0.5, 1.5, 2.5, 3.5], right=False).tolist() == _ints(rows["miss"])
    assert binCounts([0, 1, 2, 5, 10], np.arange(11), right=True).tolist() == _ints(rows["break_t"])
    assert binCounts([0, 1, 2, 5, 10], np.arange(11), right=False).tolist() == _ints(rows["break_f"])
    random = np.fromstring(rows["RAND"][0], sep=" ")
    assert binCounts(random, np.arange(11), right=True).tolist() == _ints(rows["rand_t"])
    assert binCounts(random, np.arange(11), right=False).tolist() == _ints(rows["rand_f"])


def _counts(sample, breaks, idxs=None, right=False):
    return binCounts(sample, breaks, idxs=idxs, right=right).tolist()


def _ints(row: list[str]) -> list[int]:
    return [int(value) for value in row]


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
        tag, _, payload = line.partition("\t")
        if tag == "RAND":
            rows["RAND"] = [line[len("RAND") :]]
        else:
            rows[tag] = payload.split()
    return rows
