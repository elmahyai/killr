"""Checks for mean2, including missing values, indexes, refine, and R."""

from __future__ import annotations

import math
import shutil
import subprocess
import textwrap

import numpy as np
import pytest

from matrixstats.mean2 import mean2


def test_empty_mean_is_nan():
    assert math.isnan(mean2(np.array([], dtype=np.float64)))
    assert math.isnan(mean2(np.array([], dtype=np.int32)))
    assert math.isnan(mean2(np.arange(1, 6), idxs=np.array([], dtype=np.int32)))


def test_plain_means():
    assert mean2(np.arange(1, 11, dtype=np.int32)) == 5.5
    assert mean2(np.array([1.0, 2.0, 3.0])) == 2.0
    assert mean2(np.array([True, False, True])) == pytest.approx(2.0 / 3.0)


def test_missing_values_and_na_rm():
    assert math.isnan(mean2(np.array([1.0, np.nan, 3.0])))
    assert mean2(np.array([1.0, np.nan, 3.0]), na_rm=True) == 2.0
    assert math.isnan(mean2([1, None, 3]))
    assert mean2([1, None, 3], na_rm=True) == 2.0
    assert math.isnan(mean2([True, None, False]))
    assert mean2([True, None, True], na_rm=True) == 1.0


def test_indexes_and_refine():
    x = np.arange(1, 7, dtype=np.float64)
    assert mean2(x, idxs=[3, 5, 1]) == 3.0
    assert mean2(x, idxs=[-4, 0, 0, -3, -1]) == pytest.approx((2 + 5 + 6) / 3)
    assert math.isnan(mean2(x, idxs=[-1, -2, -3, -4, -5, -6]))
    assert math.isnan(mean2(np.array([1e16, 1.0, -1e16]), refine=True)) is False
    assert mean2(np.array([1e16, 1.0, -1e16]), refine=True) == 0.0
    assert mean2(np.array([1e16, 1.0, -1e16]), refine=False) == 0.0
    with pytest.raises(ValueError, match="only 0's may be mixed"):
        mean2(x, idxs=[1, -1])
    with pytest.raises(ValueError, match="not logical"):
        mean2(x, refine=1)


