"""Checks for weightedMad against the matrixStats 1.5.0 results."""

from __future__ import annotations

import math
import struct

import numpy as np
import pytest

from matrixstats.weightedmad import colWeightedMads, rowWeightedMads, weightedMad

_R_NA_PAYLOAD = 0x7A2


def _is_r_na(value) -> bool:
    bits = struct.unpack("<Q", struct.pack("<d", float(value)))[0]
    low = bits & 0xFFFF_FFFF
    high = bits >> 32
    return low == _R_NA_PAYLOAD and high in (0x7FF0_0000, 0x7FF8_0000)


def _matrix_1_to_12():
    # Printed layout of matrix(1:12, nrow = 3).
    return np.array(
        [[1.0, 4.0, 7.0, 10.0], [2.0, 5.0, 8.0, 11.0], [3.0, 6.0, 9.0, 12.0]]
    )


def test_unweighted_matches_mad_and_ignores_idxs():
    x = np.arange(1, 11, dtype=float)
    assert weightedMad(x) == pytest.approx(3.7065)
    assert weightedMad(x, constant=1) == pytest.approx(2.5)
    # The R source returns before it looks at idxs.
    assert weightedMad(x, idxs=np.array([1, 2, 3])) == pytest.approx(3.7065)
    assert weightedMad(np.array([1.0, 2.0, 10.0, 100.0]), low=True, constant=1) == pytest.approx(4)
    assert weightedMad(np.array([1.0, 2.0, 10.0, 100.0]), high=True, constant=1) == pytest.approx(5)
    assert weightedMad(np.arange(1, 11, dtype=float), constant=np.array([1.0, 2.0])).tolist() == pytest.approx(
        [2.5, 5.0]
    )


def test_equal_weights_and_center():
    x = np.arange(1, 11, dtype=float)
    assert weightedMad(x, np.ones(10)) == pytest.approx(3.7065)
    assert weightedMad(x, np.ones(10), center=3) == pytest.approx(3.7065000000000006)
    assert weightedMad(x, center=3) == pytest.approx(3.7065)
    # matrix(1:6, nrow=2) is read column-major, the same vector as 1:6.
    printed = np.array([[1.0, 3.0, 5.0], [2.0, 4.0, 6.0]])
    assert weightedMad(printed) == pytest.approx(2.2239)


def test_weights_drop_nonpositive_before_infinity():
    x = np.arange(1, 11, dtype=float)
    w = np.ones(10)
    w[0] = np.inf
    assert weightedMad(x, w) == pytest.approx(0.0)
    w[0] = np.inf
    w[1] = np.inf
    assert weightedMad(x, w) == pytest.approx(0.7413)
    assert _is_r_na(weightedMad(x, np.zeros(10)))
    assert weightedMad(x, np.array([-1.0, *np.ones(9)])) == pytest.approx(2.9652)
    assert weightedMad(x, np.array([-np.inf, *np.ones(9)])) == pytest.approx(2.9652)
    # -Inf is already gone, so one +Inf leaves a single observation.
    assert weightedMad(np.array([1.0, 100.0, 3.0]), np.array([np.inf, -np.inf, 1.0])) == pytest.approx(0.0)
    assert weightedMad(np.array([10.0, 1.0, 100.0]), np.array([np.inf, -np.inf, np.inf])) == pytest.approx(
        66.717
    )
    assert weightedMad(np.array([4.0, 5.0, 6.0]), np.array([0.0, 2.0, 0.0])) == pytest.approx(0.0)
    assert weightedMad(np.arange(1, 5, dtype=float), np.array([True, False, True, True])) == pytest.approx(
        1.4826
    )


def test_missing_values_and_short_inputs():
    assert _is_r_na(weightedMad(np.array([1.0, np.nan, 3.0]), np.ones(3)))
    assert weightedMad(np.array([1.0, np.nan, 3.0]), np.ones(3), na_rm=True) == pytest.approx(1.4826)
    assert _is_r_na(weightedMad(np.array([1.0, 2.0, 3.0]), np.array([1.0, np.nan, 1.0]), na_rm=True))
    # A zero weight is dropped before the missing x is seen.
    paired = np.array([1.0, np.nan, 4.0])
    assert weightedMad(paired, np.array([1.0, 0.0, 1.0])) == pytest.approx(2.2239)
    assert _is_r_na(weightedMad(np.array([], dtype=float), np.array([])))
    assert weightedMad(np.array([5.0]), w=np.array([1.0])) == pytest.approx(0.0)
    assert _is_r_na(weightedMad(np.array([1.0, np.nan, 4.0, 8.0])))
    assert weightedMad(np.array([1.0, np.nan, 4.0, 8.0]), na_rm=True) == pytest.approx(4.4478)
    assert math.isnan(weightedMad(np.arange(1, 5, dtype=float), np.ones(4), center=np.inf))


def test_indices_follow_base_subsetting():
    x = np.arange(1, 11, dtype=float)
    w = np.ones(10)
    assert weightedMad(x, w, idxs=np.array([1, 2, 3, 4])) == pytest.approx(1.4826)
    assert weightedMad(x, w, idxs=np.array([-1, -2])) == pytest.approx(2.9652)
    assert weightedMad(x, w, idxs=np.array([0, 2, 4])) == pytest.approx(1.4826)
    assert weightedMad(x, w, idxs=np.array([True, False])) == pytest.approx(2.9652)
    assert weightedMad(x, w, idxs=np.array([1.9, 4.2])) == pytest.approx(2.2239)
    assert _is_r_na(weightedMad(x, w, idxs=np.array([1, 12])))
    assert _is_r_na(weightedMad(x, w, idxs=np.array([], dtype=np.int64)))
    with pytest.raises(ValueError, match="only 0's may be mixed with negative subscripts"):
        weightedMad(x, w, idxs=np.array([1, -1]))


