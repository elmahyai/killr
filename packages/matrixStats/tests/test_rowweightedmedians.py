"""Checks for rowWeightedMedians and colWeightedMedians."""

from __future__ import annotations

import numpy as np
import pytest

from matrixstats.rowweightedmedians import colWeightedMedians, rowWeightedMedians

_NA_BITS = np.uint64(0x7FF00000000007A2)
_X = np.array(
    [
        [1.0, 5.0, 9.0],
        [2.0, 6.0, 10.0],
        [3.0, 7.0, 11.0],
        [4.0, 8.0, 12.0],
    ]
)
_W = np.array([1.0, 2.0, 3.0])


def _is_r_na(value) -> bool:
    bits = int(np.float64(value).view(np.uint64))
    low = bits & 0xFFFFFFFF
    high = bits >> 32
    return low == 0x7A2 and high in (0x7FF00000, 0x7FF80000)


def _is_plain_nan(value) -> bool:
    bits = int(np.float64(value).view(np.uint64))
    return bits in (0x7FF8000000000000, 0xFFF8000000000000)


def test_weighted_rows_and_columns_of_a_4_by_3_matrix():
    rows = rowWeightedMedians(_X, _W)
    assert rows == pytest.approx([6.6, 7.6, 8.6, 9.6])
    columns = colWeightedMedians(_X, np.array([1.0, 2.0, 3.0, 4.0]))
    assert columns == pytest.approx([3.142857142857143, 7.142857142857143, 11.142857142857142])


def test_missing_weights_follow_the_unweighted_median():
    assert rowWeightedMedians(_X) == pytest.approx([5.0, 6.0, 7.0, 8.0])
    assert colWeightedMedians(_X) == pytest.approx([2.5, 6.5, 10.5])
    even = np.array([[1.0, 5.0, 9.0, 13.0]])
    assert rowWeightedMedians(even) == pytest.approx(7.0)
    # ties is an argument of weightedMedian, and the unweighted path ignores it.
    assert rowWeightedMedians(even, ties="min") == pytest.approx(7.0)
    assert rowWeightedMedians(even, np.ones(4), ties="min") == pytest.approx(5.0)


def test_nonpositive_and_missing_weights():
    zeros = rowWeightedMedians(_X, np.zeros(3))
    assert all(_is_r_na(value) for value in zeros)
    missing = rowWeightedMedians(_X, np.array([1.0, np.nan, 1.0]))
    assert all(_is_r_na(value) for value in missing)
    assert rowWeightedMedians(_X, np.array([1.0, np.nan, 1.0]), na_rm=True) == pytest.approx(
        [5.0, 6.0, 7.0, 8.0]
    )
    assert rowWeightedMedians(_X, np.array([-0.0, 1.0, 1.0])) == pytest.approx([7.0, 8.0, 9.0, 10.0])
    with pytest.raises(ValueError, match="must not contain negative values"):
        rowWeightedMedians(_X, np.array([1.0, -1.0, 1.0]), cols=[1, 3])


def test_infinite_weight_ignores_ties():
    assert rowWeightedMedians(np.array([[1.0, 2.0]]), np.array([7.0, np.inf])) == pytest.approx(2.0)
    pair = np.array([[4.0, 1.0, 3.0]])
    weights = np.array([1.0, np.inf, np.inf])
    assert rowWeightedMedians(pair, weights, ties="min") == pytest.approx(2.0)
    assert rowWeightedMedians(pair, weights, ties="max") == pytest.approx(2.0)


def test_missing_values_and_empty_margins():
    dirty = _X.copy()
    dirty[0, 1] = np.nan
    dropped = rowWeightedMedians(dirty, _W)
    assert _is_r_na(dropped[0])
    assert dropped[1:] == pytest.approx([7.6, 8.6, 9.6])
    assert rowWeightedMedians(dirty, _W, na_rm=True)[0] == pytest.approx(7.0)
    unweighted = rowWeightedMedians(dirty)
    assert int(np.float64(unweighted[0]).view(np.uint64)) == _NA_BITS
    assert unweighted[1:] == pytest.approx([6.0, 7.0, 8.0])

    blank = np.full((2, 2), np.nan)
    assert all(_is_plain_nan(value) for value in rowWeightedMedians(blank, na_rm=True))
    assert all(_is_r_na(value) for value in rowWeightedMedians(blank, np.ones(2), na_rm=True))

    assert all(_is_plain_nan(value) for value in rowWeightedMedians(np.zeros((3, 0))))
    assert all(_is_r_na(value) for value in rowWeightedMedians(np.zeros((3, 0)), np.zeros(0)))
    assert rowWeightedMedians(np.zeros((0, 3)), np.ones(3)).size == 0
    assert all(_is_plain_nan(value) for value in colWeightedMedians(np.zeros((0, 3))))
    assert all(_is_r_na(value) for value in colWeightedMedians(np.zeros((0, 3)), np.zeros(0)))
    assert colWeightedMedians(np.zeros((4, 0)), np.ones(4)).size == 0

    signed = np.array([[-np.inf, np.inf]])
    assert int(rowWeightedMedians(signed).view(np.uint64)[0]) == 0xFFF8000000000000


