"""Checks for sum2, including missing values, indexes, and R."""

from __future__ import annotations

import math
import shutil
import subprocess
import textwrap
import warnings

import numpy as np
import pytest

from matrixstats.sum2 import sum2


def test_empty_sums_are_zero():
    assert sum2(np.array([], dtype=np.float64)) == 0.0
    assert type(sum2(np.array([], dtype=np.float64))) is float
    assert sum2(np.array([], dtype=np.int32)) == 0
    assert type(sum2(np.array([], dtype=np.int32))) is int
    assert sum2(np.arange(1, 11), idxs=np.array([], dtype=np.int32)) == 0


def test_double_and_integer_totals():
    assert sum2(np.array([1.0, 2.0, 3.0])) == 6.0
    assert sum2(np.array([1, 2, 3], dtype=np.int32)) == 6
    assert type(sum2(np.array([1, 2, 3], dtype=np.int32))) is int


def test_logical_defaults_to_an_integer_sum():
    total = sum2(np.array([True, False, True]))
    assert total == 2
    assert type(total) is int
    assert sum2(np.array([True, False, True]), mode="double") == 2.0
    assert sum2(np.array([True, False, True]), mode="logical") == 2


def test_missing_values_and_na_rm():
    assert math.isnan(sum2(np.array([1.0, np.nan, 3.0])))
    assert sum2(np.array([1.0, np.nan, 3.0]), na_rm=True) == 4.0
    assert sum2([1, None, 3]) is None
    assert sum2([1, None, 3], na_rm=True) == 4
    assert sum2([True, None, False]) is None
    assert sum2([True, None, True], na_rm=True) == 2


def test_one_based_subset_zeros_negatives_and_out_of_range():
    x = np.arange(1, 7)
    assert sum2(x, idxs=[3, 5, 1]) == 9
    assert sum2(x, idxs=[-4, 0, 0, -3, -1, -3, -1]) == 13
    assert sum2(x, idxs=[-5, 0, -3, -1, -9]) == 12
    assert sum2(x, idxs=0) == 0
    assert sum2(x, idxs=[4, 5, 6, 7, 8, 9]) is None
    assert sum2(x, idxs=[4, 5, 6, 7, 8, 9], na_rm=True) == 15
    assert sum2(x, idxs=[1.9, 2.1]) == 3
    assert sum2(x, idxs=0.5) == 1
    assert sum2(np.arange(1, 6), idxs=[-1.9, -0.5]) == 14
    assert sum2(x, idxs=[False, True]) == 12
    assert sum2(x, idxs=True) == 21
    assert sum2(x, idxs=False) == 0
    assert sum2(x, idxs=[False, True, None]) is None
    with pytest.raises(ValueError, match="only 0's may be mixed"):
        sum2(x, idxs=[-4, 0, 1])


def test_integer_overflow_and_double_mode():
    values = np.array([np.iinfo(np.int32).max, 1, -np.iinfo(np.int32).max], dtype=np.int32)
    with pytest.warns(UserWarning, match="Integer overflow"):
        assert sum2(values[:2]) is None
    assert sum2(values[:2], mode="double") == 2147483648.0
    assert sum2(values) == 1
    with pytest.warns(UserWarning, match='typeof\\(x\\) == "double"'):
        assert sum2(np.array([1.0, 2.0, 3.1]), mode="integer") == 6


def test_argument_checks():
    with pytest.raises(ValueError, match="not numeric or logical"):
        sum2(["a", "b"])
    with pytest.raises(ValueError, match="not logical"):
        sum2([1.0, 2.0], na_rm=1)
    with pytest.raises(ValueError, match="Unknown value of argument 'mode'"):
        sum2([1.0, 2.0], mode="complex")
    with pytest.raises(ValueError, match="idxs can only be"):
        sum2([1.0, 2.0], idxs=["a"])


