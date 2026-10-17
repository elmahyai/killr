"""Checks for rowCummins and colCummins, including a comparison with R."""

from __future__ import annotations

import shutil
import subprocess
import textwrap

import numpy as np
import pytest

from matrixstats.rowcummins import colCummins, rowCummins

TOL = 1e-8
NA_INTEGER = np.iinfo(np.int32).min


def test_printed_matrix_matches_column_major_storage():
    printed = np.array(
        [[1, 5, 9], [2, 6, 10], [3, 7, 11], [4, 8, 12]], dtype=np.int32
    )
    rows = rowCummins(printed)
    cols = colCummins(printed)
    assert rows.dtype == np.int32
    assert rows.shape == (4, 3)
    assert rows.tolist() == [[1, 1, 1], [2, 2, 2], [3, 3, 3], [4, 4, 4]]
    assert cols.tolist() == [[1, 5, 9], [1, 5, 9], [1, 5, 9], [1, 5, 9]]

    flat = np.arange(1, 13)
    assert rowCummins(flat, dim=(4, 3)).tolist() == rows.tolist()
    assert colCummins(flat, dim=(4, 3)).tolist() == cols.tolist()

    fortran = np.asfortranarray(printed)
    assert rowCummins(fortran).tolist() == rows.tolist()
    assert colCummins(fortran).tolist() == cols.tolist()


def test_logical_input_returns_integer():
    printed = np.array([[True, False, True], [True, True, False]])
    got = rowCummins(printed)
    assert got.dtype == np.int32
    assert got.tolist() == [[1, 0, 0], [1, 1, 0]]
    assert colCummins(printed).tolist() == [[1, 0, 1], [1, 0, 0]]


def test_rows_subset_drops_zeros_and_keeps_order():
    printed = _printed_1_to_12()
    got = rowCummins(printed, rows=[3, 0, 0, 1])
    assert got.shape == (2, 3)
    assert got.tolist() == [[3, 3, 3], [1, 1, 1]]
    down = colCummins(printed, rows=[3, 1])
    assert down.tolist() == [[3, 7, 11], [1, 5, 9]]
    assert rowCummins(printed, cols=[3, 1]).tolist() == [
        [9, 1],
        [10, 2],
        [11, 3],
        [12, 4],
    ]


def test_negative_rows_and_logical_columns():
    printed = _printed_1_to_12()
    assert rowCummins(printed, rows=[-4, 0, 0, -3, -1]).tolist() == [[2, 2, 2]]
    assert rowCummins(printed, rows=[False, True]).tolist() == [[2, 2, 2], [4, 4, 4]]
    assert colCummins(printed, cols=[2, 2]).shape == (4, 2)


def test_missing_double_stops_the_cumulative_minimum():
    printed = np.array(
        [[1.0, np.nan, 9.0], [2.0, 6.0, 10.0], [4.0, 1.0, 5.0]],
        order="C",
    )
    rows = rowCummins(printed)
    assert rows[0, 0] == 1.0
    assert np.isnan(rows[0, 1]) and np.isnan(rows[0, 2])
    assert rows[1].tolist() == [2.0, 2.0, 2.0]
    assert rows[2].tolist() == [4.0, 1.0, 1.0]

    cols = colCummins(printed)
    assert cols[:, 0].tolist() == [1.0, 1.0, 1.0]
    assert np.isnan(cols[:, 1]).all()
    assert cols[:, 2].tolist() == [9.0, 9.0, 5.0]

    subset = rowCummins(printed, rows=[3, 1])
    assert subset.tolist()[0] == [4.0, 1.0, 1.0]
    assert subset[1, 0] == 1.0
    assert np.isnan(subset[1, 1]) and np.isnan(subset[1, 2])


def test_integer_na_propagates():
    na = NA_INTEGER
    printed = np.array([[1, 3, na], [na, 2, 0], [4, 1, 5]], dtype=np.int32)
    rows = rowCummins(printed)
    assert rows.dtype == np.int32
    assert rows[0, 0] == 1 and rows[0, 1] == 1 and rows[0, 2] == na
    assert np.all(rows[1] == na)
    assert rows[2].tolist() == [4, 1, 1]
    cols = colCummins(printed)
    assert cols[0, 0] == 1 and cols[1, 0] == na and cols[2, 0] == na
    assert cols[:, 1].tolist() == [3, 2, 1]
    assert np.all(cols[:, 2] == na)


def test_empty_margins_keep_their_shape():
    assert rowCummins(np.zeros((0, 0), dtype=float)).shape == (0, 0)
    assert colCummins(np.zeros((3, 0), dtype=np.int32)).shape == (3, 0)
    assert rowCummins(np.zeros((0, 4), dtype=float)).shape == (0, 4)
    assert rowCummins(_printed_1_to_12(), rows=[]).shape == (0, 3)
    assert colCummins(_printed_1_to_12(), cols=[]).shape == (4, 0)


def test_use_names_is_accepted_and_returns_a_plain_matrix():
    values = rowCummins(_printed_1_to_12().astype(float), use_names=False)
    assert values.dtype == np.float64
    assert values[0].tolist() == [1.0, 1.0, 1.0]


