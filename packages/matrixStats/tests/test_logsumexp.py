"""Checks for logSumExp, including a comparison with matrixStats 1.5.0."""

from __future__ import annotations

import math
import shutil
import subprocess
import textwrap

import numpy as np
import pytest

from matrixstats.logsumexp import logSumExp

X = np.array(
    [
        -2.8138960422948,
        -1.53451320435852,
        0.874240360222757,
        4.89849347993731,
        -3.57981682755053,
        4.78067621961236,
    ]
)


def test_max_subtraction_avoids_overflow_and_underflow():
    large = logSumExp(np.array([1000.01, 1000.02]))
    assert large == pytest.approx(1000.7081596805078, abs=1e-8)
    small = logSumExp(np.array([-1000.01, -1000.02]))
    assert small == pytest.approx(-999.32184031949214, abs=1e-8)


def test_empty_and_all_missing():
    assert logSumExp(np.array([], dtype=np.float64)) == -math.inf
    assert logSumExp([]) == -math.inf
    assert logSumExp(np.array([np.nan]), na_rm=True) == -math.inf
    assert math.isnan(logSumExp(np.array([np.nan]), na_rm=False))
    assert logSumExp(np.array([np.nan, np.nan]), na_rm=True) == -math.inf
    assert math.isnan(logSumExp(np.array([np.nan, np.nan]), na_rm=False))
    assert logSumExp(np.array([1.0])) == 1.0


def test_infinities_and_leading_missing_value():
    assert logSumExp(np.array([1.0, 2.0, np.inf])) == math.inf
    assert logSumExp(np.array([-np.inf, -np.inf])) == -math.inf
    assert logSumExp(np.array([-np.inf, 5.0, -np.inf])) == 5.0
    assert math.isnan(logSumExp(np.array([np.nan, 1.0]), na_rm=False))
    assert logSumExp(np.array([np.nan, 1.0]), na_rm=True) == 1.0
    assert logSumExp(np.array([1.0, np.nan, 3.0]), na_rm=True) == pytest.approx(
        3.1269280110429727, abs=1e-8
    )


def test_fractional_index_follows_the_c_cast():
    # 0.5 truncates to a zero subscript in base R, which drops it.
    # matrixStats converts 0.5 - 1 toward zero and keeps the first element.
    assert logSumExp(np.array([9.0, 8.0, 7.0]), idxs=0.5) == 9.0


def test_mixed_signs_use_the_r_message():
    with pytest.raises(ValueError, match="only 0's may be mixed with negative subscripts"):
        logSumExp(X, idxs=np.array([1, -1]))


def test_none_means_every_element_and_column_major_matrix():
    whole = logSumExp(X)
    assert whole == pytest.approx(logSumExp(X, idxs=None), abs=1e-8)
    matrix = np.array([[1.0, 3.0], [2.0, 4.0]])
    flat = logSumExp(np.array([1.0, 2.0, 3.0, 4.0]))
    assert logSumExp(matrix) == pytest.approx(flat, abs=1e-8)


def test_matches_matrixstats():
    if shutil.which("Rscript") is None:
        pytest.skip("Rscript is unavailable")
    expected = _r_log_sum_exp()
    for name, actual in _python_cases().items():
        _assert_match(name, actual, expected[name])


def _raised(call):
    try:
        return call()
    except ValueError as exc:
        return "ERR " + str(exc)


def _python_cases():
    view = X[::-1]
    int32_na = np.array([np.iinfo(np.int32).min, 2], dtype=np.int32)
    return {
        "empty": logSumExp(np.array([], dtype=np.float64)),
        "single": logSumExp(np.array([1.0])),
        "na_keep": logSumExp(np.array([1.0, np.nan, 3.0]), na_rm=False),
        "na_drop": logSumExp(np.array([1.0, np.nan, 3.0]), na_rm=True),
        "all_na_drop": logSumExp(np.array([np.nan, np.nan]), na_rm=True),
        "pos_inf": logSumExp(np.array([1.0, 2.0, np.inf])),
        "neg_inf": logSumExp(np.array([-np.inf, 5.0, -np.inf])),
        "large": logSumExp(np.array([1000.01, 1000.02])),
        "whole": logSumExp(X),
        "pos": logSumExp(X, idxs=np.array([3, 5, 1])),
        "pos_dup": logSumExp(X, idxs=[3, 0, 0, 5, 1, 5, 5]),
        "neg": logSumExp(X, idxs=[-4, 0, 0, -3, -1, -3, -1]),
        "oob_keep": logSumExp(X, idxs=np.arange(4, 10), na_rm=False),
        "oob_drop": logSumExp(X, idxs=np.arange(4, 10), na_rm=True),
        "neg_oob": logSumExp(X, idxs=[-5, 0, -3, -1, -9]),
        "neg_all": logSumExp(X, idxs=[-1, -2, -3, -4, -5, -6]),
        "one": logSumExp(X, idxs=4),
        "neg_one": logSumExp(X, idxs=-4),
        "zero": logSumExp(X, idxs=0),
        "empty_idxs": logSumExp(X, idxs=np.array([], dtype=np.int64)),
        "na_index_drop": logSumExp(X, idxs=np.array([np.nan, 0.0, 2.0]), na_rm=True),
        "na_index_keep": logSumExp(X, idxs=np.array([np.nan, 0.0, 2.0]), na_rm=False),
        "inf_index_drop": logSumExp(X, idxs=np.array([np.nan, 0.0, 2.0, np.inf]), na_rm=True),
        "frac": logSumExp(X, idxs=np.array([1.9, 2.1])),
        "half": logSumExp(X, idxs=0.5),
        "neg_frac": logSumExp(X, idxs=-1.9),
        "lgl_true": logSumExp(X, idxs=True),
        "lgl_false": logSumExp(X, idxs=False),
        "lgl_na": logSumExp(X, idxs=[None], na_rm=True),
        "lgl_full": logSumExp(X, idxs=np.array([False, True, False, True, True, False])),
        "lgl_long_drop": logSumExp(
            X,
            idxs=np.array([False, True, False, True, True, True, False, True]),
            na_rm=True,
        ),
        "lgl_short": logSumExp(X, idxs=np.array([False, True])),
        "lgl_short_na": logSumExp(X, idxs=[False, True, None], na_rm=True),
        "int_na": logSumExp(np.array([10.0, 20.0, 30.0]), idxs=int32_na, na_rm=True),
        "matrix": logSumExp(np.array([[1.0, 3.0], [2.0, 4.0]])),
        "reversed_view": logSumExp(view),
        "mix": _raised(lambda: logSumExp(X, idxs=np.array([1, -1]))),
    }


