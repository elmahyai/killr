"""Checks for the inequality measures against installed ineq 0.2-13."""

from __future__ import annotations

import math
import shutil
import subprocess
import textwrap

import numpy as np
import pytest

from ineq.measures import Atkinson, Gini, Kolm, RS, Theil, entropy, ineq, var_coeff

X = np.array(
    [541, 1463, 2445, 3438, 4437, 5401, 6392, 8304, 11904, 22261],
    dtype=np.float64,
)
MISSING = np.array([1.0, np.nan, 3.0, np.nan, 5.0])
WITH_ZEROS = np.array([1.0, 0.0, 2.0, 0.0, 3.0])
SMALL = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
TOLERANCE = 1e-8

_R_SCRIPT = textwrap.dedent(
    """
    suppressPackageStartupMessages(library(ineq))
    x <- c(541, 1463, 2445, 3438, 4437, 5401, 6392, 8304, 11904, 22261)
    emit <- function(name, value) cat(sprintf("%s %.17g\\n", name, value))
    emit("Gini", Gini(x))
    emit("Gini_corr", Gini(x, corr=TRUE))
    emit("RS", RS(x))
    emit("Atkinson", Atkinson(x))
    emit("Atkinson_0.5", Atkinson(x, parameter=0.5))
    emit("Atkinson_1", Atkinson(x, parameter=1))
    emit("Atkinson_null", Atkinson(x, parameter=NULL))
    emit("Theil", Theil(x))
    emit("Theil_0", Theil(x, parameter=0))
    emit("Theil_1", Theil(x, parameter=1))
    emit("Theil_2", Theil(x, parameter=2))
    emit("Theil_null", Theil(x, parameter=NULL))
    emit("Kolm", Kolm(x))
    emit("Kolm_null", Kolm(x, parameter=NULL))
    emit("Kolm_small", Kolm(c(1, 2, 3, 4, 5)))
    emit("var", var.coeff(x))
    emit("var_square", var.coeff(x, square=TRUE))
    emit("entropy", entropy(x))
    emit("entropy_0.5", entropy(x, parameter=0.5))
    emit("entropy_0", entropy(x, parameter=0))
    emit("entropy_1", entropy(x, parameter=1))
    emit("entropy_null", entropy(x, parameter=NULL))
    emit("ineq", ineq(x))
    emit("ineq_Atkinson_null", ineq(x, parameter=NULL, type="Atkinson"))
    emit("ineq_G", ineq(x, type="G"))
    emit("ineq_s", ineq(x, type="s"))
    emit("ineq_v", ineq(x, type="v"))
    emit("ineq_square", ineq(x, type="square.var"))
    emit("ineq_entropy", ineq(x, type="e"))
    y <- c(1, 0, 2, 0, 3)
    emit("Theil_zeros", Theil(y, parameter=0))
    emit("Theil_zeros_1", Theil(y, parameter=1))
    emit("entropy_zeros_0", entropy(y, parameter=0))
    emit("entropy_zeros_1", entropy(y, parameter=1))
    z <- c(1, NA, 3, NaN, 5)
    emit("Gini_na", Gini(z, na.rm=FALSE))
    emit("RS_na", RS(z, na.rm=FALSE))
    emit("Atkinson_na", Atkinson(z, na.rm=FALSE))
    emit("Theil_na", Theil(z, na.rm=FALSE))
    emit("Kolm_na", Kolm(z, na.rm=FALSE))
    emit("var_na", var.coeff(z, na.rm=FALSE))
    emit("entropy_na", entropy(z, na.rm=FALSE))
    emit("ineq_na", ineq(z, na.rm=FALSE))
    emit("Gini_drop", Gini(z))
    emit("RS_drop", RS(z))
    emit("Atkinson_drop", Atkinson(z))
    emit("Theil_drop", Theil(z))
    emit("Kolm_drop", Kolm(z))
    emit("var_drop", var.coeff(z))
    emit("var_square_drop", var.coeff(z, square=TRUE))
    emit("entropy_drop", entropy(z))
    emit("ineq_drop", ineq(z, type="RS"))
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


def test_gini_matches_r(reference):
    assert_matches(Gini(X), reference["Gini"])
    assert_matches(Gini(X, corr=True), reference["Gini_corr"])
    assert_matches(ineq(X), reference["ineq"])
    assert_matches(ineq(X, type="G"), reference["ineq_G"])


def test_rs_matches_r(reference):
    assert_matches(RS(X), reference["RS"])


def test_atkinson_matches_r(reference):
    assert_matches(Atkinson(X), reference["Atkinson"])
    assert_matches(Atkinson(X, parameter=0.5), reference["Atkinson_0.5"])
    assert_matches(Atkinson(X, parameter=1), reference["Atkinson_1"])
    assert_matches(Atkinson(X, parameter=None), reference["Atkinson_null"])
    assert_matches(ineq(X, parameter=None, type="Atkinson"), reference["ineq_Atkinson_null"])
    assert_matches(ineq(X, type="Atkinson"), Atkinson(X))


def test_theil_matches_r(reference):
    assert_matches(Theil(X), reference["Theil"])
    assert_matches(Theil(X, parameter=0), reference["Theil_0"])
    assert_matches(Theil(X, parameter=1), reference["Theil_1"])
    assert_matches(Theil(X, parameter=2), reference["Theil_2"])
    assert_matches(Theil(X, parameter=None), reference["Theil_null"])
    assert_matches(Theil(WITH_ZEROS, parameter=0), reference["Theil_zeros"])
    assert_matches(Theil(WITH_ZEROS, parameter=1), reference["Theil_zeros_1"])


def test_kolm_matches_r(reference):
    assert_matches(Kolm(X), reference["Kolm"])
    assert_matches(Kolm(X, parameter=None), reference["Kolm_null"])
    assert_matches(Kolm(SMALL), reference["Kolm_small"])


def test_var_coeff_matches_r(reference):
    assert_matches(var_coeff(X), reference["var"])
    assert_matches(var_coeff(X, square=True), reference["var_square"])
    assert_matches(ineq(X, type="v"), reference["ineq_v"])
    assert_matches(ineq(X, type="s"), reference["ineq_s"])
    assert_matches(ineq(X, type="square.var"), reference["ineq_square"])


def test_entropy_matches_r(reference):
    assert_matches(entropy(X), reference["entropy"])
    assert_matches(entropy(X, parameter=0.5), reference["entropy_0.5"])
    assert_matches(entropy(X, parameter=0), reference["entropy_0"])
    assert_matches(entropy(X, parameter=1), reference["entropy_1"])
    assert_matches(entropy(X, parameter=None), reference["entropy_null"])
    assert_matches(entropy(X, parameter=0), Theil(X, parameter=1))
    assert_matches(entropy(X, parameter=1), Theil(X, parameter=0))
    assert_matches(entropy(WITH_ZEROS, parameter=0), reference["entropy_zeros_0"])
    assert_matches(entropy(WITH_ZEROS, parameter=1), reference["entropy_zeros_1"])
    assert_matches(ineq(X, type="e"), reference["ineq_entropy"])


def test_missing_values_match_r(reference):
    assert_matches(Gini(MISSING, na_rm=False), reference["Gini_na"])
    assert_matches(RS(MISSING, na_rm=False), reference["RS_na"])
    assert_matches(Atkinson(MISSING, na_rm=False), reference["Atkinson_na"])
    assert_matches(Theil(MISSING, na_rm=False), reference["Theil_na"])
    assert_matches(Kolm(MISSING, na_rm=False), reference["Kolm_na"])
    assert_matches(var_coeff(MISSING, na_rm=False), reference["var_na"])
    assert_matches(entropy(MISSING, na_rm=False), reference["entropy_na"])
    assert_matches(ineq(MISSING, na_rm=False), reference["ineq_na"])

    assert_matches(Gini(MISSING), reference["Gini_drop"])
    assert_matches(RS(MISSING), reference["RS_drop"])
    assert_matches(Atkinson(MISSING), reference["Atkinson_drop"])
    assert_matches(Theil(MISSING), reference["Theil_drop"])
    assert_matches(Kolm(MISSING), reference["Kolm_drop"])
    assert_matches(var_coeff(MISSING), reference["var_drop"])
    assert_matches(var_coeff(MISSING, square=True), reference["var_square_drop"])
    assert_matches(entropy(MISSING), reference["entropy_drop"])
    assert_matches(ineq(MISSING, type="RS"), reference["ineq_drop"])


def test_unknown_type_raises():
    with pytest.raises(ValueError):
        ineq(X, type="nope")
    with pytest.raises(ValueError):
        ineq(X, type="")
    with pytest.raises(ValueError):
        ineq(X, type="S")


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
