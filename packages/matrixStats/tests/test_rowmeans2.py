"""Checks for rowMeans2 and colMeans2, including a comparison with R."""

from __future__ import annotations

import shutil
import subprocess
import textwrap

import numpy as np
import pytest

from matrixstats.rowmeans2 import colMeans2, rowMeans2

TOL = 1e-8


def test_printed_matrix_matches_column_major_storage():
    printed = np.array(
        [[1.0, 5.0, 9.0], [2.0, 6.0, 10.0], [3.0, 7.0, 11.0], [4.0, 8.0, 12.0]]
    )
    assert rowMeans2(printed).tolist() == [5.0, 6.0, 7.0, 8.0]
    assert colMeans2(printed).tolist() == [2.5, 6.5, 10.5]

    flat = np.arange(1.0, 13.0)
    assert rowMeans2(flat, dim=(4, 3)).tolist() == [5.0, 6.0, 7.0, 8.0]
    assert colMeans2(flat, dim=(4, 3)).tolist() == [2.5, 6.5, 10.5]

    fortran = np.asfortranarray(printed)
    assert rowMeans2(fortran).tolist() == [5.0, 6.0, 7.0, 8.0]


def test_rows_subset_drops_zeros_and_keeps_duplicates():
    printed = _printed_1_to_12()
    got = rowMeans2(printed, rows=[3, 0, 0, 1, 3])
    assert got.tolist() == [7.0, 5.0, 7.0]
    assert got.dtype == np.float64
    assert got.ndim == 1


def test_negative_rows_and_logical_columns():
    printed = _printed_1_to_12()
    assert rowMeans2(printed, rows=[-4, 0, 0, -3, -1]).tolist() == [6.0]
    assert rowMeans2(printed, rows=[False, True]).tolist() == [6.0, 8.0]
    assert colMeans2(printed, cols=[2, 2]).tolist() == [6.5, 6.5]


def test_refine_changes_the_residual_and_na_rm_skips_nan():
    tricky = np.array([[1e8, 1.0, -1e8]])
    refined = rowMeans2(tricky, refine=True)
    plain = rowMeans2(tricky, refine=False)
    assert refined[0] == pytest.approx(0.33333333830038703, abs=1e-18)
    assert plain[0] == pytest.approx(1.0 / 3.0, abs=1e-18)

    data = np.array([[np.nan, 2.0], [1.0, np.nan]])
    assert np.isnan(rowMeans2(data, na_rm=False)).all()
    assert rowMeans2(data, na_rm=True).tolist() == [2.0, 1.0]
    assert colMeans2(data, na_rm=True).tolist() == [1.0, 2.0]


def test_empty_margins_are_nan_or_length_zero():
    assert rowMeans2(np.zeros((0, 0))).shape == (0,)
    assert colMeans2(np.zeros((0, 0))).shape == (0,)
    assert np.isnan(rowMeans2(np.zeros((3, 0)))).all()
    assert np.isnan(colMeans2(np.zeros((0, 3)))).all()
    assert rowMeans2(np.zeros((0, 3))).shape == (0,)


def test_use_names_is_accepted_and_returns_a_plain_vector():
    values = rowMeans2(_printed_1_to_12(), use_names=False)
    assert values.tolist() == [5.0, 6.0, 7.0, 8.0]
    assert values.dtype == np.float64


def test_dim_reinterprets_column_major_storage():
    printed = _printed_1_to_12()
    got = rowMeans2(printed, dim=(6, 2))
    assert got.tolist() == [4.0, 5.0, 6.0, 7.0, 8.0, 9.0]


def test_integer_matrix_skips_refinement():
    values = np.arange(1, 13, dtype=np.int32).reshape((4, 3), order="F")
    assert rowMeans2(values, refine=True).tolist() == [5.0, 6.0, 7.0, 8.0]


def test_rejects_bad_dim_flags_and_subscripts():
    with pytest.raises(ValueError, match="dim."):
        rowMeans2(np.arange(4.0), dim=(2, 3))
    with pytest.raises(ValueError, match="TRUE or FALSE"):
        rowMeans2(_printed_1_to_12(), na_rm=1)
    with pytest.raises(ValueError, match="subscript out of bounds"):
        rowMeans2(_printed_1_to_12(), rows=[4, 5, 6, 7, 8, 9])
    with pytest.raises(ValueError, match="negative subscripts"):
        colMeans2(_printed_1_to_12(), cols=[-1.0, 1.0])