def test_subscripts_follow_base_extraction():
    assert rowWeightedMedians(_X, _W, rows=[2, 4], cols=[3, 1]) == pytest.approx([8.0, 10.0])
    assert rowWeightedMedians(_X, _W, rows=-1) == pytest.approx([7.6, 8.6, 9.6])
    assert rowWeightedMedians(_X, _W, rows=-9) == pytest.approx([6.6, 7.6, 8.6, 9.6])
    assert rowWeightedMedians(_X, _W, rows=[2, 2, 1]) == pytest.approx([7.6, 7.6, 6.6])
    assert rowWeightedMedians(_X, _W, rows=0).size == 0
    assert rowWeightedMedians(_X, _W, rows=np.array([], dtype=np.int64)).size == 0
    assert rowWeightedMedians(_X, _W, rows=np.array([1.9, 2.2])) == pytest.approx([6.6, 7.6])
    assert rowWeightedMedians(_X, _W, rows=-0.2).size == 0
    missing = rowWeightedMedians(_X, _W, rows=np.array([np.nan, 2.0]))
    assert _is_r_na(missing[0])
    assert missing[1] == pytest.approx(7.6)
    assert rowWeightedMedians(_X, _W, rows=[False, True]) == pytest.approx([7.6, 9.6])
    recycled = rowWeightedMedians(_X, _W, rows=np.array([True, False, None], dtype=object))
    assert recycled[0] == pytest.approx(6.6)
    assert _is_r_na(recycled[1])
    assert recycled[2] == pytest.approx(9.6)
    assert rowWeightedMedians(_X, _W, rows=False).size == 0
    assert rowWeightedMedians(_X, np.array([1.0, 0.0, 5.0]), cols=[1, 3]) == pytest.approx(
        [7.666666666666667, 8.666666666666666, 9.666666666666666, 10.666666666666666]
    )
    assert rowWeightedMedians(_X, _W, idxs=[1, 3]) == pytest.approx([7.0, 8.0, 9.0, 10.0])

    integer_na = np.array([np.iinfo(np.int32).min, np.int32(2)], dtype=np.int32)
    from_na = rowWeightedMedians(_X, _W, rows=integer_na)
    assert _is_r_na(from_na[0])
    assert from_na[1] == pytest.approx(7.6)

    with pytest.warns(RuntimeWarning, match="NAs introduced by coercion"):
        huge = rowWeightedMedians(_X, _W, rows=np.array([1.0, 1e10]))
    assert huge[0] == pytest.approx(6.6)
    assert _is_r_na(huge[1])


def test_storage_and_argument_errors():
    integers = np.arange(1, 13).reshape((4, 3), order="F")
    assert rowWeightedMedians(integers, np.array([1, 2, 3])) == pytest.approx([6.6, 7.6, 8.6, 9.6])
    stored = np.array([[1, 3, 5], [2, 4, 6]], dtype=np.int32)
    stored[0, 0] = np.iinfo(np.int32).min
    integer_missing = rowWeightedMedians(stored, np.array([1.0, 2.0, 3.0]))
    assert _is_r_na(integer_missing[0])
    assert integer_missing[1] == pytest.approx(4.8)
    assert rowWeightedMedians(np.array([[True, True], [False, False]]), np.array([1.0, 2.0])) == pytest.approx(
        [1.0, 0.0]
    )

    with pytest.raises(ValueError, match="subscript out of bounds"):
        rowWeightedMedians(_X, _W, rows=5)
    with pytest.raises(ValueError, match="only 0's may be mixed with negative subscripts"):
        rowWeightedMedians(_X, _W, rows=[-1, 1])
    with pytest.raises(ValueError, match="logical subscript too long"):
        rowWeightedMedians(_X, _W, rows=[True, False, True, False, True])
    with pytest.raises(ValueError, match="number of columns"):
        rowWeightedMedians(_X, np.array([1.0, 2.0]))
    with pytest.raises(ValueError, match="number of rows"):
        colWeightedMedians(_X, np.array([1.0, 2.0]))
    with pytest.raises(ValueError, match="not numeric: logical"):
        rowWeightedMedians(_X, [True, True, False])
    with pytest.raises(ValueError, match="should be a matrix"):
        rowWeightedMedians(np.arange(12.0))
    with pytest.raises(ValueError, match="not 'character'"):
        rowWeightedMedians(np.array([["a", "b"], ["c", "d"]]), _W[:2])
    with pytest.raises(ValueError, match="not logical"):
        rowWeightedMedians(_X, _W, use_names="yes")
