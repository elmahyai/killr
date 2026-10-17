"""Checks for rowMads and colMads, including a comparison with R."""

from __future__ import annotations

import shutil
import subprocess
import textwrap

import numpy as np
import pytest

from matrixstats.rowmads import colMads, rowMads

TOL = 1e-8
NA_INTEGER = np.iinfo(np.int32).min
NA_REAL_BITS = np.uint64(0x7FF00000000007A2)


def test_printed_matrix_and_column_major_vector():
    printed = np.arange(1, 13).reshape((4, 3), order="F")
    rows = rowMads(printed)
    cols = colMads(printed)
    assert rows.dtype == np.float64
    assert rows.shape == (4,)
    assert cols.shape == (3,)
    assert rowMads(np.arange(1, 13), dim=(4, 3)).tolist() == rows.tolist()
    assert rowMads(np.array(printed, order="C")).tolist() == rows.tolist()
    assert colMads(np.asfortranarray(printed)).tolist() == cols.tolist()
    assert rowMads(printed, constant=1.0).tolist() == [4.0, 4.0, 4.0, 4.0]


def test_double_rows_columns_and_subsets():
    printed = np.array([1.0, 2.0, 3.0, 4.0, 10.0, 20.0, 30.0, 40.0]).reshape((2, 4), order="F")
    rows = rowMads(printed, constant=1.0)
    assert rows.tolist() == [4.5, 9.0]
    cols = colMads(printed, constant=1.0)
    assert cols.tolist() == [0.5, 0.5, 5.0, 5.0]
    assert rowMads(printed, rows=[0, 2], constant=1.0).tolist() == [9.0]
    assert rowMads(printed, cols=[-2], constant=1.0).tolist() == [4.5 * 2, 9.0 * 2]
    assert rowMads(printed, rows=[2], cols=[1, 3, 4], constant=1.0).shape == (1,)
    assert colMads(printed, rows=[True, False], constant=1.0).tolist() == [0.0, 0.0, 0.0, 0.0]


def test_missing_values_use_r_na_and_one_observation_is_zero():
    na = np.array(np.uint64(NA_REAL_BITS).view(np.float64))
    present = rowMads(np.array([[1.0, na, 2.0]]))
    assert present.view(np.uint64)[0] == NA_REAL_BITS
    plain = rowMads(np.array([[1.0, np.nan, 2.0]]))
    assert plain.view(np.uint64)[0] == NA_REAL_BITS
    kept = rowMads(np.array([[1.0, na, 3.0]]), na_rm=True, constant=1.0)
    assert kept.tolist() == [1.0]
    assert rowMads(np.array([[5.0]])).view(np.uint64)[0] == np.uint64(0)
    assert rowMads(np.array([[np.inf]])).tolist() == [0.0]
    empty = rowMads(np.zeros((2, 0)))
    assert empty.shape == (2,)
    assert np.all(empty.view(np.uint64) == NA_REAL_BITS)
    assert rowMads(np.zeros((0, 3))).shape == (0,)
    dropped = rowMads(np.array([[na, na]]), na_rm=True)
    assert dropped.view(np.uint64)[0] == NA_REAL_BITS


def test_integer_even_center_wraps_and_odd_difference_uses_double():
    assert rowMads(np.array([[1, 3, 5, 7]], dtype=np.int32), constant=1.0).tolist() == [2.0]
    assert rowMads(np.array([[1, 2, 4, 7]], dtype=np.int32), constant=1.0).tolist() == [1.5]
    big = rowMads(np.array([[2_000_000_000, 2_000_000_002]], dtype=np.int32), constant=1.0)
    assert big.tolist() == [2_147_483_647.0]
    four = rowMads(
        np.array([[2_000_000_000, 2_000_000_001, 2_000_000_002, 2_000_000_003]], dtype=np.int32),
        constant=1.0,
    )
    assert four.tolist() == [1.0]
    ina = np.array([1, NA_INTEGER, 3, 5, 7, 9], dtype=np.int32).reshape((2, 3), order="F")
    got = rowMads(ina)
    assert np.isfinite(got[0])
    assert got.view(np.uint64)[1] == np.uint64(NA_REAL_BITS)
    assert np.isfinite(rowMads(ina, na_rm=True)).all()