def test_matches_r():
    if shutil.which("Rscript") is None:
        pytest.skip("Rscript is unavailable")
    script = textwrap.dedent(
        r"""
        library(matrixStats)
        options(warn = 1)
        emit <- function(name, expr) {
          value <- tryCatch(expr, error = function(e) structure(conditionMessage(e), class = "err"))
          if (inherits(value, "err")) {
            cat(name, "error", "\n", sep = "\t")
          } else if (is.nan(value)) {
            cat(name, "nan", "\n", sep = "\t")
          } else if (is.na(value)) {
            cat(name, "na", "\n", sep = "\t")
          } else if (is.infinite(value) && value > 0) {
            cat(name, "inf", "\n", sep = "\t")
          } else if (is.infinite(value) && value < 0) {
            cat(name, "ninf", "\n", sep = "\t")
          } else {
            cat(name, "float", sprintf("%.17g", value), "\n", sep = "\t")
          }
        }
        x <- 1:6
        emit("all_int", mean2(x))
        emit("subset", mean2(x, idxs = c(3L, 5L, 1L)))
        emit("neg", mean2(x, idxs = c(-4L, 0L, 0L, -3L, -1L)))
        emit("empty", mean2(double(0)))
        emit("empty_int", mean2(integer(0)))
        emit("empty_idx", mean2(1:5, idxs = integer(0)))
        emit("na", mean2(c(1, NA, 3)))
        emit("na_rm", mean2(c(1, NA, 3), na.rm = TRUE))
        emit("int_na", mean2(c(1L, NA_integer_, 3L)))
        emit("int_na_rm", mean2(c(1L, NA_integer_, 3L), na.rm = TRUE))
        emit("lgl", mean2(c(TRUE, FALSE, TRUE)))
        emit("lgl_na_rm", mean2(c(TRUE, NA, TRUE), na.rm = TRUE))
        emit("oob", mean2(x, idxs = 4:9, na.rm = TRUE))
        emit("oob_na", suppressWarnings(mean2(x, idxs = 4:9)))
        emit("frac", mean2(1:5, idxs = c(1.2, 2.8)))
        emit("recycle", mean2(x, idxs = c(FALSE, TRUE)))
        emit("excl", mean2(1:3, idxs = -1:-3))
        emit("cancel_t", mean2(c(1e16, 1, -1e16), refine = TRUE))
        emit("cancel_f", mean2(c(1e16, 1, -1e16), refine = FALSE))
        emit("mix", mean2(x, idxs = c(1L, -1L)))
        emit("pos_inf", mean2(rep(Inf, 3)))
        emit("both_inf", mean2(rep(c(-Inf, Inf), 3)))
        set.seed(1)
        z <- rnorm(1000, mean = 1e8, sd = 1)
        writeBin(z, "/tmp/matrixstats-mean2-refine.bin")
        emit("refine_t", mean2(z, refine = TRUE))
        emit("refine_f", mean2(z, refine = FALSE))
        emit("refine_rm", mean2(c(z, NA), na.rm = TRUE, refine = TRUE))
        """
    )
    reference = _run_r(script)
    sample = np.fromfile("/tmp/matrixstats-mean2-refine.bin", dtype="<f8")
    x = np.arange(1, 7)
    got = {
        "all_int": mean2(x.astype(np.int32)),
        "subset": mean2(x, idxs=[3, 5, 1]),
        "neg": mean2(x, idxs=[-4, 0, 0, -3, -1]),
        "empty": mean2(np.array([], dtype=np.float64)),
        "empty_int": mean2(np.array([], dtype=np.int32)),
        "empty_idx": mean2(np.arange(1, 6), idxs=np.array([], dtype=np.int32)),
        "na": mean2(np.array([1.0, np.nan, 3.0])),
        "na_rm": mean2(np.array([1.0, np.nan, 3.0]), na_rm=True),
        "int_na": mean2([1, None, 3]),
        "int_na_rm": mean2([1, None, 3], na_rm=True),
        "lgl": mean2(np.array([True, False, True])),
        "lgl_na_rm": mean2([True, None, True], na_rm=True),
        "oob": mean2(x, idxs=list(range(4, 10)), na_rm=True),
        "oob_na": mean2(x, idxs=list(range(4, 10))),
        "frac": mean2(np.arange(1, 6, dtype=np.float64), idxs=[1.2, 2.8]),
        "recycle": mean2(x.astype(np.float64), idxs=[False, True]),
        "excl": mean2(np.arange(1, 4), idxs=[-1, -2, -3]),
        "cancel_t": mean2(np.array([1e16, 1.0, -1e16]), refine=True),
        "cancel_f": mean2(np.array([1e16, 1.0, -1e16]), refine=False),
        "mix": "error",
        "pos_inf": mean2(np.array([np.inf, np.inf, np.inf])),
        "both_inf": mean2(np.tile(np.array([-np.inf, np.inf]), 3)),
        "refine_t": mean2(sample, refine=True),
        "refine_f": mean2(sample, refine=False),
        "refine_rm": mean2(np.append(sample, np.nan), na_rm=True, refine=True),
    }
    try:
        mean2(x, idxs=[1, -1])
    except ValueError:
        got["mix"] = "error"
    for name, spec in reference.items():
        _assert_matches(name, got[name], spec)


def _assert_matches(name, got, spec):
    kind, payload = spec
    if kind == "error":
        assert got == "error", name
        return
    if kind in ("na", "nan"):
        assert isinstance(got, float) and math.isnan(got), name
        return
    if kind == "inf":
        assert math.isinf(got) and got > 0, name
        return
    if kind == "ninf":
        assert math.isinf(got) and got < 0, name
        return
    assert abs(float(got) - float(payload)) <= 1e-8, (name, got, payload)


def _run_r(script: str) -> dict[str, tuple[str, str]]:
    completed = subprocess.run(
        ["Rscript", "-e", script],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        pytest.skip(f"Rscript failed: {completed.stderr}")
    parsed = {}
    for line in completed.stdout.splitlines():
        if "\t" not in line:
            continue
        parts = line.split("\t")
        parsed[parts[0]] = (parts[1], parts[2] if len(parts) > 2 else "")
    if not parsed:
        pytest.skip(f"Rscript produced no cases: {completed.stdout}\n{completed.stderr}")
    return parsed
