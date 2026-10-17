"""Checks for diff2, including a comparison with matrixStats 1.5.0."""

from __future__ import annotations

import shutil
import subprocess
import textwrap

import numpy as np
import pytest

from matrixstats.diff2 import diff2


def test_default_lag_and_differences_match_consecutive_gaps():
    values = diff2(np.arange(1, 11))
    assert values.dtype == np.float64
    assert values.shape == (9,)
    assert values.tolist() == [1.0] * 9


def test_lag_and_second_order():
    values = diff2(np.arange(1, 13), lag=3, differences=2)
    assert values.shape == (6,)
    assert values.tolist() == [0.0] * 6


def test_noninteger_lag_truncates_toward_zero():
    values = diff2(np.arange(1, 11), lag=1.9, differences=2.2)
    assert values.tolist() == [0.0] * 8


def test_missing_and_infinite_values():
    values = diff2(np.array([1.0, np.nan, 3.0, 4.0, np.nan, 8.0]))
    assert np.isnan(values[0]) and np.isnan(values[1])
    assert values[2] == 1.0
    assert np.isnan(values[3]) and np.isnan(values[4])

    specials = diff2(np.array([1.0, np.inf, 3.0, -np.inf, np.nan, 6.0]))
    assert np.isposinf(specials[0])
    assert np.isneginf(specials[1]) and np.isneginf(specials[2])
    assert np.isnan(specials[3]) and np.isnan(specials[4])


def test_none_selects_every_element():
    x = np.arange(1, 7, dtype=np.float64)
    assert diff2(x, idxs=None).tolist() == diff2(x).tolist()


def test_positive_negative_and_out_of_range_indexes():
    x = np.arange(1, 7, dtype=np.float64)
    assert diff2(x, idxs=[3, 0, 0, 5, 1, 5, 5]).tolist() == [2.0, -4.0, 4.0, 0.0]
    assert diff2(x, idxs=[-4, 0, 0, -3, -1, -3, -1]).tolist() == [3.0, 1.0]
    assert diff2(x, idxs=[-5, 0, -3, -1, -9]).tolist() == [2.0, 2.0]
    assert diff2(x, idxs=4).shape == (0,)
    assert diff2(x, idxs=-4).tolist() == [1.0, 1.0, 2.0, 1.0]
    assert diff2(x, idxs=0).shape == (0,)
    assert diff2(x, idxs=[]).shape == (0,)
    assert diff2(x, idxs=list(range(-1, -7, -1))).shape == (0,)

    out = diff2(x, idxs=list(range(4, 10)))
    assert out[0] == 1.0 and out[1] == 1.0
    assert np.all(np.isnan(out[2:]))

    missing = diff2(x, idxs=[np.nan, 0, 2, np.inf])
    assert missing.shape == (2,)
    assert np.all(np.isnan(missing))


def test_fractional_indexes_follow_diff2_not_base_subsetting():
    x = np.arange(1, 7, dtype=np.float64)
    assert diff2(x, idxs=[2.9, 1.1]).tolist() == [-1.0]
    assert diff2(x, idxs=[-2.9, -0.5]).tolist() == [2.0, 1.0, 1.0, 1.0]
    # 0.5 becomes the first element in the C cast, so the difference is 2 - 1.
    assert diff2(x, idxs=[0.5, 2]).tolist() == [1.0]
    assert np.isnan(diff2(x, idxs=[1, 6.1])[0])


def test_logical_indexes_recycle():
    x = np.arange(1, 7, dtype=np.float64)
    assert diff2(x, idxs=True).tolist() == [1.0] * 5
    assert diff2(x, idxs=False).shape == (0,)
    assert diff2(x, idxs=[False, True, False, True, True, False]).tolist() == [2.0, 1.0]
    assert diff2(x, idxs=[False, True]).tolist() == [2.0, 2.0]
    long = diff2(
        x, idxs=[False, True, False, True, True, True, False, True]
    )
    assert long[:3].tolist() == [2.0, 1.0, 1.0]
    assert np.isnan(long[3])
    recycled = diff2(x, idxs=[False, True, None])
    assert recycled.shape == (3,)
    assert np.all(np.isnan(recycled))
    single_na = diff2(np.arange(1, 5), idxs=[None])
    assert single_na.shape == (3,)
    assert np.all(np.isnan(single_na))


def test_use_names_does_not_change_values():
    x = np.arange(1, 6, dtype=np.float64)
    assert diff2(x, use_names=True).tolist() == diff2(x, use_names=False).tolist()


