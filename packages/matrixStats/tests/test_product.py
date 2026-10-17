"""Checks for matrixStats::product, including a comparison with R."""

from __future__ import annotations

import math
import shutil
import subprocess

import numpy as np
import pytest

from matrixstats.product import product

R_NA_BITS = 0x7FF00000000007A2


def test_empty_product_is_one():
    assert product(np.array([], dtype=np.float64)) == 1.0
    assert product(np.array([10.0, 20.0, 30.0]), idxs=np.array([], dtype=np.int64)) == 1.0
    assert product(np.array([], dtype=np.float64), idxs=-1) == 1.0


def test_negatives_stay_within_tolerance():
    assert product(np.array([1.0, -4.0, 2.0])) == pytest.approx(-8.0, abs=1e-8)
    assert product([1, -4, 2]) == pytest.approx(-8.0, abs=1e-8)


def test_real_zero_keeps_a_negative_sign():
    value = product(np.array([-1.0, 0.0]))
    assert value == 0.0
    assert math.copysign(1.0, value) == -1.0


def test_integer_zero_is_positive():
    value = product(np.array([-1, 0], dtype=np.int32))
    assert value == 0.0
    assert math.copysign(1.0, value) == 1.0


def test_short_vector_with_zero_negative_and_na():
    values = np.array([0.0, -2.0, np.nan])
    assert _is_r_na(product(values))
    kept = product(values, na_rm=True)
    assert kept == 0.0
    assert math.copysign(1.0, kept) == -1.0
    assert _is_r_na(product([0, -2, None]))


def test_missing_infinity_and_overflow():
    assert _is_r_na(product(np.array([1.0, np.nan, 2.0])))
    assert product(np.array([1.0, np.nan, 2.0]), na_rm=True) == pytest.approx(2.0, abs=1e-8)
    assert product(np.array([np.nan, np.nan]), na_rm=True) == 1.0
    assert _is_r_na(product(np.array([0.0, np.inf])))
    assert _is_r_na(product(np.array([0.0, np.inf]), na_rm=True))
    assert product(np.array([2.0, np.inf])) == np.inf
    assert product(np.array([2.0, -np.inf])) == -np.inf
    assert product(np.array([1e200, 1e200, 1e200])) == np.inf
    assert product(np.array([-1e200, 1e200, 1e200])) == -np.inf


def test_one_based_indexes():
    values = np.array([10.0, 20.0, 30.0, 40.0])
    assert product(values) == pytest.approx(240_000.0, abs=1e-8)
    assert product(values, idxs=[1, 3]) == pytest.approx(300.0, abs=1e-8)
    assert product(values, idxs=0) == 1.0
    assert product(values, idxs=[-1, -2]) == pytest.approx(1_200.0, abs=1e-8)
    assert _is_r_na(product(values, idxs=[1, 9]))
    assert product(values, idxs=[1, 9], na_rm=True) == pytest.approx(10.0, abs=1e-8)
    assert product(values, idxs=0.5) == pytest.approx(10.0, abs=1e-8)
    assert product(values, idxs=[1.9, 3.1]) == pytest.approx(300.0, abs=1e-8)
    assert product(values, idxs=[-1.2, -3.9]) == pytest.approx(800.0, abs=1e-8)
    assert product(values, idxs=[2, 2, 1]) == pytest.approx(4_000.0, abs=1e-8)
    assert product(values, idxs=np.array([True, False])) == pytest.approx(300.0, abs=1e-8)
    assert product(values, idxs=True) == pytest.approx(240_000.0, abs=1e-8)
    assert product(values, idxs=False) == 1.0
    assert _is_r_na(product(values, idxs=[True, None, False, True]))
    with pytest.raises(ValueError, match="negative subscripts"):
        product(values, idxs=[1, -2])


def test_rejects_a_logical_vector_and_a_matrix():
    with pytest.raises(ValueError, match="logical"):
        product(np.array([True, False]))
    with pytest.raises(ValueError, match="numeric vector"):
        product(np.array([[1.0, 2.0], [3.0, 4.0]]))


def test_matches_r():
    if shutil.which("Rscript") is None:
        pytest.skip("Rscript is unavailable")
    sample = np.random.default_rng(0).uniform(0.99, 1.01, 4000)
    reference = _r_product(sample)
    assert product(sample) == pytest.approx(reference, abs=1e-8)
    short = np.array([0.0, -2.0, np.nan])
    assert _same_missing(product(short), _r_value("c(0, -2, NA)", False))
    kept = product(short, na_rm=True)
    reference_kept = _r_value("c(0, -2, NA)", True)
    assert kept == pytest.approx(reference_kept, abs=1e-8)
    assert math.copysign(1.0, kept) == math.copysign(1.0, reference_kept)


def _is_r_na(value: float) -> bool:
    return int(np.float64(value).view(np.uint64)) == R_NA_BITS


def _same_missing(actual: float, reference: float) -> bool:
    return _is_r_na(actual) and math.isnan(reference)


def _r_product(sample: np.ndarray) -> float:
    path = "/tmp/killr-product-check.bin"
    np.ascontiguousarray(sample, dtype="<f8").tofile(path)
    script = (
        "library(matrixStats); "
        f'x <- readBin("{path}", "double", {sample.size}); '
        'cat(sprintf("%.17g", product(x)))'
    )
    completed = subprocess.run(
        ["Rscript", "-e", script],
        check=True,
        capture_output=True,
        text=True,
    )
    return float(completed.stdout)


def _r_value(literal: str, na_rm: bool) -> float:
    flag = "TRUE" if na_rm else "FALSE"
    script = (
        "library(matrixStats); "
        f"z <- product({literal}, na.rm={flag}); "
        'if (is.na(z)) cat("NA") else cat(sprintf("%.17g", z))'
    )
    completed = subprocess.run(
        ["Rscript", "-e", script],
        check=True,
        capture_output=True,
        text=True,
    )
    text = completed.stdout.strip()
    if text == "NA":
        return float("nan")
    return float(text)