def _r_log_sum_exp():
    script = textwrap.dedent(
        """
        library(matrixStats)
        x <- c(-2.8138960422948, -1.53451320435852, 0.874240360222757,
               4.89849347993731, -3.57981682755053, 4.78067621961236)
        say <- function(name, expr) {
          val <- tryCatch(expr, error = function(e) paste0("ERR ", conditionMessage(e)))
          if (is.character(val)) {
            cat(name, "\\t", val, "\\n", sep = "")
          } else if (is.na(val)) {
            cat(name, "\\tNA\\n", sep = "")
          } else {
            cat(name, "\\t", sprintf("%.17g", val), "\\n", sep = "")
          }
        }
        say("empty", logSumExp(numeric(0)))
        say("single", logSumExp(1))
        say("na_keep", logSumExp(c(1, NA_real_, 3), na.rm = FALSE))
        say("na_drop", logSumExp(c(1, NA_real_, 3), na.rm = TRUE))
        say("all_na_drop", logSumExp(c(NA_real_, NA_real_), na.rm = TRUE))
        say("pos_inf", logSumExp(c(1, 2, Inf)))
        say("neg_inf", logSumExp(c(-Inf, 5, -Inf)))
        say("large", logSumExp(c(1000.01, 1000.02)))
        say("whole", logSumExp(x))
        say("pos", logSumExp(x, idxs = as.integer(c(3, 5, 1))))
        say("pos_dup", logSumExp(x, idxs = as.integer(c(3, 0, 0, 5, 1, 5, 5))))
        say("neg", logSumExp(x, idxs = as.integer(c(-4, 0, 0, -3, -1, -3, -1))))
        say("oob_keep", logSumExp(x, idxs = 4:9, na.rm = FALSE))
        say("oob_drop", logSumExp(x, idxs = 4:9, na.rm = TRUE))
        say("neg_oob", logSumExp(x, idxs = as.integer(c(-5, 0, -3, -1, -9))))
        say("neg_all", logSumExp(x, idxs = as.integer(-1:-6)))
        say("one", logSumExp(x, idxs = 4L))
        say("neg_one", logSumExp(x, idxs = -4L))
        say("zero", logSumExp(x, idxs = 0L))
        say("empty_idxs", logSumExp(x, idxs = integer(0)))
        say("na_index_drop", logSumExp(x, idxs = c(NA_real_, 0, 2), na.rm = TRUE))
        say("na_index_keep", logSumExp(x, idxs = c(NA_real_, 0, 2), na.rm = FALSE))
        say("inf_index_drop", logSumExp(x, idxs = c(NA_real_, 0, 2, Inf), na.rm = TRUE))
        say("frac", logSumExp(x, idxs = c(1.9, 2.1)))
        say("half", logSumExp(x, idxs = 0.5))
        say("neg_frac", logSumExp(x, idxs = -1.9))
        say("lgl_true", logSumExp(x, idxs = TRUE))
        say("lgl_false", logSumExp(x, idxs = FALSE))
        say("lgl_na", logSumExp(x, idxs = NA, na.rm = TRUE))
        say("lgl_full", logSumExp(x, idxs = c(FALSE, TRUE, FALSE, TRUE, TRUE, FALSE)))
        say("lgl_long_drop", logSumExp(x, idxs = c(FALSE, TRUE, FALSE, TRUE, TRUE, TRUE, FALSE, TRUE), na.rm = TRUE))
        say("lgl_short", logSumExp(x, idxs = c(FALSE, TRUE)))
        say("lgl_short_na", logSumExp(x, idxs = c(FALSE, TRUE, NA), na.rm = TRUE))
        say("int_na", logSumExp(c(10, 20, 30), idxs = c(NA_integer_, 2L), na.rm = TRUE))
        say("matrix", logSumExp(matrix(c(1, 2, 3, 4), nrow = 2)))
        say("reversed_view", logSumExp(rev(x)))
        say("mix", logSumExp(x, idxs = as.integer(c(1, -1))))
        """
    )
    completed = subprocess.run(
        ["Rscript", "-e", script],
        check=True,
        capture_output=True,
        text=True,
    )
    parsed = {}
    for line in completed.stdout.splitlines():
        if "\t" not in line:
            continue
        name, value = line.split("\t", 1)
        parsed[name] = value
    return parsed


def _assert_match(name, actual, expected):
    if expected.startswith("ERR"):
        assert actual == expected, name
        return
    if expected == "NA":
        assert isinstance(actual, float) and math.isnan(actual), name
        return
    assert actual == pytest.approx(float(expected), abs=1e-8), name