def test_argument_errors():
    x = np.arange(4, dtype=np.float64)
    with pytest.raises(ValueError, match="only 0's may be mixed with negative subscripts"):
        diff2(x, idxs=[1, -1])
    with pytest.raises(ValueError, match="only 0's may be mixed with negative subscripts"):
        diff2(x, idxs=[-np.inf, -1])
    with pytest.raises(ValueError, match="Argument 'lag' must be a positive integer"):
        diff2(x, lag=0)
    with pytest.raises(ValueError, match="Argument 'differences' must be a positive integer"):
        diff2(x, differences=-2)
    with pytest.raises(ValueError, match="Argument 'lag' is not a scalar: 2"):
        diff2(x, lag=[1, 2])
    with pytest.raises(ValueError, match="Argument 'differences' is not a scalar: 2"):
        diff2(x, differences=[1, 2])
    with pytest.raises(ValueError, match="Argument 'x' must be a numeric vector"):
        diff2(np.ones((2, 2)))
    with pytest.raises(ValueError, match="Argument 'x' cannot be logical"):
        diff2(np.array([True, False, True]))
    with pytest.raises(ValueError, match="use_names"):
        diff2(x, use_names=None)


def test_empty_input_and_oversized_order():
    assert diff2(np.array([], dtype=np.float64)).shape == (0,)
    assert diff2(np.arange(6), lag=10).shape == (0,)
    assert diff2(np.arange(6), differences=7).shape == (0,)


def test_matches_r():
    if shutil.which("Rscript") is None:
        pytest.skip("Rscript is unavailable")
    reference = _r_cases()
    for case, expected in reference:
        kwargs = {}
        if "lag" in case:
            kwargs["lag"] = case["lag"]
        if "differences" in case:
            kwargs["differences"] = case["differences"]
        if "idxs" in case:
            kwargs["idxs"] = case["idxs"]
        if case.get("error"):
            with pytest.raises(ValueError):
                diff2(case["x"], **kwargs)
            continue
        actual = diff2(case["x"], **kwargs)
        _assert_close(actual, expected)


def _assert_close(actual, expected) -> None:
    actual = np.asarray(actual, dtype=np.float64)
    expected = np.asarray(expected, dtype=np.float64)
    assert actual.shape == expected.shape
    if actual.size == 0:
        return
    both_nan = np.isnan(actual) & np.isnan(expected)
    both_pos = np.isposinf(actual) & np.isposinf(expected)
    both_neg = np.isneginf(actual) & np.isneginf(expected)
    comparable = ~(both_nan | both_pos | both_neg)
    if np.any(comparable):
        assert actual[comparable] == pytest.approx(expected[comparable], abs=1e-8, rel=0)


