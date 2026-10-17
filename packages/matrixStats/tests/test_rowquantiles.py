"""Checks for rowQuantiles and colQuantiles."""

from __future__ import annotations

import numpy as np
import pytest

from matrixstats.rowquantiles import colQuantiles, rowQuantiles

NA_INTEGER = np.iinfo(np.int32).min
_EPS = 100 * np.finfo(np.float64).eps


def _printed():
    return np.arange(1, 13).reshape((4, 3), order="F")


def test_row_and_column_quartiles_and_percentage_names():
    printed = _printed()
    rows = rowQuantiles(printed, probs=[0.25, 0.75])
    assert rows.shape == (4, 2)
    assert rows.dtype == np.float64
    assert rows.tolist() == [[3.0, 7.0], [4.0, 8.0], [5.0, 9.0], [6.0, 10.0]]
    assert rows.colnames == ("25%", "75%")
    columns = colQuantiles(printed, probs=[0.25, 0.75])
    assert columns.shape == (3, 2)
    assert columns.tolist() == [[1.75, 3.25], [5.75, 7.25], [9.75, 11.25]]
    assert columns.colnames == ("25%", "75%")
    defaults = rowQuantiles(printed)
    assert defaults.colnames == ("0%", "25%", "50%", "75%", "100%")
    assert defaults[:, 0].tolist() == [1.0, 2.0, 3.0, 4.0]
    assert defaults[:, 4].tolist() == [9.0, 10.0, 11.0, 12.0]


def test_one_row_keeps_percentage_names_and_one_probability_drops():
    printed = _printed()
    one_row = rowQuantiles(printed[:1], probs=[0.25, 0.75])
    assert one_row.shape == (2,)
    assert one_row.names == ("25%", "75%")
    assert one_row.tolist() == [3.0, 7.0]
    dropped = rowQuantiles(printed, probs=0.5)
    assert dropped.shape == (4,)
    assert dropped.names is None
    assert dropped.tolist() == [5.0, 6.0, 7.0, 8.0]
    kept = rowQuantiles(printed, probs=0.5, drop=False)
    assert kept.shape == (4, 1)
    assert kept.colnames == ("50%",)
    unnamed = rowQuantiles(printed, probs=[0.25, 0.75], use_names=False)
    assert unnamed.colnames is None
    assert rowQuantiles(printed, probs=[1 / 3], digits=2, drop=False).colnames == ("33%",)


def test_types_match_r_quantile_on_a_known_vector():
    values = np.array([[1.0, 2.0, 3.0, 4.0, 5.0, 8.0, 10.0]])
    expected = {
        1: [1.0, 2.0, 4.0, 8.0, 10.0],
        2: [1.0, 2.0, 4.0, 8.0, 10.0],
        3: [1.0, 2.0, 4.0, 5.0, 10.0],
        4: [1.0, 1.75, 3.5, 5.75, 10.0],
        5: [1.0, 2.25, 4.0, 7.25, 10.0],
        6: [1.0, 2.0, 4.0, 8.0, 10.0],
        7: [1.0, 2.5, 4.0, 6.5, 10.0],
        8: [1.0, 2.166666666666667, 4.0, 7.499999999999999, 10.0],
        9: [1.0, 2.1875, 4.0, 7.4375, 10.0],
    }
    probs = [0.0, 0.25, 0.5, 0.75, 1.0]
    for choice, want in expected.items():
        got = rowQuantiles(values, probs=probs, type=choice)
        assert got.shape == (5,)
        assert np.allclose(got, want, atol=1e-8, rtol=0.0)


def test_missing_row_is_nan_until_na_rm_drops_it():
    printed = _printed().astype(float)
    printed[1, 1] = np.nan
    blocked = rowQuantiles(printed, probs=[0.25, 0.75], na_rm=False)
    assert np.isnan(blocked[1]).all()
    assert blocked[0].tolist() == [3.0, 7.0]
    removed = rowQuantiles(printed, probs=[0.25, 0.75], na_rm=True)
    assert removed[1].tolist() == [4.0, 8.0]
    integers = _printed().astype(np.int32)
    integers[1, 1] = NA_INTEGER
    assert np.isnan(rowQuantiles(integers, probs=[0.25, 0.75])[1]).all()
    assert rowQuantiles(integers, probs=[0.25, 0.75], na_rm=True, type=1)[1].tolist() == [
        2.0,
        10.0,
    ]


