"""Checks for the poverty measures against installed ineq 0.2-13."""

from __future__ import annotations

import math
import shutil
import subprocess
import textwrap

import numpy as np
import pytest

from ineq.measures import Gini
from ineq.poverty import Foster, SST, Sen, Watts, pov

X = np.array(
    [541, 1463, 2445, 3438, 4437, 5401, 6392, 8304, 11904, 22261],
    dtype=np.float64,
)
Y = np.array(
    [841, 2063, 2445, 3438, 4437, 5401, 6392, 8304, 11304, 21961],
    dtype=np.float64,
)
LINE = 2000
MISSING = np.array([100.0, np.nan, 300.0, np.nan, 5000.0])
MORE = np.array([10.0, 20.0, 20.0, 50.0, 80.0, 100.0, 100.0, 150.0, 400.0, 800.0, 2000.0, 5000.0])
TOLERANCE = 1e-8

_R_SCRIPT = textwrap.dedent(
    """
    suppressPackageStartupMessages(library(ineq))
    x <- c(541, 1463, 2445, 3438, 4437, 5401, 6392, 8304, 11904, 22261)
    y <- c(841, 2063, 2445, 3438, 4437, 5401, 6392, 8304, 11304, 21961)
    more <- c(10, 20, 20, 50, 80, 100, 100, 150, 400, 800, 2000, 5000)
    emit <- function(name, value) cat(sprintf("%s %.17g\\n", name, value))
    emit("Watts_x", Watts(x, 2000))
    emit("Watts_y", Watts(y, 2000))
    emit("pov_x", pov(x, 2000))
    emit("pov_y", pov(y, 2000))
    emit("pov_param_ignored", pov(x, 2000, parameter=2))
    emit("Foster1_x", Foster(x, 2000, parameter=1))
    emit("Foster2_x", Foster(x, 2000, parameter=2))
    emit("Foster1_y", Foster(y, 2000, parameter=1))
    emit("Foster2_y", Foster(y, 2000, parameter=2))
    emit("Foster_null_x", Foster(x, 2000, parameter=NULL))
    emit("Foster0_x", Foster(x, 2000, parameter=0))
    emit("Foster3_x", Foster(x, 2000, parameter=3))
    emit("pov_Foster_x", pov(x, 2000, type="Foster"))
    emit("pov_Foster_y", pov(y, 2000, parameter=1, type="Foster"))
    emit("pov_Foster2_x", pov(x, 2000, parameter=2, type="Foster"))
    emit("pov_Foster2_y", pov(y, 2000, parameter=2, type="F"))
    emit("Sen_x", Sen(x, 2000))
    emit("Sen_y", Sen(y, 2000))
    emit("pov_Sen_x", pov(x, 2000, type="Sen"))
    emit("pov_Sen_y", pov(y, 2000, type="Se"))
    emit("SST_x", SST(x, 2000))
    emit("SST_y", SST(y, 2000))
    emit("pov_SST_x", pov(x, 2000, type="SST"))
    emit("pov_SST_y", pov(y, 2000, type="SS"))
    emit("pov_W", pov(x, 2000, type="W"))
    emit("boundary", Watts(x, 541))
    emit("above", Sen(x, 100))
    emit("equal_line", SST(c(2000, 2000), 2000))
    emit("one_poor", Foster(c(100, 2000, 3000), 2000, parameter=2))
    emit("all_poor", Sen(c(1, 2, 3, 4), 10))
    emit("empty", Watts(numeric(0), 2000))
    emit("all_na", Foster(c(NA, NA), 1))
    emit("na_keep", Watts(c(1, NA, 3), 2, na.rm=FALSE))
    emit("na_drop", Watts(c(1, NA, 3), 2))
    emit("k_na", Sen(x, NA))
    emit("k_na_empty", SST(numeric(0), NA))
    z <- c(100, NA, 300, 5000)
    emit("drop_Watts", Watts(z, 1000))
    emit("drop_Sen", Sen(z, 1000))
    emit("drop_SST", SST(z, 1000))
    emit("drop_Foster", Foster(z, 1000, parameter=2))
    emit("drop_keep_clean", pov(x, 2000, na.rm=FALSE))
    emit("nan_keep", Sen(c(1, NaN, 3), 2, na.rm=FALSE))
    emit("zero_income", Watts(c(0, 5), 1))
    emit("sen_zeros", Sen(c(0, 0, 5), 1))
    emit("more_Watts", Watts(more, 100))
    emit("more_Sen", Sen(more, 100))
    emit("more_SST", SST(more, 100))
    emit("more_Foster1", Foster(more, 100, parameter=1))
    emit("more_Foster2", Foster(more, 100, parameter=2))
    emit("more_pov", pov(more, 100, parameter=NULL, type="Foster"))
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
    values = {}
    for line in result.stdout.splitlines():
        name, raw = line.split(maxsplit=1)
        values[name] = _parse_r(raw)
    return values


def test_watts_matches_r(reference):
    assert_matches(Watts(X, LINE), reference["Watts_x"])
    assert_matches(Watts(Y, LINE), reference["Watts_y"])
    assert_matches(pov(X, LINE), reference["pov_x"])
    assert_matches(pov(Y, LINE), reference["pov_y"])
    assert_matches(pov(X, LINE, parameter=2), reference["pov_param_ignored"])
    assert_matches(pov(X, LINE, type="W"), reference["pov_W"])
    assert_matches(pov(X, LINE, type=None), reference["Watts_x"])
    assert_matches(Watts(MORE, 100), reference["more_Watts"])


def test_foster_matches_r(reference):
    assert_matches(Foster(X, LINE, parameter=1), reference["Foster1_x"])
    assert_matches(Foster(X, LINE, parameter=2), reference["Foster2_x"])
    assert_matches(Foster(Y, LINE, parameter=1), reference["Foster1_y"])
    assert_matches(Foster(Y, LINE, parameter=2), reference["Foster2_y"])
    assert_matches(Foster(X, LINE, parameter=None), reference["Foster_null_x"])
    assert_matches(Foster(X, LINE), reference["Foster_null_x"])
    assert_matches(Foster(X, LINE, parameter=0), reference["Foster0_x"])
    assert_matches(Foster(X, LINE, parameter=3), reference["Foster3_x"])
    assert_matches(pov(X, LINE, type="Foster"), reference["pov_Foster_x"])
    assert_matches(pov(Y, LINE, parameter=1, type="Foster"), reference["pov_Foster_y"])
    assert_matches(pov(X, LINE, parameter=2, type="Foster"), reference["pov_Foster2_x"])
    assert_matches(pov(Y, LINE, parameter=2, type="F"), reference["pov_Foster2_y"])
    assert_matches(pov(X, LINE, type="Foster"), Foster(X, LINE))
    assert_matches(Foster(MORE, 100, parameter=1), reference["more_Foster1"])
    assert_matches(Foster(MORE, 100, parameter=2), reference["more_Foster2"])
    assert_matches(pov(MORE, 100, parameter=None, type="Foster"), reference["more_pov"])


def test_sen_matches_r(reference):
    assert_matches(Sen(X, LINE), reference["Sen_x"])
    assert_matches(Sen(Y, LINE), reference["Sen_y"])
    assert_matches(pov(X, LINE, type="Sen"), reference["pov_Sen_x"])
    assert_matches(pov(Y, LINE, type="Se"), reference["pov_Sen_y"])
    assert_matches(Sen(np.array([1.0, 2.0, 3.0, 4.0]), 10), reference["all_poor"])
    assert_matches(Sen(MORE, 100), reference["more_Sen"])
    poor = X[X < LINE]
    headcount = poor.size / X.size
    shortfall = float(np.sum((LINE - poor) / LINE) / poor.size)
    expected = headcount * (shortfall + (1.0 - shortfall) * Gini(poor))
    assert_matches(Sen(X, LINE), expected)


def test_sst_matches_r(reference):
    assert_matches(SST(X, LINE), reference["SST_x"])
    assert_matches(SST(Y, LINE), reference["SST_y"])
    assert_matches(pov(X, LINE, type="SST"), reference["pov_SST_x"])
    assert_matches(pov(Y, LINE, type="SS"), reference["pov_SST_y"])
    assert_matches(SST(MORE, 100), reference["more_SST"])
    ordered = np.sort(X[X < LINE])
    n = float(X.size)
    ranks = np.arange(1, ordered.size + 1, dtype=np.float64)
    weights = 2.0 * n - 2.0 * ranks + 1.0
    expected = float(np.sum((weights * (LINE - ordered)) / LINE) / (n * n))
    assert_matches(SST(X, LINE), expected)


def test_nobody_strictly_below_is_zero(reference):
    assert_matches(Watts(X, 541), reference["boundary"])
    assert_matches(Sen(X, 100), reference["above"])
    assert_matches(SST(np.array([2000.0, 2000.0]), LINE), reference["equal_line"])
    assert_matches(Foster(np.array([100.0, 2000.0, 3000.0]), LINE, parameter=2), reference["one_poor"])
    assert_matches(Watts(np.array([]), LINE), reference["empty"])
    assert_matches(Foster(np.array([np.nan, np.nan]), 1), reference["all_na"])
    assert Sen(X, LINE) != 0
    for measure in (Watts, Sen, SST, Foster):
        assert measure(X, 100) == 0


def test_missing_values_match_r(reference):
    assert_matches(Watts(np.array([1.0, np.nan, 3.0]), 2, na_rm=False), reference["na_keep"])
    assert_matches(Watts(np.array([1.0, np.nan, 3.0]), 2), reference["na_drop"])
    assert_matches(Sen(X, np.nan), reference["k_na"])
    assert_matches(SST(np.array([]), np.nan), reference["k_na_empty"])
    assert_matches(Watts(MISSING, 1000), reference["drop_Watts"])
    assert_matches(Sen(MISSING, 1000), reference["drop_Sen"])
    assert_matches(SST(MISSING, 1000), reference["drop_SST"])
    assert_matches(Foster(MISSING, 1000, parameter=2), reference["drop_Foster"])
    assert_matches(pov(X, LINE, na_rm=False), reference["drop_keep_clean"])
    assert_matches(Sen(np.array([1.0, np.nan, 3.0]), 2, na_rm=False), reference["nan_keep"])
    for measure in (Watts, Sen, SST, Foster):
        assert math.isnan(measure(MISSING, 1000, na_rm=False))
    assert math.isnan(pov(MISSING, 1000, na_rm=False, type="Foster"))


def test_non_finite_incomes_match_r(reference):
    assert_matches(Watts(np.array([0.0, 5.0]), 1), reference["zero_income"])
    assert_matches(Sen(np.array([0.0, 0.0, 5.0]), 1), reference["sen_zeros"])


def test_unknown_type_raises():
    with pytest.raises(ValueError):
        pov(X, LINE, type="nope")
    with pytest.raises(ValueError):
        pov(X, LINE, type="")
    with pytest.raises(ValueError):
        pov(X, LINE, type="S")
    with pytest.raises(ValueError):
        pov(X, LINE, type="sen")
    with pytest.raises(ValueError):
        pov(X, LINE, type="ST")
    with pytest.raises(ValueError):
        pov(X, LINE, type=1)


def assert_matches(actual, expected, tolerance=TOLERANCE):
    actual = float(actual)
    expected = float(expected)
    if math.isnan(expected):
        assert math.isnan(actual)
        return
    if math.isinf(expected):
        assert actual == expected
        return
    assert actual == pytest.approx(expected, abs=tolerance, rel=0)


def _parse_r(text: str) -> float:
    if text in {"NA", "NaN"}:
        return float("nan")
    if text == "Inf":
        return float("inf")
    if text == "-Inf":
        return float("-inf")
    return float(text)