def test_infinities():
    assert math.isinf(sum2(np.array([np.inf, np.inf])))
    assert sum2(np.array([np.inf, np.inf])) > 0
    assert math.isnan(sum2(np.array([np.inf, -np.inf])))
    assert math.isinf(sum2(np.array([np.nan, np.inf, 3.14]), na_rm=True))


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
          } else if (is.integer(value)) {
            if (is.na(value)) cat(name, "na_int", "\n", sep = "\t")
            else cat(name, "int", format(value, scientific = FALSE), "\n", sep = "\t")
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
        emit("all_int", sum2(x))
        emit("subset", sum2(x, idxs = c(3L, 5L, 1L)))
        emit("neg", sum2(x, idxs = c(-4L, 0L, 0L, -3L, -1L, -3L, -1L)))
        emit("neg_oob", sum2(x, idxs = c(-5L, 0L, -3L, -1L, -9L)))
        emit("zero", sum2(x, idxs = 0L))
        emit("oob", suppressWarnings(sum2(x, idxs = 4:9)))
        emit("oob_rm", sum2(x, idxs = 4:9, na.rm = TRUE))
        emit("frac", sum2(x, idxs = c(1.9, 2.1)))
        emit("half", sum2(x, idxs = 0.5))
        emit("neg_frac", sum2(1:5, idxs = c(-1.9, -0.5)))
        emit("recycle", sum2(x, idxs = c(FALSE, TRUE)))
        emit("lgl_true", sum2(x, idxs = TRUE))
        emit("lgl_false", sum2(x, idxs = FALSE))
        emit("lgl_na_idx", sum2(x, idxs = c(FALSE, TRUE, NA)))
        emit("lgl_long", sum2(x, idxs = c(FALSE, TRUE, FALSE, TRUE, TRUE, TRUE, FALSE, TRUE), na.rm = TRUE))
        emit("mix", sum2(x, idxs = c(-4L, 0L, 1L)))
        emit("dbl", sum2(c(1, 2, 3)))
        emit("na", sum2(c(1, NA, 3)))
        emit("na_rm", sum2(c(1, NA, 3), na.rm = TRUE))
        emit("int_na", sum2(c(1L, NA_integer_, 3L)))
        emit("int_na_rm", sum2(c(1L, NA_integer_, 3L), na.rm = TRUE))
        emit("lgl", sum2(c(TRUE, FALSE, TRUE)))
        emit("lgl_na", sum2(c(TRUE, NA, FALSE)))
        emit("lgl_na_rm", sum2(c(TRUE, NA, TRUE), na.rm = TRUE))
        y <- c(.Machine$integer.max, 1L, -.Machine$integer.max)
        emit("overflow", suppressWarnings(sum2(y[1:2])))
        emit("overflow_dbl", suppressWarnings(sum2(y[1:2], mode = "double")))
        emit("overflow_total", sum2(y))
        emit("mode_int", suppressWarnings(sum2(c(1, 2, 3.1), mode = "integer")))
        emit("empty_dbl", sum2(double(0)))
        emit("empty_int", sum2(integer(0)))
        emit("empty_idx", sum2(1:10, idxs = integer(0)))
        emit("pos_inf", sum2(c(Inf, Inf)))
        emit("neg_inf", sum2(c(-Inf, -Inf)))
        emit("both_inf", sum2(c(Inf, -Inf)))
        emit("nan_rm", sum2(c(NaN, Inf, 3.14), na.rm = TRUE))
        emit("na_idx", sum2(1:5, idxs = c(NA_real_, 0, 2)))
        emit("na_idx_rm", sum2(1:5, idxs = c(NA_real_, 0, 2), na.rm = TRUE))
        emit("repeats", sum2(1:5, idxs = c(1L, 1L, 2L)))
        emit("excl", sum2(1:3, idxs = -1:-3))
        emit("dbl_idx", sum2(1:10, idxs = as.double(1:5)))
        """
    )
    reference = _run_r(script)
    x = np.arange(1, 7)
    got = {
        "all_int": sum2(x.astype(np.int32)),
        "subset": sum2(x, idxs=[3, 5, 1]),
        "neg": sum2(x, idxs=[-4, 0, 0, -3, -1, -3, -1]),
        "neg_oob": sum2(x, idxs=[-5, 0, -3, -1, -9]),
        "zero": sum2(x, idxs=0),
        "oob": sum2(x, idxs=list(range(4, 10))),
        "oob_rm": sum2(x, idxs=list(range(4, 10)), na_rm=True),
        "frac": sum2(x, idxs=[1.9, 2.1]),
        "half": sum2(x, idxs=0.5),
        "neg_frac": sum2(np.arange(1, 6), idxs=[-1.9, -0.5]),
        "recycle": sum2(x, idxs=[False, True]),
        "lgl_true": sum2(x, idxs=True),
        "lgl_false": sum2(x, idxs=False),
        "lgl_na_idx": sum2(x, idxs=[False, True, None]),
        "lgl_long": sum2(
            x,
            idxs=[False, True, False, True, True, True, False, True],
            na_rm=True,
        ),
        "mix": "error",
        "dbl": sum2(np.array([1.0, 2.0, 3.0])),
        "na": sum2(np.array([1.0, np.nan, 3.0])),
        "na_rm": sum2(np.array([1.0, np.nan, 3.0]), na_rm=True),
        "int_na": sum2([1, None, 3]),
        "int_na_rm": sum2([1, None, 3], na_rm=True),
        "lgl": sum2(np.array([True, False, True])),
        "lgl_na": sum2([True, None, False]),
        "lgl_na_rm": sum2([True, None, True], na_rm=True),
        "overflow": None,
        "overflow_dbl": None,
        "overflow_total": sum2(
            np.array(
                [np.iinfo(np.int32).max, 1, -np.iinfo(np.int32).max],
                dtype=np.int32,
            )
        ),
        "mode_int": None,
        "empty_dbl": sum2(np.array([], dtype=np.float64)),
        "empty_int": sum2(np.array([], dtype=np.int32)),
        "empty_idx": sum2(np.arange(1, 11), idxs=np.array([], dtype=np.int32)),
        "pos_inf": sum2(np.array([np.inf, np.inf])),
        "neg_inf": sum2(np.array([-np.inf, -np.inf])),
        "both_inf": sum2(np.array([np.inf, -np.inf])),
        "nan_rm": sum2(np.array([np.nan, np.inf, 3.14]), na_rm=True),
        "na_idx": sum2(np.arange(1, 6), idxs=[np.nan, 0.0, 2.0]),
        "na_idx_rm": sum2(np.arange(1, 6), idxs=[np.nan, 0.0, 2.0], na_rm=True),
        "repeats": sum2(np.arange(1, 6), idxs=[1, 1, 2]),
        "excl": sum2(np.arange(1, 4), idxs=[-1, -2, -3]),
        "dbl_idx": sum2(np.arange(1, 11), idxs=np.array([1, 2, 3, 4, 5], dtype=np.float64)),
    }
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        got["oob"] = sum2(x, idxs=list(range(4, 10)))
        got["overflow"] = sum2(np.array([np.iinfo(np.int32).max, 1], dtype=np.int32))
        got["overflow_dbl"] = sum2(
            np.array([np.iinfo(np.int32).max, 1], dtype=np.int32), mode="double"
        )
        got["mode_int"] = sum2(np.array([1.0, 2.0, 3.1]), mode="integer")
    try:
        sum2(x, idxs=[-4, 0, 1])
    except ValueError:
        got["mix"] = "error"
    for name, spec in reference.items():
        _assert_matches(name, got[name], spec)


def _assert_matches(name, got, spec):
    kind, payload = spec
    if kind == "error":
        assert got == "error", name
        return
    if kind == "na_int":
        assert got is None, name
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
    if kind == "int":
        assert type(got) is int, name
        assert got == int(payload), name
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
