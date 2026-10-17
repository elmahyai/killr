"""Checks for weightedVar and the row and column wrappers."""

from __future__ import annotations

import math
import struct
import warnings

import numpy as np
import pytest

from matrixstats.weightedvar import (
    colWeightedSds,
    colWeightedVars,
    rowWeightedSds,
    rowWeightedVars,
    weightedSd,
    weightedVar,
)

_R_NA_PAYLOAD = 0x7A2


def _is_r_na(value) -> bool:
    bits = struct.unpack("<Q", struct.pack("<d", float(value)))[0]
    low = bits & 0xFFFF_FFFF
    high = bits >> 32
    return low == _R_NA_PAYLOAD and high in (0x7FF0_0000, 0x7FF8_0000)


def _matrix_1_to_12():
    return np.arange(1, 13, dtype=float).reshape((3, 4), order="F")


def test_equal_weights_match_the_sample_variance():
    x = np.arange(1, 11, dtype=float)
    assert weightedVar(x) == pytest.approx(55.0 / 6.0)
    assert weightedVar(x, w=None) == pytest.approx(55.0 / 6.0)
    assert weightedVar(x, np.ones(10)) == pytest.approx(55.0 / 6.0)
    assert weightedVar(np.arange(1, 11)) == pytest.approx(55.0 / 6.0)
    assert weightedSd(x) == pytest.approx(math.sqrt(55.0 / 6.0))


def test_frequency_weights_repeat_the_observations():
    assert weightedVar(np.array([2.0, 4.0, 5.0]), np.array([2.0, 1.0, 3.0])) == pytest.approx(
        2.166666666666667
    )
    assert weightedVar(np.arange(1, 11, dtype=float), np.full(10, 3.0)) == pytest.approx(
        float(np.var(np.repeat(np.arange(1, 11), 3), ddof=1))
    )


def test_non_positive_weights_are_dropped_and_missing_weights_stay_missing():
    assert weightedVar(np.array([1.0, 2.0, 3.0]), np.array([1.0, -1.0, 1.0])) == pytest.approx(2.0)
    assert weightedVar(np.array([1.0, 2.0, 3.0]), np.array([1.0, 0.0, 1.0])) == pytest.approx(2.0)
    assert weightedVar(np.array([1.0, 2.0, 3.0]), np.array([1.0, -np.inf, 1.0])) == pytest.approx(2.0)
    # A negative weight is dropped, so one observation remains. weightedMean would keep it.
    assert _is_r_na(weightedVar(np.array([4.0, 1.0]), np.array([1.0, -0.5])))
    assert _is_r_na(weightedVar(np.array([1.0, 2.0, 3.0]), np.array([1.0, np.nan, 1.0]), na_rm=False))
    assert _is_r_na(weightedVar(np.array([1.0, 2.0, 3.0]), np.array([1.0, np.nan, 1.0]), na_rm=True))
    assert weightedVar(np.array([1.0, np.nan, 3.0]), np.array([1.0, np.nan, 1.0]), na_rm=True) == pytest.approx(2.0)
    assert weightedVar(np.array([1.0, np.nan, 3.0]), np.array([1.0, 0.0, 1.0]), na_rm=False) == pytest.approx(2.0)


def test_missing_x_infinite_weights_and_short_inputs():
    assert _is_r_na(weightedVar(np.array([1.0, np.nan, 3.0, 4.0])))
    assert weightedVar(np.array([1.0, np.nan, 3.0, 4.0]), na_rm=True) == pytest.approx(
        float(np.var([1.0, 3.0, 4.0], ddof=1))
    )
    assert weightedVar(np.array([1.0, 2.0, 3.0, 4.0]), np.array([1.0, np.inf, np.inf, 1.0])) == pytest.approx(0.5)
    assert _is_r_na(weightedVar(np.array([1.0, 2.0, 3.0]), np.array([np.inf, 1.0, -np.inf])))
    assert _is_r_na(weightedVar(np.array([], dtype=float)))
    assert _is_r_na(weightedVar(np.array([1.0])))
    assert _is_r_na(weightedVar(1))
    assert _is_r_na(weightedVar(True))
    assert weightedVar(np.array([True, False, True, False])) == pytest.approx(1.0 / 3.0)
    assert _is_r_na(weightedSd(np.array([1.0])))


def test_small_weight_sum_is_negative_and_the_square_root_is_nan():
    with pytest.warns(UserWarning, match=r"sum\(w\) <= 1\): -1 \(wsum = 0.8\)"):
        value = weightedVar(np.array([1.0, 2.0]), np.array([0.4, 0.4]))
    assert value == pytest.approx(-1.0)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        root = weightedSd(np.array([1.0, 2.0]), np.array([0.4, 0.4]))
    messages = [str(item.message) for item in caught]
    assert any("sum(w) <= 1" in message for message in messages)
    assert any(message == "NaNs produced" for message in messages)
    assert math.isnan(root) and not _is_r_na(root)


