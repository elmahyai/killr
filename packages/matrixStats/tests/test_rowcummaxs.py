"""Checks for rowCummaxs and colCummaxs, including a comparison with R."""

from __future__ import annotations

import shutil
import subprocess
import textwrap

import numpy as np
import pytest

from matrixstats.rowcummaxs import colCummaxs, rowCummaxs

TOL = 1e-8
NA_INTEGER = np.int32(np.iinfo(np.int32).min)


def test_printed_matrix_matches_column_major_storage():
    printed = np.array([[3.0, 4.0, 5.0], [1.0, 2.0, 0.0]])
    assert rowCummaxs(printed).tolist() == [[3.0, 4.0, 5.0], [1.0, 2.0, 2.0]]
    assert colCummaxs(printed).tolist() == [[3.0, 4.0, 5.0], [3.0, 4.0, 5.0]]

    flat = np.array([3.0, 1.0, 4.0, 2.0, 5.0, 0.0])
    assert rowCummaxs(flat, dim=(2, 3)).tolist() == [[3.0, 4.0, 5.0], [1.0, 2.0, 2.0]]
    assert colCummaxs(np.asfortranarray(printed)).tolist() == [
        [3.0, 4.0, 5.0],
        [3.0, 4.0, 5.0],
    ]


def test_logical_input_returns_int32():
    printed = np.array([[True, False, True], [False, True, False]])
    rows = rowCummaxs(printed)
    cols = colCummaxs(printed)
    assert rows.dtype == np.int32
    assert cols.dtype == np.int32
    assert rows.tolist() == [[1, 1, 1], [0, 1, 1]]
    assert cols.tolist() == [[1, 0, 1], [1, 1, 1]]


def test_integer_matrix_and_nan_propagation():
    values = np.array([[5, 1, 4], [2, 9, 3]], dtype=np.int32)
    assert rowCummaxs(values).tolist() == [[5, 5, 5], [2, 9, 9]]
    assert colCummaxs(values).dtype == np.int32
    assert colCummaxs(values).tolist() == [[5, 1, 4], [5, 9, 4]]

    data = np.array([[1.0, np.nan, 4.0], [2.0, 0.0, np.nan]])
    rows = rowCummaxs(data)
    cols = colCummaxs(data)
    assert rows.dtype == np.float64
    assert rows[0, 0] == 1.0 and np.isnan(rows[0, 1]) and np.isnan(rows[0, 2])
    assert rows[1, 0] == 2.0 and rows[1, 1] == 2.0 and np.isnan(rows[1, 2])
    assert cols[0, 0] == 1.0 and cols[1, 0] == 2.0
    assert np.isnan(cols[:, 1]).all()
    assert cols[0, 2] == 4.0 and np.isnan(cols[1, 2])


def test_integer_na_propagates_like_r():
    data = np.array([[1, 5, 9], [2, 6, 10], [3, 7, 11], [NA_INTEGER, 8, 12]], dtype=np.int32)
    data[1, 1] = NA_INTEGER
    rows = rowCummaxs(data)
    assert rows[0].tolist() == [1, 5, 9]
    assert rows[1, 0] == 2 and rows[1, 1] == NA_INTEGER and rows[1, 2] == NA_INTEGER
    assert rows[3, 0] == NA_INTEGER and rows[3, 1] == NA_INTEGER
    cols = colCummaxs(data)
    assert cols[:3, 0].tolist() == [1, 2, 3]
    assert cols[3, 0] == NA_INTEGER
    assert cols[0, 1] == 5 and cols[1, 1] == NA_INTEGER and cols[3, 1] == NA_INTEGER


def test_cols_subset_drops_zeros_and_keeps_duplicates():
    printed = np.array([[3.0, 4.0, 5.0], [1.0, 2.0, 0.0]])
    got = rowCummaxs(printed, cols=[3, 0, 0, 1, 3])
    assert got.shape == (2, 3)
    assert got.tolist() == [[5.0, 5.0, 5.0], [0.0, 1.0, 1.0]]
    assert colCummaxs(printed, cols=[2, 2]).tolist() == [[4.0, 4.0], [4.0, 4.0]]


def test_negative_rows_and_logical_columns():
    printed = np.arange(1.0, 13.0).reshape((4, 3), order="F")
    assert rowCummaxs(printed, rows=[-4, 0, 0, -3, -1]).shape == (1, 3)
    assert rowCummaxs(printed, rows=[False, True]).shape == (2, 3)
    assert colCummaxs(printed, rows=[3, 1]).shape == (2, 3)