def test_argument_errors():
    x = np.arange(1, 5, dtype=float)
    with pytest.raises(ValueError, match="does not match: 3 != 4"):
        weightedMad(x, np.ones(3))
    with pytest.raises(ValueError, match="Argument 'constant' is not a scalar: 2"):
        weightedMad(x, np.ones(4), constant=np.array([1.0, 2.0]))
    with pytest.raises(ValueError, match="Argument 'constant' is not numeric: logical"):
        weightedMad(x, np.ones(4), constant=True)
    with pytest.raises(ValueError, match="Argument 'center' is not a scalar or NULL: 2"):
        weightedMad(x, np.ones(4), center=np.array([1.0, 2.0]))
    with pytest.raises(ValueError, match="'low' and 'high' cannot be both TRUE"):
        weightedMad(np.arange(1, 11, dtype=float), low=True, high=True)
    # An odd count never takes the low/high branch.
    assert weightedMad(np.arange(1, 6, dtype=float), low=True, high=True, constant=1) == pytest.approx(1)
    with pytest.raises(ValueError, match="partial"):
        weightedMad(np.array([], dtype=float), low=True)


def test_seeded_sample_matches_r():
    x = np.array(
        [
            -0.62645381074233242,
            0.18364332422208224,
            -0.83562861241004716,
            1.5952808021377916,
            0.32950777181536051,
            -0.82046838411801526,
            0.48742905242848528,
            0.73832470512921733,
        ]
    )
    w = np.array(
        [
            0.71761850826442242,
            0.9919060948304832,
            0.38003517943434417,
            0.77744522131979465,
            0.93470523110590875,
            0.21214252128265798,
            0.65167376608587801,
            0.12555509596131742,
        ]
    )
    assert weightedMad(x, w) == pytest.approx(0.45495347807116077)
    assert weightedMad(x) == pytest.approx(1.0117103138155799)


def test_row_and_column_margins():
    x = _matrix_1_to_12()
    assert rowWeightedMads(x).tolist() == pytest.approx([4.4478, 4.4478, 4.4478])
    assert colWeightedMads(x).tolist() == pytest.approx([1.4826, 1.4826, 1.4826, 1.4826])
    assert rowWeightedMads(x, rows=np.array([1, 3])).tolist() == pytest.approx([4.4478, 4.4478])
    assert rowWeightedMads(x, rows=np.array([-2])).tolist() == pytest.approx([4.4478, 4.4478])
    assert rowWeightedMads(x, rows=np.array([0, 1, 3])).tolist() == pytest.approx([4.4478, 4.4478])
    assert rowWeightedMads(x, w=np.array([1.0, 2.0, 3.0, 4.0])).tolist() == pytest.approx(
        [3.8124000000000007, 3.812400000000002, 3.812400000000002]
    )
    assert colWeightedMads(x, w=np.array([1.0, 2.0, 3.0])).tolist() == pytest.approx(
        [0.83025599999999999, 0.83025599999999966, 0.83025599999999966, 0.83025599999999966]
    )
    assert rowWeightedMads(x, center=np.array([2.0, 5.0, 9.0])).tolist() == pytest.approx(
        [5.1890999999999998, 4.4478, 4.4478]
    )
    assert colWeightedMads(x, center=np.array([1.0, 2.0, 3.0, 4.0])).tolist() == pytest.approx(
        [1.4826, 4.4478, 7.413, 10.3782]
    )
    assert rowWeightedMads(x, rows=np.array([1, np.nan]))[0] == pytest.approx(4.4478)
    assert _is_r_na(rowWeightedMads(x, rows=np.array([1.0, np.nan]))[1])
    assert rowWeightedMads(np.array([[1.0], [2.0], [3.0]]), w=np.array([1.0])).tolist() == pytest.approx(
        [0.0, 0.0, 0.0]
    )
    wide = np.array([[1.0, 2.0, 3.0], [4.0, 9.0, 1.0]])
    assert rowWeightedMads(wide).tolist() == pytest.approx([1.4826, 4.4478])


def test_margin_errors():
    x = _matrix_1_to_12()
    with pytest.raises(ValueError, match="subscript out of bounds"):
        rowWeightedMads(x, rows=np.array([1, 5]))
    with pytest.raises(ValueError, match="logical subscript too long"):
        rowWeightedMads(x, rows=np.array([True, False, True, True]))
    with pytest.raises(ValueError, match="scalar value is defunct"):
        rowWeightedMads(x, center=1)
    with pytest.raises(ValueError, match="number of cols"):
        colWeightedMads(x, center=1)
    with pytest.raises(ValueError, match="number of rows of 'x': 1 != 3"):
        rowWeightedMads(x, center=1, rows=np.array([1]))
    with pytest.raises(ValueError, match="number of columns of 'x': 2 != 4"):
        colWeightedMads(x, center=np.array([1.0, 2.0]))
    with pytest.raises(ValueError, match="does not match: 2 != 4"):
        rowWeightedMads(x, w=np.array([1.0, 2.0]))
    with pytest.raises(ValueError, match="invalid 'length' argument"):
        rowWeightedMads(np.arange(1, 11, dtype=float))
    with pytest.raises(ValueError, match="only 0's may be mixed"):
        rowWeightedMads(x, rows=np.array([1, -1]), center=np.array([1.0, 2.0, 3.0]))