def test_matches_r_on_subsets_refine_and_missing_values():
    if shutil.which("Rscript") is None:
        pytest.skip("Rscript is unavailable")
    reference = _r_suite()
    if reference is None:
        pytest.skip("matrixStats is unavailable")

    printed = _printed_1_to_12()
    _assert_close(rowMeans2(printed), reference["rows"])
    _assert_close(colMeans2(printed), reference["cols"])
    _assert_close(rowMeans2(printed, rows=[3, 0, 0, 1, 3]), reference["sub"])
    _assert_close(rowMeans2(printed, rows=[-4, 0, 0, -3, -1]), reference["neg"])
    _assert_close(rowMeans2(printed, rows=[False, True]), reference["logic"])
    _assert_close(rowMeans2(np.array([[1e8, 1.0, -1e8]]), refine=True), reference["refine_t"])
    _assert_close(rowMeans2(np.array([[1e8, 1.0, -1e8]]), refine=False), reference["refine_f"])
    _assert_close(rowMeans2(printed, dim=(6, 2)), reference["redim"])
    _assert_close(rowMeans2(np.arange(1.0, 13.0), dim=(4, 3)), reference["vector"])

    matrix = reference["matrix"]
    _assert_close(rowMeans2(matrix, na_rm=False, refine=True), reference["big_row"])
    _assert_close(colMeans2(matrix, na_rm=False, refine=True), reference["big_col"])
    _assert_close(rowMeans2(matrix, na_rm=False, refine=False), reference["big_row_plain"])
    _assert_close(colMeans2(matrix, cols=[2, 4, 4, 10]), reference["big_cols"])
    rows = np.array([3, 5, 1, 5, 20])
    _assert_close(rowMeans2(matrix, rows=rows, refine=True), reference["big_rows"])

    with_nan = np.array(matrix, order="F", copy=True)
    with_nan.ravel(order="F")[:30] = np.nan
    _assert_close(rowMeans2(with_nan, na_rm=True, refine=True), reference["na_row"])
    _assert_close(colMeans2(with_nan, na_rm=True, refine=False), reference["na_col"])


def _printed_1_to_12():
    return np.arange(1.0, 13.0).reshape((4, 3), order="F")


def _assert_close(actual, expected):
    actual = np.asarray(actual, dtype=np.float64)
    expected = np.asarray(expected, dtype=np.float64)
    assert actual.shape == expected.shape
    both_nan = np.isnan(actual) & np.isnan(expected)
    both_pos = np.isposinf(actual) & np.isposinf(expected)
    both_neg = np.isneginf(actual) & np.isneginf(expected)
    diff = np.abs(actual - expected)
    ok = both_nan | both_pos | both_neg | (diff <= TOL)
    assert bool(np.all(ok)), np.nanmax(np.where(ok, 0.0, diff))


def _r_suite():
    script = textwrap.dedent(
        r"""
        args <- commandArgs(trailingOnly=TRUE)
        bin <- args[[1]]
        if (!requireNamespace("matrixStats", quietly=TRUE)) quit(status=2)
        emit <- function(name, values) {
          cat(name, "\n", sep="")
          if (length(values)) cat(sprintf("%.17g\n", values), sep="")
          cat("---\n")
        }
        x <- matrix(1:12, nrow=4)
        emit("rows", matrixStats::rowMeans2(x))
        emit("cols", matrixStats::colMeans2(x))
        emit("sub", matrixStats::rowMeans2(x, rows=c(3, 0, 0, 1, 3)))
        emit("neg", matrixStats::rowMeans2(x, rows=c(-4, 0, 0, -3, -1)))
        emit("logic", matrixStats::rowMeans2(x, rows=c(FALSE, TRUE)))
        tricky <- matrix(c(1e8, 1, -1e8), nrow=1)
        emit("refine_t", matrixStats::rowMeans2(tricky, refine=TRUE))
        emit("refine_f", matrixStats::rowMeans2(tricky, refine=FALSE))
        emit("redim", matrixStats::rowMeans2(x, dim.=c(6L, 2L)))
        emit("vector", matrixStats::rowMeans2(as.numeric(x), dim.=c(4L, 3L)))

        set.seed(1)
        big <- matrix(rnorm(40 * 25), nrow=40, ncol=25)
        writeBin(as.numeric(big), bin)
        emit("big_row", matrixStats::rowMeans2(big, na.rm=FALSE, refine=TRUE))
        emit("big_col", matrixStats::colMeans2(big, na.rm=FALSE, refine=TRUE))
        emit("big_row_plain", matrixStats::rowMeans2(big, na.rm=FALSE, refine=FALSE))
        emit("big_cols", matrixStats::colMeans2(big, cols=c(2, 4, 4, 10)))
        emit("big_rows", matrixStats::rowMeans2(big, rows=c(3, 5, 1, 5, 20)))
        big[seq_len(30)] <- NA
        emit("na_row", matrixStats::rowMeans2(big, na.rm=TRUE, refine=TRUE))
        emit("na_col", matrixStats::colMeans2(big, na.rm=TRUE, refine=FALSE))
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
    name = None
    chunk: list[str] = []
    for line in text.splitlines():
        if line == "---":
            parsed[name] = _numbers(chunk)
            name = None
            chunk = []
        elif name is None:
            name = line
        else:
            chunk.append(line)
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
