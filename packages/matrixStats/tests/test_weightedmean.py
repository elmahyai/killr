"""Checks for weightedMean against the matrixStats 1.5.0 results."""

from __future__ import annotations

import math
import struct

import numpy as np
import pytest

from matrixstats.weightedmean import weightedMean

# Quiet NaN that R treats as NA_real_. A plain NaN does not have this payload.
_R_NA_PAYLOAD = 0x7A2


def _is_r_na(value) -> bool:
    bits = struct.unpack("<Q", struct.pack("<d", float(value)))[0]
    low = bits & 0xFFFF_FFFF
    high = bits >> 32
    return low == _R_NA_PAYLOAD and high in (0x7FF0_0000, 0x7FF8_0000)


def _is_plain_nan(value) -> bool:
    return math.isnan(value) and not _is_r_na(value)


def test_empty_input_returns_nan():
    assert _is_plain_nan(weightedMean([]))
    assert _is_plain_nan(weightedMean(np.array([], dtype=np.float64), w=np.array([])))


def test_equal_weights_match_the_mean():
    x = np.arange(1, 11, dtype=float)
    assert weightedMean(x) == pytest.approx(5.5)
    assert weightedMean(x, w=None) == pytest.approx(5.5)
    assert weightedMean(x, np.ones(10)) == pytest.approx(5.5)


def test_heavier_first_weight_pulls_the_mean_down():
    x = np.arange(1, 11, dtype=float)
    w = np.ones(10)
    w[0] = 5
    assert weightedMean(x, w) == pytest.approx(59.0 / 14.0)
    w[0] = 8.5
    assert weightedMean(x, w) == pytest.approx(62.5 / 17.5)


def test_na_in_x_is_kept_or_skipped():
    x = np.array([1.0, np.nan, 3.0])
    assert _is_r_na(weightedMean(x, na_rm=False))
    assert weightedMean(x, na_rm=True) == pytest.approx(2.0)


def test_na_in_w_is_missing_even_when_na_rm_is_true():
    x = np.array([1.0, 2.0, 3.0])
    w = np.array([1.0, np.nan, 1.0])
    assert _is_r_na(weightedMean(x, w, na_rm=False))
    assert _is_r_na(weightedMean(x, w, na_rm=True))


def test_paired_missing_x_and_w_is_skipped_when_na_rm_is_true():
    x = np.array([np.nan, 2.0, 3.0])
    w = np.array([np.nan, 1.0, 1.0])
    assert math.isnan(weightedMean(x, w, na_rm=False))
    assert weightedMean(x, w, na_rm=True) == pytest.approx(2.5)


def test_negative_weight_stays_in_the_sum():
    # matrixStats 1.5.0: (4*1 + 1*(-0.5)) / (1 - 0.5) = 7.
    # The manual says a negative weight counts as zero; the C code does not.
    x = np.array([4.0, 1.0])
    w = np.array([1.0, -0.5])
    assert weightedMean(x, w) == pytest.approx(7.0)


def test_zero_weight_skips_a_missing_x_without_na_rm():
    x = np.array([1.0, np.nan, 3.0])
    w = np.array([1.0, 0.0, 1.0])
    assert weightedMean(x, w, na_rm=False) == pytest.approx(2.0)


def test_refine_adds_the_residual_pass():
    x = np.array([1e16, 1.0, -1e16, 2.0])
    w = np.ones(4)
    assert weightedMean(x, w, refine=False) == pytest.approx(0.5)
    assert weightedMean(x, w, refine=True) == pytest.approx(0.875)


def test_infinite_weight_is_nan_and_all_zero_weights_are_nan():
    x = np.arange(1, 11, dtype=float)
    w = np.ones(10)
    w[0] = np.inf
    assert _is_plain_nan(weightedMean(x, w))
    assert _is_plain_nan(weightedMean(x, np.zeros(10)))


def test_one_based_indices_and_logical_recycling():
    x = np.arange(1, 6, dtype=float)
    assert weightedMean(x, idxs=np.array([2, 4])) == pytest.approx(3.0)
    assert weightedMean(x, idxs=np.array([-2])) == pytest.approx(3.25)
    assert weightedMean(x, idxs=4) == pytest.approx(4.0)
    assert weightedMean(x, idxs=np.array([True, False])) == pytest.approx(3.0)
    assert math.isnan(weightedMean(x, idxs=np.array([], dtype=np.int64)))
    assert math.isnan(weightedMean(x, idxs=0))


def test_missing_and_out_of_bounds_indices():
    x = np.arange(1, 6, dtype=float)
    missing = np.array([np.nan, 2.0])
    assert math.isnan(weightedMean(x, idxs=missing, na_rm=False))
    assert weightedMean(x, idxs=missing, na_rm=True) == pytest.approx(2.0)
    out = np.array([1.0, 8.0])
    assert math.isnan(weightedMean(x, idxs=out, na_rm=False))
    assert weightedMean(x, idxs=out, na_rm=True) == pytest.approx(1.0)


def test_fractional_index_truncates_toward_zero():
    x = np.array([10.0, 20.0, 30.0, 40.0, 50.0])
    assert weightedMean(x, idxs=np.array([0.5, 2.9])) == pytest.approx(15.0)


def test_length_mismatch_and_mixed_signs_raise():
    x = np.arange(3, dtype=float)
    with pytest.raises(ValueError, match="different lengths"):
        weightedMean(x, w=np.ones(2))
    with pytest.raises(ValueError, match="negative subscripts"):
        weightedMean(x, idxs=np.array([1, -1]))


def test_subset_uses_the_same_positions_in_x_and_w():
    x = np.arange(1, 6, dtype=float)
    w = np.array([1.0, 10.0, 1.0, 1.0, 1.0])
    assert weightedMean(x, w, idxs=np.array([1, 2])) == pytest.approx(21.0 / 11.0)
