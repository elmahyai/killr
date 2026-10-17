"""Checks for iqr."""

from __future__ import annotations

import math

import numpy as np
import pytest

from matrixstats.iqr import iqr

NA_INTEGER = np.iinfo(np.int32).min


def test_vector_range_matches_the_quartile_gap():
    assert iqr(np.arange(1, 11)) == pytest.approx(4.5)
    assert iqr(list(range(1, 11))) == pytest.approx(4.5)
    assert iqr(np.arange(1, 11), type=1) == pytest.approx(5.0)
    assert iqr(np.arange(1, 11), idxs=[1, 2, 3, 4]) == pytest.approx(1.5)
    assert iqr(np.arange(1, 7), idxs=[0, 2, 0, 4]) == pytest.approx(1.0)
    assert iqr(np.arange(1, 11), idxs=[-1, -2]) == pytest.approx(3.5)
    assert iqr(np.arange(1, 7), idxs=[True, False]) == pytest.approx(2.0)


def test_matrix_is_read_column_major():
    printed = np.arange(1, 13).reshape((4, 3), order="F")
    assert iqr(printed) == pytest.approx(5.5)
    c_order = np.array([[1, 5, 9], [2, 6, 10], [3, 7, 11], [4, 8, 12]])
    assert iqr(c_order) == pytest.approx(5.5)


def test_missing_empty_and_scalar():
    assert math.isnan(iqr(np.array([], dtype=float)))
    assert math.isnan(iqr(np.array([], dtype=np.int32)))
    assert iqr(5) == 0.0
    assert iqr(np.int32(5)) == 0.0
    assert math.isnan(iqr(np.array([1.0, np.nan, 3.0])))
    assert iqr(np.array([1.0, np.nan, 3.0]), na_rm=True) == pytest.approx(1.0)
    integers = np.array([1, NA_INTEGER, 4], dtype=np.int32)
    assert math.isnan(iqr(integers))
    assert iqr(integers, na_rm=True) == pytest.approx(1.5)
    printed = np.arange(1, 13, dtype=float).reshape((4, 3), order="F")
    printed[0, 0] = np.nan
    assert math.isnan(iqr(printed, na_rm=False))
    assert math.isfinite(iqr(printed, na_rm=True))


def test_subscript_errors():
    with pytest.raises(ValueError, match="subscript out of bounds"):
        iqr(np.arange(1, 6), idxs=6)
    with pytest.raises(ValueError, match="negative subscripts"):
        iqr(np.arange(1, 6), idxs=[-1, 2])