def test_weight_sum_of_one_is_inf_or_plain_nan():
    with pytest.warns(UserWarning, match=r"Inf \(wsum = 1\)"):
        assert math.isinf(weightedVar(np.array([1.0, 2.0]), np.array([0.5, 0.5])))
    with pytest.warns(UserWarning, match=r"NaN \(wsum = 1\)"):
        value = weightedVar(np.array([1.0, 1.0]), np.array([0.5, 0.5]))
    assert math.isnan(value) and not _is_r_na(value)


def test_center_is_the_supplied_scalar_not_the_mean():
    x = np.arange(1, 11, dtype=float)
    assert weightedVar(x, center=0) == pytest.approx(385.0 / 9.0)
    assert weightedVar(x, center=5.5) == pytest.approx(55.0 / 6.0)
    assert _is_r_na(weightedVar(x, center=np.nan))
    with pytest.warns(UserWarning, match="not a multiple of shorter object length"):
        assert weightedVar(np.arange(1, 7, dtype=float), center=np.array([1.0, 2.0, 3.0, 4.0])) == pytest.approx(6.4)
    assert weightedVar(np.arange(1, 5, dtype=float), center=np.array([], dtype=float)) == pytest.approx(0.0)


def test_null_weight_is_not_subset_by_idxs():
    # w stays rep(1, 6). The product recycles c(1, 3, 5) and the divisor is 5.
    assert weightedVar(np.arange(1, 7), idxs=np.array([1, 3, 5])) == pytest.approx(3.2)
    assert weightedVar(np.arange(1, 7), idxs=np.array([1, 3, 5]), na_rm=True) == pytest.approx(4.0)
    assert weightedVar(np.arange(1, 7), idxs=np.array([1, 3, 5]), center=0) == pytest.approx(14.0)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        assert weightedVar(np.arange(1, 5), idxs=np.array([1, 1, 1])) == pytest.approx(0.0)
    assert sum("not a multiple" in str(item.message) for item in caught) == 2
    assert weightedVar(np.arange(1, 5), idxs=np.array([1, 1, 1]), na_rm=True) == pytest.approx(0.0)
    assert _is_r_na(weightedVar(np.arange(1, 7), idxs=1))


def test_vector_indexes_follow_base_subsetting():
    x = np.arange(1, 7, dtype=float)
    w = np.arange(1, 7, dtype=float)
    assert weightedVar(x, w, idxs=np.array([1, 3, 5])) == pytest.approx(2.111111111111111)
    assert weightedVar(x, w, idxs=np.array([0, 2, 0, 4])) == pytest.approx(1.0666666666666667)
    assert weightedVar(x, w, idxs=np.array([-1, -2])) == pytest.approx(1.2418300653594772)
    assert weightedVar(x, w, idxs=np.array([-5, 0, -3, -1, -9])) == pytest.approx(2.4242424242424243)
    assert weightedVar(x, w, idxs=np.array([3, 0, 0, 5, 1, 5, 5])) == pytest.approx(1.263157894736842)
    assert _is_r_na(weightedVar(x, w, idxs=np.array([0.5, 2.9])))
    assert _is_r_na(weightedVar(x, w, idxs=np.array([7])))
    assert _is_r_na(weightedVar(x, w, idxs=np.array([NA := np.nan, 2.0])))
    assert _is_r_na(weightedVar(x, w, idxs=0))
    assert _is_r_na(weightedVar(x, idxs=False))
    assert weightedVar(np.arange(1, 5), idxs=True) == pytest.approx(float(np.var(np.arange(1, 5), ddof=1)))
    assert weightedVar(x, w, idxs=np.array([True, False])) == pytest.approx(
        weightedVar(x[0::2], w[0::2])
    )
    with pytest.raises(ValueError, match="only 0's may be mixed with negative subscripts"):
        weightedVar(x, idxs=np.array([1, -1]))
    with pytest.raises(ValueError, match="only 0's may be mixed with negative subscripts"):
        weightedVar(x, idxs=np.array([-np.inf, -1.0]))
    with pytest.raises(ValueError, match="does not match"):
        weightedVar(np.arange(3), w=np.ones(2))


def test_rows_and_columns_apply_the_same_variance():
    x = _matrix_1_to_12()
    assert rowWeightedVars(x) == pytest.approx([15.0, 15.0, 15.0])
    assert colWeightedVars(x) == pytest.approx([1.0, 1.0, 1.0, 1.0])
    assert rowWeightedSds(x) == pytest.approx([math.sqrt(15.0)] * 3)
    assert colWeightedSds(x) == pytest.approx([1.0, 1.0, 1.0, 1.0])
    printed = np.array([[1.0, 4.0, 7.0, 10.0], [2.0, 5.0, 8.0, 11.0], [3.0, 6.0, 9.0, 12.0]])
    assert rowWeightedVars(printed) == pytest.approx([15.0, 15.0, 15.0])
    assert rowWeightedVars(np.asfortranarray(printed)) == pytest.approx([15.0, 15.0, 15.0])


