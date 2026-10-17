"""Checks for rowSums2 and colSums2 against NumPy and R."""

from __future__ import annotations

import subprocess
import textwrap

import numpy as np
import pytest

from matrixstats.rowsums2 import colSums2, rowSums2


def test_full_sums_match_the_printed_matrix():
    x = np.array([[1.0, 3.0, 5.0], [2.0, 4.0, 6.0]])
    assert rowSums2(x).tolist() == [9.0, 12.0]
    assert colSums2(x).tolist() == [3.0, 7.0, 11.0]


def test_na_rm_and_all_na_rows():
    x = np.array([[np.nan, np.nan, np.nan], [2.0, 4.0, 6.0]])
    assert rowSums2(x, na_rm=True).tolist() == [0.0, 12.0]
    assert np.isnan(rowSums2(x, na_rm=False)[0])
    assert rowSums2(x, na_rm=False)[1] == 12.0
    assert colSums2(x, na_rm=True).tolist() == [2.0, 4.0, 6.0]
    assert np.isnan(colSums2(x, na_rm=False)).all()

    blank = np.full((2, 3), np.nan)
    assert rowSums2(blank, na_rm=True).tolist() == [0.0, 0.0]
    assert colSums2(blank, na_rm=True).tolist() == [0.0, 0.0, 0.0]
    assert np.isnan(rowSums2(blank)).all()
    assert np.isnan(colSums2(blank)).all()


def test_empty_margins():
    x = np.array([[1.0, 3.0, 5.0], [2.0, 4.0, 6.0]])
    assert rowSums2(x, rows=np.array([], dtype=np.int64)).size == 0
    assert rowSums2(x, cols=np.array([], dtype=np.int64)).tolist() == [0.0, 0.0]
    assert colSums2(x, rows=np.array([], dtype=np.int64)).tolist() == [0.0, 0.0, 0.0]
    assert colSums2(x, cols=np.array([], dtype=np.int64)).size == 0
    assert colSums2(np.zeros((0, 3))).tolist() == [0.0, 0.0, 0.0]
    assert rowSums2(np.zeros((4, 0))).tolist() == [0.0, 0.0, 0.0, 0.0]


def test_one_based_subsets_and_column_major_dim():
    x = np.array([[1.0, 3.0, 5.0], [2.0, 4.0, 6.0]])
    assert rowSums2(x, rows=[1, 1]).tolist() == [9.0, 9.0]
    assert rowSums2(x, cols=[1, 3]).tolist() == [6.0, 8.0]
    assert colSums2(x, cols=[2]).tolist() == [7.0]
    assert rowSums2(x, rows=[0, 2, 0]).tolist() == [12.0]
    assert rowSums2(x, rows=[-2]).tolist() == [9.0]

    flat = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0])
    assert rowSums2(flat, dim=(2, 3)).tolist() == [9.0, 12.0]
    assert colSums2(flat, dim=np.array([2, 3], dtype=np.int32)).tolist() == [3.0, 7.0, 11.0]


def test_logical_rows_and_out_of_bounds():
    x = np.array([[1.0, 3.0, 5.0], [2.0, 4.0, 6.0]])
    assert rowSums2(x, rows=[False, True]).tolist() == [12.0]
    assert rowSums2(x, rows=True).tolist() == [9.0, 12.0]
    assert rowSums2(x, rows=False).size == 0
    with pytest.raises(ValueError, match="out of bounds"):
        rowSums2(x, rows=[1, 9])
    with pytest.raises(ValueError, match="negative subscripts"):
        rowSums2(x, rows=[-1, 1])