def test_center_subtracts_then_scales_the_median():
    printed = np.array([1.0, 2.0, 3.0, 4.0, 10.0, 20.0, 30.0, 40.0]).reshape((2, 4), order="F")
    assert rowMads(printed, center=[2.0, 3.0]).shape == (2,)
    assert rowMads(np.array([[5.0]]), center=[2.0]).tolist() == pytest.approx([1.4826 * 3.0])
    na = np.array(np.uint64(NA_REAL_BITS).view(np.float64))
    centered = rowMads(np.array([[1.0, na, 5.0]]), center=[1.0])
    assert centered.view(np.uint64)[0] == np.uint64(0x7FF80000000007A2)
    empty = rowMads(np.array([[na, na]]), center=[0.0], na_rm=True)
    assert empty.view(np.uint64)[0] == np.uint64(0x7FF8000000000000)
    ints = np.arange(1, 7, dtype=np.int32).reshape((2, 3), order="F")
    assert rowMads(ints, center=[1.5, 2.5], constant=1.0).tolist() == [1.5, 1.5]


def test_integer_center_overflow_is_missing_only_down_rows():
    values = np.array([2_000_000_000, 1, -2_000_000_000, 2], dtype=np.int32).reshape((2, 2), order="F")
    rows = rowMads(values, center=np.array([-2_000_000_000, 0], dtype=np.int32), constant=1.0)
    assert rows.view(np.uint64)[0] == np.uint64(0x7FF80000000007A2)
    assert rows[1] == 1.5
    cols = colMads(
        values,
        center=np.array([2_000_000_000, -2_000_000_000], dtype=np.int32),
        constant=1.0,
    )
    assert np.isfinite(cols).all()


def test_rejects_bad_arguments():
    printed = np.arange(1, 13).reshape((4, 3), order="F")
    with pytest.raises(ValueError, match="cannot be logical"):
        rowMads(np.array([[True, False]]))
    with pytest.raises(ValueError, match="subscript out of bounds"):
        rowMads(printed, rows=[5])
    with pytest.raises(ValueError, match="negative subscripts"):
        colMads(printed, cols=[-1.0, 1.0])
    with pytest.raises(ValueError, match="logical subscript too long"):
        rowMads(printed, rows=[True, False, True, False, True])
    with pytest.raises(ValueError, match="defunct"):
        rowMads(printed, center=1)
    with pytest.raises(ValueError, match="1 != 2"):
        colMads(np.arange(6).reshape(3, 2), center=1)
    with pytest.raises(ValueError, match="2 != 4"):
        rowMads(printed, center=[1, 2])
    with pytest.raises(ValueError, match="TRUE or FALSE"):
        rowMads(printed, na_rm=2)
    with pytest.raises(ValueError, match="must be a logical"):
        colMads(printed, use_names=1.5)
    with pytest.raises(ValueError, match="dim."):
        rowMads(np.arange(5), dim=(2, 3))
    with pytest.raises(ValueError, match="character"):
        rowMads(np.array(["a", "b"]))
    assert rowMads(printed, na_rm=0).tolist() == rowMads(printed).tolist()
    assert rowMads(printed, rows=1).shape == (1,)


