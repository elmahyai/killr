"""Checks for rowCounts, colCounts, and count."""

from __future__ import annotations

import numpy as np
import pytest

from matrixstats.rowcounts import colCounts, count, rowCounts

NA = np.int32(np.iinfo(np.int32).min)


def test_manual_integer_matrix():
    x = _manual_matrix()
    assert rowCounts(x, value=2).tolist() == [0, 1, int(NA), 0]
    assert rowCounts(x, value=2, na_rm=True).tolist() == [0, 1, 1, 0]
    assert colCounts(x, value=2).tolist() == [1, 1, int(NA)]
    assert colCounts(x, value=NA).tolist() == [0, 0, 1]
    assert colCounts(x, value=2, na_rm=True).tolist() == [1, 1, 0]
    printed = np.array(x, order="C", copy=True)
    assert rowCounts(printed, value=2).tolist() == [0, 1, int(NA), 0]
    assert rowCounts(x.ravel(order="F"), dim=(4, 3), value=2).tolist() == [0, 1, int(NA), 0]


def test_subscripts_drop_zero_exclude_negatives_and_keep_duplicates():
    x = _manual_matrix()
    assert rowCounts(x, rows=[0, 2], value=2).tolist() == [1]
    assert rowCounts(x, rows=[-1], value=1).tolist() == [1, int(NA), 0]
    duplicated = np.array([[1, 1], [1, 2]], dtype=np.int32)
    assert colCounts(duplicated, cols=[1, 1], value=1).tolist() == [2, 2]
    values = np.arange(1, 7, dtype=np.int32).reshape((2, 3), order="F")
    assert rowCounts(values, rows=[1.9], value=2).tolist() == [0]
    assert rowCounts(values, rows=[False, True], value=2).tolist() == [1]
    with pytest.raises(ValueError, match="subscript out of bounds"):
        rowCounts(values, rows=[5])
    with pytest.raises(ValueError, match="negative subscripts"):
        rowCounts(values, cols=[1, -1])
    with pytest.raises(ValueError, match="logical subscript too long"):
        colCounts(values, cols=[True, False, True, False])


def test_count_allows_an_index_past_the_end():
    assert count(np.arange(1, 6), idxs=[1, 9], value=1) is None
    assert count(np.arange(1, 6), idxs=[1, 9], value=1, na_rm=True) == 1
    assert count(np.arange(1, 6), idxs=[9], value=None) == 1
    assert count(np.array([], dtype=np.int32)) == 0
    assert count(np.array([0.0, -0.0]), value=0) == 2
    assert count(np.array([1.0, np.nan, np.nan]), value=np.nan) == 2
    assert count(np.array([1.0, np.inf, np.inf]), value=np.inf) == 2
    assert count(np.array([True, False, True]), value=2) == 2
    logical = np.array([True, False, True, True])
    assert count(np.arange(1, 4), idxs=logical) is None


def test_double_nan_and_empty_margins():
    x = np.array([[1.0, np.nan], [0.0, 2.0]])
    assert rowCounts(x, value=np.nan).tolist() == [1, 0]
    assert colCounts(x, value=0.0).tolist() == [1, int(NA)]
    assert rowCounts(np.zeros((0, 3), dtype=np.int32)).shape == (0,)
    assert colCounts(np.zeros((2, 0), dtype=np.float64)).shape == (0,)
    assert rowCounts(np.zeros((2, 0), dtype=np.int32)).tolist() == [0, 0]


def test_value_coercion_and_rejections():
    values = np.arange(1, 7).reshape((2, 3), order="F")
    with pytest.warns(UserWarning, match="integer range"):
        assert rowCounts(values, value=1e20).tolist() == [0, 0]
    with pytest.raises(ValueError, match="not a scalar"):
        rowCounts(values, value=[1, 2])
    with pytest.raises(ValueError, match="not a vector"):
        count(values)
    with pytest.raises(ValueError, match="dim."):
        rowCounts(np.arange(4.0))
    with pytest.raises(ValueError, match="TRUE or FALSE"):
        colCounts(values, na_rm=2)
    with pytest.raises(ValueError, match="character"):
        rowCounts(np.array(["a", "b"]))


def _manual_matrix():
    return np.array(
        [0, 1, 2, 3, 4, 2, 3, 7, 8, 4, NA, 11],
        dtype=np.int32,
    ).reshape((4, 3), order="F")