def test_matches_r_on_subsets_na_and_the_timing_shape():
    rng = np.random.default_rng(1)
    x = rng.standard_normal((400, 250))
    _assert_r(x, "row")
    _assert_r(x, "col")
    _assert_r(x, "row", rows=np.array([1, 50, 400]))
    _assert_r(x, "col", cols=np.array([2, 10, 250]))

    dirty = x.copy()
    dirty[::17, ::13] = np.nan
    dirty[0, :] = np.nan
    _assert_r(dirty, "row", na_rm=True)
    _assert_r(dirty, "col", na_rm=True)
    _assert_r(dirty, "row", na_rm=False)
    _assert_r(dirty, "col", na_rm=False)

    small = np.array([[1.0, 3.0, 5.0], [2.0, 4.0, 6.0]])
    _assert_r(small, "row", rows=np.array([], dtype=np.int64))
    _assert_r(small, "col", cols=np.array([], dtype=np.int64))
    _assert_r(np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0]), "row", dim=(2, 3))
    _assert_r(np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0]), "col", dim=(2, 3))


def _assert_r(x, kind, rows=None, cols=None, na_rm=False, dim=None):
    reference = _r_sums(x, kind, rows=rows, cols=cols, na_rm=na_rm, dim=dim)
    if kind == "row":
        got = rowSums2(x, rows=rows, cols=cols, na_rm=na_rm, dim=dim)
    else:
        got = colSums2(x, rows=rows, cols=cols, na_rm=na_rm, dim=dim)
    _close(got, reference)


def _close(got, reference):
    got = np.asarray(got, dtype=np.float64)
    reference = np.asarray(reference, dtype=np.float64)
    assert got.shape == reference.shape
    both_nan = np.isnan(got) & np.isnan(reference)
    assert np.array_equal(np.isnan(got), np.isnan(reference))
    if np.any(~both_nan):
        diff = np.abs(got[~both_nan] - reference[~both_nan])
        assert np.all(diff <= 1e-8)


def _r_sums(x, kind, rows=None, cols=None, na_rm=False, dim=None):
    values = np.asarray(x, dtype=np.float64)
    if dim is None:
        nrow, ncol = values.shape
        payload = np.asfortranarray(values).ravel(order="F")
    else:
        nrow, ncol = (int(dim[0]), int(dim[1]))
        if values.ndim == 1:
            payload = np.ascontiguousarray(values, dtype=np.float64)
        else:
            payload = np.ravel(np.asfortranarray(values), order="F")
    script = _r_script(kind, nrow, ncol, rows, cols, na_rm)
    result = subprocess.run(
        ["Rscript", "-e", script],
        input=payload.tobytes(),
        check=False,
        capture_output=True,
    )
    if result.returncode != 0:
        raise AssertionError(result.stderr.decode())
    lines = result.stdout.decode().splitlines()
    length = int(lines[0])
    if length == 0:
        return np.zeros(0, dtype=np.float64)
    out = np.frombuffer(bytes.fromhex(lines[1]), dtype=np.float64).copy()
    assert out.size == length
    return out


def _r_script(kind, nrow, ncol, rows, cols, na_rm):
    fn = "rowSums2" if kind == "row" else "colSums2"
    na = "TRUE" if na_rm else "FALSE"
    rows_r = _r_index(rows)
    cols_r = _r_index(cols)
    return textwrap.dedent(
        f"""
        library(matrixStats)
        input <- file("stdin", "rb")
        x <- readBin(input, "double", {nrow * ncol})
        close(input)
        res <- {fn}(x, rows = {rows_r}, cols = {cols_r}, na.rm = {na}, dim. = c({nrow}L, {ncol}L), useNames = FALSE)
        cat(length(res), "\\n", sep = "")
        if (length(res)) {{
          raw <- writeBin(as.numeric(res), raw())
          cat(paste(sprintf("%02x", as.integer(raw)), collapse = ""), "\\n", sep = "")
        }}
        """
    )


def _r_index(index):
    if index is None:
        return "NULL"
    arr = np.asarray(index)
    if arr.ndim == 0:
        arr = arr.reshape(1)
    if arr.size == 0:
        return "integer(0)"
    if arr.dtype == np.bool_:
        flags = ", ".join("TRUE" if flag else "FALSE" for flag in arr.tolist())
        return f"c({flags})"
    values = ", ".join(str(int(v)) for v in arr.tolist())
    return f"c({values})"