def test_missing_subscript_fills_the_rest_of_the_line():
    printed = np.array([[3.0, 4.0, 5.0], [1.0, 2.0, 0.0]])
    got = rowCummaxs(printed, cols=np.array([2.0, np.nan, 1.0]))
    assert got.shape == (2, 3)
    assert got[:, 0].tolist() == [4.0, 2.0]
    assert np.isnan(got[:, 1:]).all()


def test_infinity_and_a_tie():
    data = np.array([[1.0, np.inf, 3.0], [-np.inf, -4.0, -1.0]])
    rows = rowCummaxs(data)
    assert rows[0, 0] == 1.0 and np.isposinf(rows[0, 1]) and np.isposinf(rows[0, 2])
    assert np.isneginf(rows[1, 0]) and rows[1, 1] == -4.0 and rows[1, 2] == -1.0
    tied = rowCummaxs(np.array([[-0.0, 0.0]]))
    assert np.signbit(tied[0, 0]) and np.signbit(tied[0, 1])


def test_empty_margins():
    assert rowCummaxs(np.zeros((0, 0))).shape == (0, 0)
    assert colCummaxs(np.zeros((0, 5))).shape == (0, 5)
    assert rowCummaxs(np.zeros((4, 0))).shape == (4, 0)
    assert rowCummaxs(np.zeros((3, 4), dtype=np.int32), rows=[]).shape == (0, 4)
    assert rowCummaxs(np.zeros((3, 4), dtype=np.int32), rows=[]).dtype == np.int32


def test_use_names_is_accepted():
    values = rowCummaxs(np.array([[3.0, 1.0], [2.0, 4.0]]), use_names=False)
    assert values.tolist() == [[3.0, 3.0], [2.0, 4.0]]
    assert colCummaxs(np.array([[3.0, 1.0], [2.0, 4.0]]), use_names=True).tolist() == [
        [3.0, 1.0],
        [3.0, 4.0],
    ]


def test_dim_reinterprets_column_major_storage():
    flat = np.array([3.0, 1.0, 4.0, 2.0, 9.0, 0.0])
    got = rowCummaxs(flat, dim=(3, 2))
    assert got.shape == (3, 2)
    # Column-major 3 by 2 is [[3, 2], [1, 9], [4, 0]].
    assert got.tolist() == [[3.0, 3.0], [1.0, 9.0], [4.0, 4.0]]


def test_rejects_bad_dim_flags_and_subscripts():
    with pytest.raises(ValueError, match="dim."):
        rowCummaxs(np.arange(4.0), dim=(2, 3))
    with pytest.raises(ValueError, match="TRUE or FALSE"):
        rowCummaxs(np.arange(4.0).reshape(2, 2), use_names=1)
    with pytest.raises(ValueError, match="subscript out of bounds"):
        rowCummaxs(np.arange(6.0).reshape(2, 3), rows=[4])
    with pytest.raises(ValueError, match="negative subscripts"):
        colCummaxs(np.arange(6.0).reshape(2, 3), cols=[-1.0, 1.0])
    with pytest.raises(ValueError, match="logical, integer or numeric"):
        rowCummaxs(np.array(["a", "b"]))


def test_matches_r_on_na_subsets_and_modes():
    if shutil.which("Rscript") is None:
        pytest.skip("Rscript is unavailable")
    reference = _r_suite()
    if reference is None:
        pytest.skip("matrixStats is unavailable")

    printed = np.array([[3.0, 4.0, 5.0], [1.0, 2.0, 0.0]])
    _assert_close(rowCummaxs(printed), reference["small_row"])
    _assert_close(colCummaxs(printed), reference["small_col"])
    _assert_close(rowCummaxs(printed, cols=[3, 0, 0, 1, 3]), reference["cols_sub"])
    _assert_close(
        rowCummaxs(printed, cols=np.array([2.0, np.nan, 1.0])),
        reference["cols_na"],
    )
    _assert_close(colCummaxs(printed, rows=[2, 1, 2]), reference["rows_sub"])

    logical = np.array([[True, False, True], [False, True, False]])
    _assert_close(rowCummaxs(logical), reference["lgl_row"])
    _assert_close(colCummaxs(logical), reference["lgl_col"])

    ints = np.array([[1, 5, 9], [2, 6, 10], [3, 7, 11], [4, 8, 12]], dtype=np.int32)
    ints = np.array(ints, order="F", copy=True)
    ints[1, 1] = NA_INTEGER
    ints[3, 0] = NA_INTEGER
    _assert_close(rowCummaxs(ints), reference["int_row"])
    _assert_close(colCummaxs(ints), reference["int_col"])

    matrix = reference["matrix"]
    _assert_close(rowCummaxs(matrix), reference["big_row"])
    _assert_close(colCummaxs(matrix), reference["big_col"])
    _assert_close(rowCummaxs(matrix, cols=[2, 4, 4, 10]), reference["big_cols"])
    _assert_close(colCummaxs(matrix, cols=[2, 4, 4, 10]), reference["big_cols_down"])
    with_nan = np.array(matrix, order="F", copy=True)
    with_nan.ravel(order="F")[:30] = np.nan
    _assert_close(rowCummaxs(with_nan), reference["na_row"])
    _assert_close(colCummaxs(with_nan), reference["na_col"])
    _assert_close(rowCummaxs(with_nan, cols=[3, 1, 8]), reference["na_cols"])