def test_dim_reinterprets_column_major_storage():
    printed = _printed_1_to_12()
    got = rowCummins(printed, dim=(6, 2))
    assert got.shape == (6, 2)
    assert got[0].tolist() == [1, 1]
    assert got[5].tolist() == [6, 6]


def test_infinities_and_equal_values():
    values = np.array([[np.inf, 1.0, -np.inf]])
    assert rowCummins(values).tolist() == [[np.inf, 1.0, -np.inf]]
    tied = np.array([[5.0, 5.0, 4.0], [3.0, 3.0, 9.0]])
    assert rowCummins(tied).tolist() == [[5.0, 5.0, 4.0], [3.0, 3.0, 3.0]]


def test_rejects_bad_dim_flags_and_subscripts():
    with pytest.raises(ValueError, match="dim."):
        rowCummins(np.arange(4.0), dim=(2, 3))
    with pytest.raises(ValueError, match="TRUE or FALSE"):
        rowCummins(_printed_1_to_12(), use_names=1)
    with pytest.raises(ValueError, match="subscript out of bounds"):
        rowCummins(_printed_1_to_12(), rows=[5])
    with pytest.raises(ValueError, match="negative subscripts"):
        colCummins(_printed_1_to_12(), cols=[-1.0, 1.0])
    with pytest.raises(ValueError, match="logical, integer or numeric"):
        rowCummins(np.array(["a", "b"]))


def test_matches_r_on_subsets_missing_values_and_types():
    if shutil.which("Rscript") is None:
        pytest.skip("Rscript is unavailable")
    reference = _r_suite()
    if reference is None:
        pytest.skip("matrixStats is unavailable")

    printed = _printed_1_to_12()
    _assert_close(rowCummins(printed), reference["rows"])
    _assert_close(colCummins(printed), reference["cols"])
    _assert_close(rowCummins(printed, rows=[3, 0, 0, 1]), reference["sub"])
    _assert_close(colCummins(printed, rows=[3, 1]), reference["sub_col"])
    _assert_close(rowCummins(printed, cols=[3, 1]), reference["sub_cols"])
    _assert_close(rowCummins(printed, rows=[-4, 0, 0, -3, -1]), reference["neg"])
    _assert_close(rowCummins(printed, rows=[False, True]), reference["logic"])
    _assert_close(rowCummins(np.arange(1, 13), dim=(4, 3)), reference["vector"])
    _assert_close(rowCummins(printed, dim=(6, 2)), reference["redim"])

    logical = np.array([[True, False, True], [True, True, False]])
    _assert_close(rowCummins(logical), reference["lgl_row"])
    _assert_close(colCummins(logical), reference["lgl_col"])

    with_nan = np.array(
        [[1.0, np.nan, 9.0], [2.0, 6.0, 10.0], [4.0, 1.0, 5.0]]
    )
    _assert_close(rowCummins(with_nan), reference["na_row"])
    _assert_close(colCummins(with_nan), reference["na_col"])
    _assert_close(rowCummins(with_nan, rows=[3, 1]), reference["na_rows"])
    _assert_close(colCummins(with_nan, rows=[3, 1]), reference["na_rows_col"])

    na = NA_INTEGER
    ints = np.array([[1, 3, na], [na, 2, 0], [4, 1, 5]], dtype=np.int32)
    _assert_close(rowCummins(ints), reference["int_row"])
    _assert_close(colCummins(ints), reference["int_col"])

    matrix = reference["matrix"]
    _assert_close(rowCummins(matrix), reference["big_row"])
    _assert_close(colCummins(matrix), reference["big_col"])
    rows = np.array([3, 5, 1, 5, 20])
    _assert_close(rowCummins(matrix, rows=rows), reference["big_rows"])
    _assert_close(colCummins(matrix, rows=rows), reference["big_rows_col"])

    poisoned = np.array(matrix, order="C", copy=True)
    poisoned[1, 4] = np.nan
    poisoned[10, 0] = np.nan
    _assert_close(rowCummins(poisoned), reference["poison_row"])
    _assert_close(colCummins(poisoned), reference["poison_col"])
    _assert_close(rowCummins(poisoned, rows=[2, 11, 1]), reference["poison_sub"])


def _printed_1_to_12():
    return np.arange(1, 13, dtype=np.int32).reshape((4, 3), order="F")


def _assert_close(actual, expected):
    actual = np.asarray(actual)
    expected = np.asarray(expected)
    assert actual.shape == expected.shape
    if np.issubdtype(actual.dtype, np.integer) or np.issubdtype(
        expected.dtype, np.integer
    ):
        actual_na = actual == NA_INTEGER
        expected_na = expected == NA_INTEGER
        assert np.array_equal(actual_na, expected_na)
        assert np.array_equal(actual[~actual_na], expected[~expected_na])
        return
    actual_f = actual.astype(np.float64)
    expected_f = expected.astype(np.float64)
    both_nan = np.isnan(actual_f) & np.isnan(expected_f)
    both_pos = np.isposinf(actual_f) & np.isposinf(expected_f)
    both_neg = np.isneginf(actual_f) & np.isneginf(expected_f)
    diff = np.abs(actual_f - expected_f)
    ok = both_nan | both_pos | both_neg | (diff <= TOL)
    assert bool(np.all(ok)), np.nanmax(np.where(ok, 0.0, diff))