def _r_cases():
    """Ask matrixStats::diff2 for the same cases the Python side builds."""
    script = textwrap.dedent(
        r"""
        library(matrixStats)
        fmt <- function(expr) {
          value <- tryCatch(expr, error = function(e) structure(conditionMessage(e), class = "err"))
          if (inherits(value, "err")) {
            cat("ERR\n")
            cat(value, "\n", sep = "")
            return()
          }
          cat("OK", length(value), "\n")
          if (length(value) == 0) return()
          shown <- ifelse(is.na(value), "NA", sprintf("%.17g", value))
          cat(shown, sep = "\n")
        }
        x <- 1:6
        fmt(diff2(x))
        fmt(diff2(x, lag = 2, differences = 2))
        fmt(diff2(c(1, NA, 3, 4, NA, 8), differences = 2))
        fmt(diff2(c(1, Inf, 3, -Inf, NaN, 6)))
        fmt(diff2(x, idxs = c(3, 0, 0, 5, 1, 5, 5)))
        fmt(diff2(x, idxs = c(-4, 0, 0, -3, -1, -3, -1)))
        fmt(diff2(x, idxs = 4:9))
        fmt(diff2(x, idxs = c(-5, 0, -3, -1, -9)))
        fmt(diff2(x, idxs = -1:-6))
        fmt(diff2(x, idxs = 4))
        fmt(diff2(x, idxs = -4))
        fmt(diff2(x, idxs = 0))
        fmt(diff2(x, idxs = integer()))
        fmt(diff2(x, idxs = c(NA_real_, 0, 2, Inf)))
        fmt(diff2(x, idxs = c(2.9, 1.1)))
        fmt(diff2(x, idxs = c(-2.9, -0.5)))
        fmt(diff2(x, idxs = c(0.5, 2)))
        fmt(diff2(x, idxs = c(1, 6.1)))
        fmt(diff2(x, idxs = TRUE))
        fmt(diff2(x, idxs = FALSE))
        fmt(diff2(x, idxs = c(FALSE, TRUE, FALSE, TRUE, TRUE, FALSE)))
        fmt(diff2(x, idxs = c(FALSE, TRUE)))
        fmt(diff2(x, idxs = c(FALSE, TRUE, FALSE, TRUE, TRUE, TRUE, FALSE, TRUE)))
        fmt(diff2(x, idxs = c(FALSE, TRUE, NA)))
        fmt(diff2(1:4, idxs = NA))
        fmt(diff2(1:10, lag = 1.9, differences = 2.2))
        fmt(diff2(1:12, lag = 3, differences = 2))
        fmt(diff2(numeric(0)))
        set.seed(1)
        xr <- rnorm(50)
        fmt(diff2(xr, lag = 3, differences = 2, idxs = c(1, 4, 4, 10, 2, 8, NA, 60)))
        cat("SAMPLE", length(xr), "\n")
        cat(sprintf("%.17g\n", xr), sep = "")
        fmt(tryCatch(diff2(x, idxs = c(1, -1)), error = function(e) stop(e)))
        """
    )
    result = subprocess.run(
        ["Rscript", "-e", script],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr)
    cases = _python_cases()
    # The last successful numeric block before SAMPLE is paired in order.
    # SAMPLE is not a case. The final ERR is the mixed-sign case.
    numeric = []
    sample = None
    error = None
    mode = None
    numbers = []
    for line in result.stdout.splitlines():
        if line.startswith("SAMPLE "):
            if mode == "ok":
                numeric.append(np.asarray(numbers, dtype=np.float64))
            mode = "sample"
            numbers = []
            continue
        if line.startswith("OK "):
            if mode == "ok":
                numeric.append(np.asarray(numbers, dtype=np.float64))
            if mode == "sample":
                sample = np.asarray(numbers, dtype=np.float64)
            numbers = []
            if int(line.split()[1]) == 0:
                numeric.append(np.asarray([], dtype=np.float64))
                mode = None
            else:
                mode = "ok"
            continue
        if line.startswith("ERR"):
            if mode == "ok":
                numeric.append(np.asarray(numbers, dtype=np.float64))
            if mode == "sample":
                sample = np.asarray(numbers, dtype=np.float64)
            mode = "err"
            continue
        if mode == "err":
            error = line
            mode = None
            continue
        if mode in ("ok", "sample"):
            numbers.append(np.nan if line == "NA" else float(line))
    if mode == "ok":
        numeric.append(np.asarray(numbers, dtype=np.float64))
    if mode == "sample":
        sample = np.asarray(numbers, dtype=np.float64)
    if error is None or "only 0's may be mixed" not in error:
        raise RuntimeError(result.stdout)
    if sample is None:
        raise RuntimeError("R did not return the standard normal sample")

    built = []
    sample_used = False
    for case in cases:
        if case.get("sample"):
            case = dict(case)
            case["x"] = sample
            sample_used = True
        if case.get("error"):
            built.append((case, None))
        else:
            built.append((case, numeric.pop(0)))
    if numeric or not sample_used:
        raise RuntimeError("R case count does not match the Python cases")
    return built


def _python_cases():
    x = np.arange(1, 7, dtype=np.float64)
    return [
        {"x": x},
        {"x": x, "lag": 2, "differences": 2},
        {"x": np.array([1.0, np.nan, 3.0, 4.0, np.nan, 8.0]), "differences": 2},
        {"x": np.array([1.0, np.inf, 3.0, -np.inf, np.nan, 6.0])},
        {"x": x, "idxs": [3, 0, 0, 5, 1, 5, 5]},
        {"x": x, "idxs": [-4, 0, 0, -3, -1, -3, -1]},
        {"x": x, "idxs": list(range(4, 10))},
        {"x": x, "idxs": [-5, 0, -3, -1, -9]},
        {"x": x, "idxs": list(range(-1, -7, -1))},
        {"x": x, "idxs": 4},
        {"x": x, "idxs": -4},
        {"x": x, "idxs": 0},
        {"x": x, "idxs": np.array([], dtype=np.int64)},
        {"x": x, "idxs": [np.nan, 0.0, 2.0, np.inf]},
        {"x": x, "idxs": [2.9, 1.1]},
        {"x": x, "idxs": [-2.9, -0.5]},
        {"x": x, "idxs": [0.5, 2.0]},
        {"x": x, "idxs": [1.0, 6.1]},
        {"x": x, "idxs": True},
        {"x": x, "idxs": False},
        {"x": x, "idxs": [False, True, False, True, True, False]},
        {"x": x, "idxs": [False, True]},
        {"x": x, "idxs": [False, True, False, True, True, True, False, True]},
        {"x": x, "idxs": [False, True, None]},
        {"x": np.arange(1, 5, dtype=np.float64), "idxs": [None]},
        {"x": np.arange(1, 11, dtype=np.float64), "lag": 1.9, "differences": 2.2},
        {"x": np.arange(1, 13, dtype=np.float64), "lag": 3, "differences": 2},
        {"x": np.array([], dtype=np.float64)},
        {"sample": True, "x": None, "lag": 3, "differences": 2, "idxs": [1, 4, 4, 10, 2, 8, np.nan, 60]},
        {"x": x, "idxs": [1, -1], "error": True},
    ]