def test_subscripts_are_one_based_and_follow_r_rules():
    printed = _printed()
    assert rowQuantiles(printed, rows=[3, 1], probs=[0.25, 0.75]).tolist() == [
        [5.0, 9.0],
        [3.0, 7.0],
    ]
    assert rowQuantiles(printed, cols=[3, 1], probs=[0.25, 0.75]).tolist() == [
        [3.0, 7.0],
        [4.0, 8.0],
        [5.0, 9.0],
        [6.0, 10.0],
    ]
    assert rowQuantiles(printed, rows=-2, probs=0.5).tolist() == [5.0, 7.0, 8.0]
    assert rowQuantiles(printed, rows=[0, 2, 0, 4], probs=0.5).tolist() == [6.0, 8.0]
    assert rowQuantiles(printed, rows=[True, False], probs=0.5).tolist() == [5.0, 7.0]
    assert rowQuantiles(printed, rows=2.9, probs=0.5).tolist() == [6.0]
    assert np.isnan(rowQuantiles(printed, rows=[1, None], probs=0.5)[1])
    both = rowQuantiles(printed, rows=[2, 4], cols=[1, 3], probs=[0.25, 0.75])
    assert both.tolist() == [[4.0, 8.0], [6.0, 10.0]]


def test_empty_margins_and_logical_values():
    assert rowQuantiles(np.zeros((0, 0)), probs=[0.25, 0.75]).shape == (0, 2)
    assert np.isnan(rowQuantiles(np.zeros((2, 0)), probs=[0.25, 0.75])).all()
    assert colQuantiles(np.zeros((0, 2)), probs=[0.25, 0.75]).shape == (2, 2)
    assert np.isnan(colQuantiles(np.zeros((0, 2)), probs=[0.25, 0.75])).all()
    empty_int = rowQuantiles(np.zeros((2, 0), dtype=np.int32), type=1, probs=[0.25, 0.75])
    assert empty_int.dtype == np.int32
    assert np.all(empty_int == NA_INTEGER)
    assert rowQuantiles(np.zeros((0, 2), dtype=np.int32), type=7).dtype == np.float64
    logical = np.array([[True, True, True], [False, False, True]])
    assert rowQuantiles(logical, probs=[0.25, 0.75]).tolist() == [[1.0, 1.0], [0.0, 0.5]]


def test_many_probabilities_use_the_common_percentage_format():
    printed = _printed()
    names = rowQuantiles(printed, probs=np.linspace(0.0, 1.0, 100), drop=False).colnames
    assert names[0] == "0.000000%"
    assert names[1] == "1.010101%"
    assert names[-1] == "100.000000%"
    assert len(names) == 100


def test_errors_for_range_type_and_subscripts():
    printed = _printed()
    with pytest.raises(ValueError, match="should be a matrix"):
        rowQuantiles(np.arange(4))
    with pytest.raises(ValueError, match="character"):
        rowQuantiles(np.array([["a", "b"], ["c", "d"]]))
    with pytest.raises(ValueError, match="missing values"):
        rowQuantiles(printed, probs=[0.25, np.nan])
    with pytest.raises(ValueError, match="out of range"):
        rowQuantiles(printed, probs=[-1e-13])
    with pytest.raises(ValueError, match="partial"):
        rowQuantiles(printed, probs=[-_EPS / 2])
    with pytest.raises(ValueError, match="type"):
        rowQuantiles(printed, type=0)
    with pytest.raises(ValueError, match="missing value"):
        rowQuantiles(printed, type=np.nan)
    with pytest.raises(ValueError, match="subscript out of bounds"):
        rowQuantiles(printed, rows=5)
    with pytest.raises(ValueError, match="negative subscripts"):
        rowQuantiles(printed, cols=[-1, 1])
    with pytest.raises(ValueError, match="digits"):
        rowQuantiles(printed, digits=0)
    assert rowQuantiles(printed, probs=0.25, use_names=False, digits=0).tolist() == [
        3.0,
        4.0,
        5.0,
        6.0,
    ]
