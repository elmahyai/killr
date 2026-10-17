"""Checks for the all, any, and any-NA wrappers."""

from __future__ import annotations

import numpy as np
import pytest

from matrixstats.rowalls import (
    allValue,
    anyValue,
    colAlls,
    colAnys,
    colAnyMissings,
    colAnyNAs,
    rowAlls,
    rowAnys,
    rowAnyMissings,
    rowAnyNAs,
)

NA = np.int32(np.iinfo(np.int32).min)


def test_manual_any_and_all_on_the_count_matrix():
    x = np.array(
        [0, 1, 2, 3, 4, 2, 3, 7, 8, 4, NA, 11],
        dtype=np.int32,
    ).reshape((4, 3), order="F")
    assert rowAnys(x, value=2).tolist() == [False, True, True, False]
    assert rowAnys(x, value=NA).tolist() == [False, False, True, False]
    assert colAnys(x, value=2).tolist() == [True, True, None]
    assert colAnys(x, value=2, na_rm=True).tolist() == [True, True, False]
    assert colAlls(x, value=2).tolist() == [False, False, False]


def test_logical_matrix_with_missing_values():
    x = np.array(
        [True, None, False, True, None, False],
        dtype=object,
    ).reshape((3, 2), order="F")
    assert rowAlls(x).tolist() == [True, None, False]
    assert rowAnys(x).tolist() == [True, None, False]
    assert rowAnyNAs(x).tolist() == [False, True, False]
    assert rowAnyMissings(x).tolist() == rowAnyNAs(x).tolist()
    assert colAnyNAs(x).tolist() == colAnyMissings(x).tolist()
    assert colAlls(x).tolist() == [False, False]
    assert rowAlls(x, value=False).tolist() == [False, None, True]
    assert anyValue(np.array([False, None, True], dtype=object)) is True
    assert allValue(np.array([True, True], dtype=bool)) is True
    assert allValue(np.array([], dtype=bool)) is True


def test_logical_value_on_a_numeric_matrix_counts_zeros():
    x = np.array([[0.0, 1.0], [np.nan, 2.0]])
    assert rowAnys(x, value=True).tolist() == [True, True]
    assert rowAnys(x, value=True, na_rm=True).tolist() == [True, True]
    assert rowAlls(x, value=True).tolist() == [False, None]
    assert rowAlls(x, value=True, na_rm=True).tolist() == [False, True]
    assert allValue(np.array([1, 2, 0]), value=True) is False
    assert allValue(np.array([1, 2, 3]), value=True) is True
    assert anyValue(np.array([1.0, np.nan])) is True
    assert allValue(np.array([NA, NA], dtype=np.int32)) is None
    assert rowAlls(np.zeros((2, 0), dtype=np.int32)).tolist() == [True, True]
    assert colAlls(np.zeros((0, 3), dtype=np.float64)).tolist() == [True, True, True]


def test_character_value_is_rejected_and_subscripts_still_apply():
    x = np.arange(1, 13, dtype=np.int32).reshape((4, 3), order="F")
    with pytest.raises(ValueError, match="numeric or a logical"):
        rowAlls(x, value="a")
    assert rowAnys(x, rows=[False, True], value=2).tolist() == [True, False]
    assert colAnyNAs(np.array([[1.0, np.nan], [2.0, 3.0]])).tolist() == [False, True]
    with pytest.raises(ValueError, match="subscript out of bounds"):
        colAnys(x, cols=[8])