def test_margin_subset_weights_and_missing_rows():
    x = _matrix_1_to_12()
    assert rowWeightedVars(x, rows=np.array([1, 3]), cols=np.array([2, 4])) == pytest.approx([18.0, 18.0])
    assert rowWeightedVars(x, w=np.array([1.0, 2.0, 3.0, 4.0])) == pytest.approx([10.0, 10.0, 10.0])
    assert colWeightedVars(x, w=np.array([1.0, 2.0, 3.0])) == pytest.approx([0.6666666666666667] * 4)
    assert rowWeightedVars(x, w=np.array([1.0, 2.0, 3.0, 4.0]), cols=np.array([1, 3])) == pytest.approx([9.0, 9.0, 9.0])
    assert colWeightedVars(x, w=np.array([1.0, 2.0, 3.0]), rows=np.array([1, 3])) == pytest.approx([1.0, 1.0, 1.0, 1.0])
    assert rowWeightedVars(x, rows=np.array([True, False])) == pytest.approx([15.0, 15.0])
    assert rowWeightedVars(x, rows=np.array([0.5, 2.9])) == pytest.approx([15.0])
    assert rowWeightedVars(x, rows=np.array([-1.2, -0.2])) == pytest.approx([15.0, 15.0])
    assert rowWeightedVars(x, cols=np.array([1, 1])) == pytest.approx([0.0, 0.0, 0.0])
    selected = rowWeightedVars(x, rows=np.array([1.0, np.nan]))
    assert selected[0] == pytest.approx(15.0)
    assert _is_r_na(selected[1])
    assert rowWeightedVars(x, center=0) == pytest.approx([55.333333333333329, 71.333333333333329, 90.0])
    ragged = np.array([[1.0, 4.0], [np.nan, 5.0], [3.0, 6.0]])
    na_rows = rowWeightedVars(ragged, na_rm=True)
    assert na_rows[0] == pytest.approx(4.5)
    assert _is_r_na(na_rows[1])
    assert na_rows[2] == pytest.approx(4.5)
    assert rowWeightedVars(x, w=np.array([1.0, 0.0, 1.0, 1.0])) == pytest.approx([21.0, 21.0, 21.0])
    assert rowWeightedVars(x, w=np.array([1.0, np.inf, np.inf, 0.0])) == pytest.approx([4.5, 4.5, 4.5])
    assert np.all([_is_r_na(value) for value in rowWeightedVars(x, w=np.array([10.0, 20.0]), cols=np.array([1, 3]))])


def test_empty_margins_and_argument_errors():
    assert rowWeightedVars(np.zeros((0, 3))) .size == 0
    assert np.all([_is_r_na(value) for value in rowWeightedVars(np.zeros((3, 0)))])
    assert np.all([_is_r_na(value) for value in colWeightedVars(np.zeros((0, 3)))])
    assert colWeightedVars(np.zeros((3, 0)), w=np.arange(1, 4, dtype=float)).size == 0
    assert np.all([_is_r_na(value) for value in colWeightedVars(np.zeros((0, 3)), w=np.zeros(0))])
    with pytest.raises(ValueError, match="does not match: 2 != 3"):
        rowWeightedVars(np.zeros((0, 3)), w=np.array([1.0, 2.0]))
    with pytest.raises(ValueError, match="does not match: 1 != 0"):
        colWeightedVars(np.zeros((0, 3)), w=np.array([1.0]))
    with pytest.raises(ValueError, match="does not match: 2 != 4"):
        rowWeightedVars(_matrix_1_to_12(), w=np.ones(2))
    with pytest.raises(ValueError, match="dim\\(X\\) must have a positive length"):
        rowWeightedVars(np.arange(12))
    with pytest.raises(ValueError, match="subscript out of bounds"):
        rowWeightedVars(_matrix_1_to_12(), rows=np.array([1, 5]))
    with pytest.raises(ValueError, match="logical subscript too long"):
        rowWeightedVars(_matrix_1_to_12(), rows=np.array([True, False, True, True]))
    with pytest.raises(ValueError, match="only 0's may be mixed"):
        rowWeightedVars(_matrix_1_to_12(), rows=np.array([1, -1]))
    with pytest.raises(ValueError, match="not logical"):
        rowWeightedVars(_matrix_1_to_12(), na_rm=1)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        with pytest.raises(ValueError, match="subscript out of bounds"):
            rowWeightedVars(_matrix_1_to_12(), rows=2147483647)
    assert caught == []
    with pytest.warns(UserWarning, match="NAs introduced by coercion to integer range"):
        coerced = rowWeightedVars(_matrix_1_to_12(), rows=np.inf)
    assert coerced.shape == (1,)
    assert _is_r_na(coerced[0])
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        values = rowWeightedVars(np.arange(1, 7, dtype=float).reshape(2, 3, order="F"), w=np.array([0.2, 0.2, 0.2]))
    assert values == pytest.approx([-4.0, -4.0])
    assert len(caught) == 2


def test_logical_matrix_and_duplicate_column_deviation():
    logical = np.array([[True, True, True], [False, False, False]])
    assert rowWeightedVars(logical) == pytest.approx([0.0, 0.0])
    assert colWeightedSds(logical) == pytest.approx([math.sqrt(0.5)] * 3)