def test_matches_r_on_mads_centers_and_missing_values():
    if shutil.which("Rscript") is None:
        pytest.skip("Rscript is unavailable")
    reference = _r_suite()
    if reference is None:
        pytest.skip("matrixStats is unavailable")

    printed = np.array([1.0, 2.0, 3.0, 4.0, 10.0, 20.0, 30.0, 40.0]).reshape((2, 4), order="F")
    _assert_match(rowMads(printed), reference["rows"])
    _assert_match(colMads(printed), reference["cols"])
    matrix = np.arange(1, 13).reshape((4, 3), order="F")
    _assert_match(rowMads(matrix), reference["mads"])
    _assert_match(colMads(matrix), reference["cmads"])
    _assert_match(rowMads(np.arange(1, 13), dim=(4, 3)), reference["dimv12"])

    na = np.array(np.uint64(NA_REAL_BITS).view(np.float64))
    _assert_match(rowMads(np.array([[1.0, na, 2.0]])), reference["na"])
    _assert_match(rowMads(np.array([[1.0, np.nan, 2.0]])), reference["nan"])
    _assert_match(rowMads(np.array([[1.0, na, 3.0]]), na_rm=True), reference["na_rm"])
    _assert_match(rowMads(np.array([[5.0]])), reference["one"])
    _assert_match(rowMads(np.zeros((2, 0))), reference["empty"])
    _assert_match(rowMads(np.array([[na, na]]), na_rm=True), reference["all_na_rm"])
    _assert_match(rowMads(np.array([[np.inf]])), reference["one_inf"])

    _assert_match(
        rowMads(np.array([[1, 3, 5, 7]], dtype=np.int32), constant=1),
        reference["int_mu"],
    )
    _assert_match(
        rowMads(np.array([[2_000_000_000, 2_000_000_002]], dtype=np.int32), constant=1),
        reference["big"],
    )
    _assert_match(
        rowMads(
            np.array([[2_000_000_000, 2_000_000_001, 2_000_000_002, 2_000_000_003]], dtype=np.int32),
            constant=1,
        ),
        reference["four_big"],
    )
    _assert_match(
        rowMads(np.array([[-5, -1, 2, 8]], dtype=np.int32), constant=1),
        reference["neg_int"],
    )
    ina = np.array([1, NA_INTEGER, 3, 5, 7, 9], dtype=np.int32).reshape((2, 3), order="F")
    _assert_match(rowMads(ina), reference["int_na"])
    _assert_match(rowMads(ina, na_rm=True), reference["int_na_rm"])

    _assert_match(rowMads(printed, center=[2.0, 3.0]), reference["center"])
    _assert_match(colMads(printed, center=[10.0, 30.0, 5.0, 7.0]), reference["center_col"])
    _assert_match(rowMads(printed, rows=2, cols=[1, 3, 4]), reference["subset"])
    _assert_match(rowMads(printed, cols=-2), reference["neg"])
    _assert_match(rowMads(printed, rows=[0, 1]), reference["zero"])
    _assert_match(rowMads(printed, constant=2), reference["const2"])
    _assert_match(rowMads(np.arange(1, 9), dim=(2, 4)), reference["dimv"])
    pair = np.array([1.0, na, 3.0, 4.0]).reshape((2, 2), order="F")
    _assert_match(colMads(pair), reference["col_na"])
    _assert_match(colMads(pair, na_rm=True), reference["col_na_rm"])
    _assert_match(rowMads(np.array([[1.0, na, 5.0]]), center=[1.0]), reference["center_na"])
    _assert_match(
        rowMads(np.array([[na, na]]), center=[0.0], na_rm=True),
        reference["center_empty"],
    )
    _assert_match(rowMads(np.array([[5.0]]), center=[2.0]), reference["center_one"])
    _assert_match(rowMads(np.arange(1, 7).reshape((3, 2), order="F"), rows=[True, None, False]), reference["lgl"])
    _assert_match(rowMads(printed, rows=1.9), reference["frac"])
    _assert_match(rowMads(np.array([[1.0, 5.0, 9.0]]), cols=[1, 1, 1]), reference["dup"])
    _assert_match(rowMads(np.array([[1.0, np.inf, 3.0, 4.0]]), constant=1), reference["inf"])
    na_const = np.array(np.uint64(NA_REAL_BITS).view(np.float64))
    _assert_match(rowMads(np.array([[1.0, 2.0, 3.0, 4.0]]), constant=na_const), reference["const_na"])
    overflow = np.array([2_000_000_000, 1, -2_000_000_000, 2], dtype=np.int32).reshape((2, 2), order="F")
    _assert_match(
        rowMads(overflow, center=np.array([-2_000_000_000, 0], dtype=np.int32), constant=1),
        reference["ov_row"],
    )
    _assert_match(
        colMads(overflow, center=np.array([2_000_000_000, -2_000_000_000], dtype=np.int32), constant=1),
        reference["ov_col"],
    )
    ints = np.arange(1, 7, dtype=np.int32).reshape((2, 3), order="F")
    _assert_match(rowMads(ints, center=[1.5, 2.5], constant=1), reference["dbl_center"])
    _assert_match(rowMads(np.arange(1, 7).reshape((3, 2), order="F"), rows=1, center=[1, 2, 3]), reference["center_before"])
    _assert_match(rowMads(np.arange(1, 7).reshape((3, 2), order="F"), rows=[]), reference["empty_rows"])
    _assert_match(rowMads(np.arange(1, 7).reshape((3, 2), order="F"), cols=[0, 2]), reference["cols02"])
    _assert_match(rowMads(np.array([[1.0, 1.0, 2.0, 2.0]]), constant=1), reference["ties"])
    _assert_match(rowMads(np.array([[-np.inf, 0.0, np.inf]]), constant=1), reference["infs"])
    _assert_match(rowMads(matrix, rows=[3, 0, 1]), reference["rows_idx"])
    _assert_match(colMads(matrix, rows=[2], cols=[3, 1]), reference["col_sub"])