def _assert_close(actual, expected):
    actual_f = _as_float(actual)
    expected = np.asarray(expected, dtype=np.float64)
    assert actual_f.shape == expected.shape
    both_nan = np.isnan(actual_f) & np.isnan(expected)
    both_pos = np.isposinf(actual_f) & np.isposinf(expected)
    both_neg = np.isneginf(actual_f) & np.isneginf(expected)
    diff = np.abs(actual_f - expected)
    ok = both_nan | both_pos | both_neg | (diff <= TOL)
    assert bool(np.all(ok)), np.nanmax(np.where(ok, 0.0, diff))


def _as_float(actual) -> np.ndarray:
    actual = np.asarray(actual)
    if np.issubdtype(actual.dtype, np.integer):
        out = actual.astype(np.float64)
        out[actual == NA_INTEGER] = np.nan
        return out
    return actual.astype(np.float64)


def _r_suite():
    script = textwrap.dedent(
        r"""
        args <- commandArgs(trailingOnly=TRUE)
        bin <- args[[1]]
        if (!requireNamespace("matrixStats", quietly=TRUE)) quit(status=2)
        emit <- function(name, values) {
          cat(name, "\n", sep="")
          cat(nrow(values), " ", ncol(values), "\n", sep="")
          flat <- as.numeric(values)
          if (length(flat)) cat(sprintf("%.17g\n", flat), sep="")
          cat("---\n")
        }
        x <- matrix(c(3, 1, 4, 2, 5, 0), nrow=2, ncol=3)
        emit("small_row", matrixStats::rowCummaxs(x))
        emit("small_col", matrixStats::colCummaxs(x))
        emit("cols_sub", matrixStats::rowCummaxs(x, cols=c(3, 0, 0, 1, 3)))
        emit("cols_na", matrixStats::rowCummaxs(x, cols=c(2, NA, 1)))
        emit("rows_sub", matrixStats::colCummaxs(x, rows=c(2, 1, 2)))

        lx <- matrix(c(TRUE, FALSE, FALSE, TRUE, TRUE, FALSE), nrow=2, ncol=3)
        emit("lgl_row", matrixStats::rowCummaxs(lx))
        emit("lgl_col", matrixStats::colCummaxs(lx))

        ix <- matrix(1:12, nrow=4, ncol=3)
        storage.mode(ix) <- "integer"
        ix[2, 2] <- NA
        ix[4, 1] <- NA
        emit("int_row", matrixStats::rowCummaxs(ix))
        emit("int_col", matrixStats::colCummaxs(ix))

        set.seed(1)
        big <- matrix(rnorm(40 * 25), nrow=40, ncol=25)
        writeBin(as.numeric(big), bin)
        emit("big_row", matrixStats::rowCummaxs(big))
        emit("big_col", matrixStats::colCummaxs(big))
        emit("big_cols", matrixStats::rowCummaxs(big, cols=c(2, 4, 4, 10)))
        emit("big_cols_down", matrixStats::colCummaxs(big, cols=c(2, 4, 4, 10)))
        big[seq_len(30)] <- NA
        emit("na_row", matrixStats::rowCummaxs(big))
        emit("na_col", matrixStats::colCummaxs(big))
        emit("na_cols", matrixStats::rowCummaxs(big, cols=c(3, 1, 8)))
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
        parsed["matrix"] = np.array(matrix, order="F", copy=True)
    return parsed


def _parse_blocks(text: str) -> dict:
    parsed = {}
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        name = lines[i]
        i += 1
        nrow, ncol = (int(part) for part in lines[i].split())
        i += 1
        chunk: list[str] = []
        while i < len(lines) and lines[i] != "---":
            chunk.append(lines[i])
            i += 1
        i += 1
        values = _numbers(chunk)
        parsed[name] = values.reshape((nrow, ncol), order="F")
    return parsed


def _numbers(lines: list[str]) -> np.ndarray:
    values = []
    for line in lines:
        if line in ("NA", "NaN"):
            values.append(np.nan)
        elif line == "Inf":
            values.append(np.inf)
        elif line == "-Inf":
            values.append(-np.inf)
        else:
            values.append(float(line))
    return np.asarray(values, dtype=np.float64)
