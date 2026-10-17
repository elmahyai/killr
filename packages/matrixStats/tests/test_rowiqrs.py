"""Checks for rowIQRs and colIQRs."""

from __future__ import annotations

import numpy as np
import pytest

from matrixstats.rowiqrs import colIQRs, rowIQRs

NA_INTEGER = np.iinfo(np.int32).min


def _printed():
    return np.arange(1, 13).reshape((4, 3), order="F")


def test_row_and_column_ranges_are_the_quartile_gap():
    printed = _printed()
    assert rowIQRs(printed).tolist() == [4.0, 4.0, 4.0, 4.0]
    assert colIQRs(printed).tolist() == [1.5, 1.5, 1.5]
    assert rowIQRs(printed).dtype == np.float64
    assert rowIQRs(printed, rows=[4, 1]).tolist() == [4.0, 4.0]
    assert colIQRs(printed, cols=[3, 1]).tolist() == [1.5, 1.5]


def test_missing_row_and_na_rm():
    printed = _printed().astype(float)
    printed[1, 0] = np.nan
    blocked = rowIQRs(printed, na_rm=False)
    assert blocked[0] == 4.0
    assert np.isnan(blocked[1])
    assert blocked[2] == 4.0
    removed = rowIQRs(printed, na_rm=True)
    assert removed.tolist() == [4.0, 2.0, 4.0, 4.0]
    integers = _printed().astype(np.int32)
    integers[1, 1] = NA_INTEGER
    assert np.isnan(rowIQRs(integers)[1])
    assert colIQRs(integers, na_rm=True)[1] == pytest.approx(1.5)


def test_type_changes_the_quartile_gap():
    printed = _printed().astype(np.int32)
    assert rowIQRs(printed, type=1).tolist() == [8.0, 8.0, 8.0, 8.0]
    assert rowIQRs(printed, type=7).tolist() == [4.0, 4.0, 4.0, 4.0]


def test_empty_integer_margin_stays_the_integer_sentinel():
    gap = rowIQRs(np.zeros((2, 0), dtype=np.int32), type=1)
    assert gap.dtype == np.int32
    assert gap.shape == (2,)
    assert np.all(gap == NA_INTEGER)
    assert rowIQRs(np.zeros((0, 0), dtype=np.int32), type=1).dtype == np.int32
    assert rowIQRs(np.zeros((2, 0), dtype=np.int32), type=7).dtype == np.float64
    columns = colIQRs(np.zeros((0, 3), dtype=np.int32), type=1)
    assert columns.dtype == np.int32
    assert columns.shape == (3,)
    assert np.all(columns == NA_INTEGER)


def test_one_column_range_is_zero_and_bad_digits_still_error():
    assert rowIQRs(np.arange(1, 5).reshape(4, 1)).tolist() == [0.0, 0.0, 0.0, 0.0]
    assert colIQRs(np.arange(1, 5).reshape(1, 4)).tolist() == [0.0, 0.0, 0.0, 0.0]
    with pytest.raises(ValueError, match="digits"):
        rowIQRs(_printed(), digits=0)
    assert rowIQRs(_printed(), use_names=False, digits=0).tolist() == [4.0, 4.0, 4.0, 4.0]