def _r_suite():
    script = textwrap.dedent(
        r"""
        args <- commandArgs(trailingOnly=TRUE)
        bin <- args[[1]]
        if (!requireNamespace("matrixStats", quietly=TRUE)) quit(status=2)
        na_int <- NA_integer_
        emit <- function(name, values) {
          values <- as.matrix(values)
          cat(name, "\n", sep="")
          cat(nrow(values), " ", ncol(values), "\n", sep="")
          flat <- as.vector(values)
          missing <- is.na(flat)
          encoded <- ifelse(missing, "NA", sprintf("%.17g", as.numeric(flat)))
          if (length(encoded)) cat(encoded, sep="\n")
          cat("---\n")
        }
        x <- matrix(1:12, nrow=4)
        emit("rows", matrixStats::rowCummins(x))
        emit("cols", matrixStats::colCummins(x))
        emit("sub", matrixStats::rowCummins(x, rows=c(3, 0, 0, 1)))
        emit("sub_col", matrixStats::colCummins(x, rows=c(3, 1)))
        emit("sub_cols", matrixStats::rowCummins(x, cols=c(3, 1)))
        emit("neg", matrixStats::rowCummins(x, rows=c(-4, 0, 0, -3, -1)))
        emit("logic", matrixStats::rowCummins(x, rows=c(FALSE, TRUE)))
        emit("vector", matrixStats::rowCummins(as.integer(x), dim.=c(4L, 3L)))
        emit("redim", matrixStats::rowCummins(x, dim.=c(6L, 2L)))

        logical <- matrix(c(TRUE, TRUE, FALSE, TRUE, TRUE, FALSE), nrow=2)
        emit("lgl_row", matrixStats::rowCummins(logical))
        emit("lgl_col", matrixStats::colCummins(logical))

        na_x <- matrix(c(1, 2, 4, NA, 6, 1, 9, 10, 5), nrow=3)
        emit("na_row", matrixStats::rowCummins(na_x))
        emit("na_col", matrixStats::colCummins(na_x))
        emit("na_rows", matrixStats::rowCummins(na_x, rows=c(3, 1)))
        emit("na_rows_col", matrixStats::colCummins(na_x, rows=c(3, 1)))

        int_x <- matrix(c(1L, NA_integer_, 4L, 3L, 2L, 1L, NA_integer_, 0L, 5L), nrow=3)
        emit("int_row", matrixStats::rowCummins(int_x))
        emit("int_col", matrixStats::colCummins(int_x))

        set.seed(1)
        big <- matrix(rnorm(40 * 25), nrow=40, ncol=25)
        writeBin(as.numeric(big), bin)
        emit("big_row", matrixStats::rowCummins(big))
        emit("big_col", matrixStats::colCummins(big))
        emit("big_rows", matrixStats::rowCummins(big, rows=c(3, 5, 1, 5, 20)))
        emit("big_rows_col", matrixStats::colCummins(big, rows=c(3, 5, 1, 5, 20)))
        big[2, 5] <- NA
        big[11, 1] <- NA
        emit("poison_row", matrixStats::rowCummins(big))
        emit("poison_col", matrixStats::colCummins(big))
        emit("poison_sub", matrixStats::rowCummins(big, rows=c(2, 11, 1)))
        """
    )
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        program = root / "check.R"
        data = root / "big.bin"
        program.write_text(script)
        result = subprocess.run(
            ["Rscript", str(program), str(data)],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode == 2:
            return None
        if result.returncode != 0:
            raise RuntimeError(result.stderr)
        parsed = _parse_blocks(result.stdout)
        matrix = np.fromfile(data, dtype="<f8").reshape((40, 25), order="F")
        parsed["matrix"] = np.array(matrix, order="C", copy=True)
        return parsed


def _parse_blocks(text: str):
    parsed = {}
    chunks = text.split("---\n")
    for chunk in chunks:
        lines = [line for line in chunk.splitlines() if line != ""]
        if not lines:
            continue
        name = lines[0]
        nrow, ncol = (int(part) for part in lines[1].split())
        values = []
        for line in lines[2:]:
            values.append(np.nan if line == "NA" else float(line))
        parsed[name] = np.asarray(values, dtype=np.float64).reshape((nrow, ncol), order="F")
    for name in (
        "rows",
        "cols",
        "sub",
        "sub_col",
        "sub_cols",
        "neg",
        "logic",
        "vector",
        "redim",
        "lgl_row",
        "lgl_col",
        "int_row",
        "int_col",
    ):
        block = parsed[name]
        as_int = np.array(block, dtype=np.float64, copy=True)
        out = np.empty(as_int.shape, dtype=np.int32)
        missing = np.isnan(as_int)
        out[missing] = NA_INTEGER
        out[~missing] = as_int[~missing].astype(np.int32)
        parsed[name] = out
    return parsed