def _assert_match(actual, expected):
    actual = np.asarray(actual)
    kind, values = expected
    values = np.asarray(values).reshape(-1)
    actual = actual.reshape(-1)
    assert actual.shape == values.shape
    assert actual.dtype == np.float64
    assert kind == "double"
    for got, want in zip(actual, values):
        if not np.isfinite(want) or not np.isfinite(got):
            assert got.view(np.uint64) == want.view(np.uint64)
        else:
            assert abs(float(got) - float(want)) <= TOL


def _r_suite():
    script = textwrap.dedent(
        r"""
        if (!requireNamespace("matrixStats", quietly=TRUE)) quit(status=2)
        emit <- function(name, values) {
          mat <- as.matrix(values)
          cat(name, "\n", "double", "\n", nrow(mat), " ", ncol(mat), "\n", sep="")
          raw <- writeBin(as.double(as.vector(mat)), raw())
          if (length(raw)) cat(sprintf("%02x", as.integer(raw)), sep="\n")
          cat("---\n")
        }
        x <- matrix(c(1, 2, 3, 4, 10, 20, 30, 40), nrow=2)
        emit("rows", matrixStats::rowMads(x))
        emit("cols", matrixStats::colMads(x))
        m <- matrix(1:12, nrow=4)
        emit("mads", matrixStats::rowMads(m))
        emit("cmads", matrixStats::colMads(m))
        emit("dimv12", matrixStats::rowMads(1:12, dim.=c(4, 3)))
        emit("na", matrixStats::rowMads(matrix(c(1, NA, 2), nrow=1)))
        emit("nan", matrixStats::rowMads(matrix(c(1, NaN, 2), nrow=1)))
        emit("na_rm", matrixStats::rowMads(matrix(c(1, NA, 3), nrow=1), na.rm=TRUE))
        emit("one", matrixStats::rowMads(matrix(5, nrow=1)))
        emit("empty", matrixStats::rowMads(matrix(numeric(0), nrow=2, ncol=0)))
        emit("all_na_rm", matrixStats::rowMads(matrix(c(NA_real_, NA_real_), nrow=1), na.rm=TRUE))
        emit("one_inf", matrixStats::rowMads(matrix(Inf, nrow=1)))
        emit("int_mu", matrixStats::rowMads(matrix(as.integer(c(1, 3, 5, 7)), nrow=1), constant=1))
        emit("big", matrixStats::rowMads(matrix(as.integer(c(2000000000, 2000000002)), nrow=1), constant=1))
        emit("four_big", matrixStats::rowMads(matrix(as.integer(c(2000000000, 2000000001, 2000000002, 2000000003)), nrow=1), constant=1))
        emit("neg_int", matrixStats::rowMads(matrix(as.integer(c(-5, -1, 2, 8)), nrow=1), constant=1))
        emit("int_na", matrixStats::rowMads(matrix(as.integer(c(1, NA, 3, 5, 7, 9)), nrow=2)))
        emit("int_na_rm", matrixStats::rowMads(matrix(as.integer(c(1, NA, 3, 5, 7, 9)), nrow=2), na.rm=TRUE))
        emit("center", matrixStats::rowMads(x, center=c(2, 3)))
        emit("center_col", matrixStats::colMads(x, center=c(10, 30, 5, 7)))
        emit("subset", matrixStats::rowMads(x, rows=2, cols=c(1, 3, 4)))
        emit("neg", matrixStats::rowMads(x, cols=-2))
        emit("zero", matrixStats::rowMads(x, rows=c(0, 1)))
        emit("const2", matrixStats::rowMads(x, constant=2))
        emit("dimv", matrixStats::rowMads(1:8, dim.=c(2, 4)))
        emit("col_na", matrixStats::colMads(matrix(c(1, NA, 3, 4), nrow=2)))
        emit("col_na_rm", matrixStats::colMads(matrix(c(1, NA, 3, 4), nrow=2), na.rm=TRUE))
        emit("center_na", matrixStats::rowMads(matrix(c(1, NA, 5), nrow=1), center=1))
        emit("center_empty", matrixStats::rowMads(matrix(c(NA, NA), nrow=1), center=0, na.rm=TRUE))
        emit("center_one", matrixStats::rowMads(matrix(5, nrow=1), center=2))
        emit("lgl", matrixStats::rowMads(matrix(1:6, nrow=3), rows=c(TRUE, NA, FALSE)))
        emit("frac", matrixStats::rowMads(x, rows=1.9))
        emit("dup", matrixStats::rowMads(matrix(c(1, 5, 9), nrow=1), cols=c(1, 1, 1)))
        emit("inf", matrixStats::rowMads(matrix(c(1, Inf, 3, 4), nrow=1), constant=1))
        emit("const_na", matrixStats::rowMads(matrix(c(1, 2, 3, 4), nrow=1), constant=NA_real_))
        ov <- matrix(as.integer(c(2000000000, 1, -2000000000, 2)), nrow=2)
        emit("ov_row", suppressWarnings(matrixStats::rowMads(ov, center=as.integer(c(-2000000000, 0)), constant=1)))
        emit("ov_col", matrixStats::colMads(ov, center=as.integer(c(2000000000, -2000000000)), constant=1))
        emit("dbl_center", matrixStats::rowMads(matrix(as.integer(1:6), nrow=2), center=c(1.5, 2.5), constant=1))
        emit("center_before", matrixStats::rowMads(matrix(1:6, nrow=3), rows=1, center=c(1, 2, 3)))
        emit("empty_rows", matrixStats::rowMads(matrix(1:6, nrow=3), rows=integer(0)))
        emit("cols02", matrixStats::rowMads(matrix(1:6, nrow=3), cols=c(0, 2)))
        emit("ties", matrixStats::rowMads(matrix(c(1, 1, 2, 2), nrow=1), constant=1))
        emit("infs", matrixStats::rowMads(matrix(c(-Inf, 0, Inf), nrow=1), constant=1))
        emit("rows_idx", matrixStats::rowMads(m, rows=c(3, 0, 1)))
        emit("col_sub", matrixStats::colMads(m, rows=2, cols=c(3, 1)))
        """
    )
    result = subprocess.run(
        ["Rscript", "-e", script],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode == 2:
        return None
    if result.returncode != 0:
        raise RuntimeError(result.stderr)
    return _parse_blocks(result.stdout)


def _parse_blocks(text: str):
    parsed = {}
    for chunk in text.split("---\n"):
        lines = [line for line in chunk.splitlines() if line != ""]
        if not lines:
            continue
        name = lines[0]
        kind = lines[1]
        nrow, ncol = (int(part) for part in lines[2].split())
        raw = bytes(int(line, 16) for line in lines[3:])
        values = np.frombuffer(raw, dtype="<f8").reshape((nrow, ncol), order="F")
        parsed[name] = (kind, np.array(values, copy=True))
    return parsed
