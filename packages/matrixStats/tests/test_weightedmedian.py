"""Checks for weightedMedian against the matrixStats 1.5.0 results."""

from __future__ import annotations

import struct

import numpy as np
import pytest

from matrixstats.weightedmedian import weightedMedian

# Quiet NaN that R treats as NA_real_. A plain NaN does not have this payload.
_R_NA_PAYLOAD = 0x7A2


def _is_r_na(value) -> bool:
    bits = struct.unpack("<Q", struct.pack("<d", float(value)))[0]
    low = bits & 0xFFFF_FFFF
    high = bits >> 32
    return low == _R_NA_PAYLOAD and high in (0x7FF0_0000, 0x7FF8_0000)


def test_equal_weights_match_the_sample_median():
    x = np.arange(1, 11, dtype=float)
    assert weightedMedian(x) == pytest.approx(5.5)
    assert weightedMedian(x, w=None) == pytest.approx(5.5)
    assert weightedMedian(x, np.ones(10)) == pytest.approx(5.5)


def test_interpolate_false_honors_ties():
    x = np.arange(1, 11, dtype=float)
    assert weightedMedian(x, ties="weighted") == pytest.approx(5.5)
    assert weightedMedian(x, ties="min") == pytest.approx(5.0)
    assert weightedMedian(x, ties="max") == pytest.approx(6.0)
    assert weightedMedian(x, ties="mean") == pytest.approx(5.5)
    # An explicit interpolate stays in charge even when ties is also set.
    assert weightedMedian(x, interpolate=True, ties="min") == pytest.approx(5.5)


def test_heavier_first_weight_and_infinite_weight():
    x = np.arange(1, 11, dtype=float)
    w = np.ones(10)
    w[0] = 5
    assert weightedMedian(x, w) == pytest.approx(3.5)
    w[0] = 8.5
    assert weightedMedian(x, w) == pytest.approx(1.9473684210526319)
    w[0] = np.inf
    assert weightedMedian(x, w) == pytest.approx(1.0)
    w[0] = 1
    w[-1] = np.inf
    assert weightedMedian(x, w) == pytest.approx(10.0)


def test_zero_weight_and_negative_weight():
    x = np.arange(1, 11, dtype=float)
    assert _is_r_na(weightedMedian(x, np.zeros(10)))
    w = np.ones(10)
    w[0] = -1
    assert weightedMedian(x, w) == pytest.approx(6.0)
    w[0] = -np.inf
    assert weightedMedian(x, w) == pytest.approx(6.0)


def test_na_in_x_and_a_zero_weight_on_a_missing_x():
    x = np.array([1.0, np.nan, 3.0])
    assert _is_r_na(weightedMedian(x, na_rm=False))
    assert weightedMedian(x, na_rm=True) == pytest.approx(2.0)
    paired = np.array([1.0, np.nan, 4.0])
    assert weightedMedian(paired, np.array([1.0, 0.0, 1.0]), na_rm=False) == pytest.approx(2.5)


def test_na_in_w_is_dropped_only_when_na_rm_is_true():
    x = np.array([1.0, 5.0, 9.0])
    w = np.array([1.0, np.nan, 1.0])
    assert _is_r_na(weightedMedian(x, w, na_rm=False))
    assert weightedMedian(x, w, na_rm=True) == pytest.approx(5.0)


def test_interpolate_true_and_false_on_tied_values():
    x = np.array([0.0, 0.0, 10.0])
    heavy_last = np.array([0.15, 0.40, 0.45])
    heavy_first = np.array([0.40, 0.15, 0.45])
    assert weightedMedian(x, heavy_last, interpolate=True) == pytest.approx(3.5294117647058822)
    assert weightedMedian(x, heavy_first, interpolate=True) == pytest.approx(0.83333333333333215)
    assert weightedMedian(x, heavy_last, interpolate=False) == pytest.approx(0.0)
    assert weightedMedian(x, heavy_first, interpolate=False, ties="max") == pytest.approx(0.0)


def test_infinite_weights_ignore_ties_and_odd_counts_use_partial_sort():
    x = np.array([1.0, 10.0, 3.0, 7.0])
    mixed = np.array([np.inf, -np.inf, 1.0, 2.0])
    assert weightedMedian(x, mixed) == pytest.approx(5.5)
    assert weightedMedian(x, mixed, ties="min") == pytest.approx(5.5)
    odd = np.array(
        [
            -0.6264538107423324,
            0.1836433242220822,
            -0.8356286124100472,
            1.5952808021377917,
            0.3295077718153605,
        ]
    )
    assert weightedMedian(odd, np.full(5, np.inf)) == pytest.approx(-0.83562861241004716)


def test_empty_input_is_na_and_bad_arguments_raise():
    assert _is_r_na(weightedMedian([]))
    assert _is_r_na(weightedMedian(np.array([], dtype=np.float64), w=np.array([])))
    with pytest.raises(ValueError, match="different lengths"):
        weightedMedian(np.arange(3, dtype=float), w=np.ones(2))
    with pytest.raises(ValueError, match="negative subscripts"):
        weightedMedian(np.arange(3, dtype=float), idxs=np.array([1, -1]))
    with pytest.raises(ValueError, match="Unknown value of argument 'ties'"):
        weightedMedian(np.arange(1, 5, dtype=float), ties="mi")
    with pytest.raises(ValueError, match="interpolate"):
        weightedMedian(np.arange(3, dtype=float), interpolate=float("nan"))


def test_one_based_indices_zero_weight_and_logical():
    x = np.arange(1, 6, dtype=float)
    assert weightedMedian(x, idxs=np.array([2, 4])) == pytest.approx(3.0)
    assert weightedMedian(x, idxs=np.array([-2])) == pytest.approx(3.5)
    assert weightedMedian(x, idxs=np.array([True, False])) == pytest.approx(3.0)
    wide = np.array([10.0, 20.0, 30.0, 40.0, 50.0])
    assert weightedMedian(wide, idxs=np.array([0.5, 2.9])) == pytest.approx(15.0)
    assert _is_r_na(weightedMedian(x, idxs=np.array([], dtype=np.int64)))
