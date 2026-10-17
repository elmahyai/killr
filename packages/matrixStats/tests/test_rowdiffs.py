"""Checks for rowDiffs and colDiffs against the printed matrix and R."""

from __future__ import annotations

import subprocess
import textwrap
import warnings

import numpy as np
import pytest

from matrixstats.rowdiffs import colDiffs, rowDiffs

_NA = np.iinfo(np.int32).min


def test_full_diffs_match_the_printed_matrix():
    x = np.array(
        [[1, 5, 9], [2, 6, 10], [3, 7, 11], [4, 8, 12]],
        dtype=np.int32,
    )
    rows = rowDiffs(x)
    cols = colDiffs(x)
    assert rows.dtype == np.int32
    assert cols.dtype == np.int32
    assert rows.tolist() == [[4, 4], [4, 4], [4, 4], [4, 4]]
    assert cols.tolist() == [[1, 1, 1], [1, 1, 1], [1, 1, 1]]
    assert rowDiffs(x, use_names=False).shape == (4, 2)
    assert colDiffs(x).shape == (3, 3)


def test_logical_and_character_are_rejected():
    with pytest.raises(ValueError, match="cannot be logical"):
        rowDiffs(np.array([[True, False], [False, True]]))
    with pytest.raises(ValueError, match="not 'character'"):
        colDiffs(np.array(["a", "b"]))


def test_double_na_and_integer_na_and_wrap():
    x = np.array([[1.0, 5.0, 9.0], [np.nan, 6.0, 10.0], [3.0, 7.0, 11.0], [4.0, 8.0, 12.0]])
    rows = rowDiffs(x)
    assert rows[0].tolist() == [4.0, 4.0]
    assert np.isnan(rows[1, 0])
    assert rows[1, 1] == 4.0
    assert rows[2].tolist() == [4.0, 4.0]
    cols = colDiffs(x)
    assert np.isnan(cols[0, 0])
    assert np.isnan(cols[1, 0])
    assert cols[2, 0] == 1.0
    assert cols[:, 1].tolist() == [1.0, 1.0, 1.0]

    xi = np.array([[1, 5, 9], [_NA, 6, 10], [3, 7, 11], [4, 8, 12]], dtype=np.int32)
    assert rowDiffs(xi)[1].tolist() == [_NA, 4]
    assert colDiffs(xi)[:, 0].tolist() == [_NA, _NA, 1]

    wrapped = rowDiffs(np.array([[2_147_483_647, -1]], dtype=np.int32))
    assert wrapped.tolist() == [[_NA]]
    other = rowDiffs(np.array([[-2_000_000_000, 2_000_000_000]], dtype=np.int32))
    assert other.tolist() == [[-294_967_296]]


def test_subsets_lag_differences_and_dim():
    x = np.array(
        [[1.0, 5.0, 9.0], [2.0, 6.0, 10.0], [3.0, 7.0, 11.0], [4.0, 8.0, 12.0]]
    )
    assert rowDiffs(x, rows=[2, 4]).tolist() == [[4.0, 4.0], [4.0, 4.0]]
    assert colDiffs(x, cols=[3, 1]).tolist() == [[1.0, 1.0], [1.0, 1.0], [1.0, 1.0]]
    assert rowDiffs(x, rows=[1, 1], cols=[3, 1]).tolist() == [[-8.0], [-8.0]]
    assert rowDiffs(x, rows=[-2]).shape == (3, 2)
    assert colDiffs(x, cols=[0, 2, 0]).tolist() == [[1.0], [1.0], [1.0]]
    assert rowDiffs(x, lag=2).tolist() == [[8.0], [8.0], [8.0], [8.0]]
    assert rowDiffs(x, differences=2).tolist() == [[0.0], [0.0], [0.0], [0.0]]
    assert rowDiffs(x, lag=5).shape == (4, 0)
    assert colDiffs(x, differences=4).shape == (0, 3)

    flat = np.arange(1, 13)
    assert rowDiffs(flat, dim=(4, 3)).tolist() == rowDiffs(x).tolist()
    assert colDiffs(flat, dim=np.array([4, 3], dtype=np.int32)).tolist() == colDiffs(x).tolist()

    stepped = np.array([[1, 10], [4, 30], [9, 60], [16, 100]], dtype=np.int32)
    assert colDiffs(stepped, differences=2).tolist() == [[2, 10], [2, 10]]
    assert colDiffs(stepped, rows=[1, 2, 4], differences=2).tolist() == [[9, 50]]


def test_index_and_argument_errors():
    x = np.array([[1.0, 5.0], [2.0, 6.0]])
    with pytest.raises(ValueError, match="out of bounds"):
        rowDiffs(x, rows=[1, 9])
    with pytest.raises(ValueError, match="negative subscripts"):
        rowDiffs(x, cols=[-1, 1])
    with pytest.raises(ValueError, match="logical subscript too long"):
        colDiffs(x, rows=[True, False, True])
    with pytest.raises(ValueError, match="dim."):
        rowDiffs(np.array([1.0, 2.0, 3.0]))
    with pytest.raises(ValueError, match="positive integer"):
        rowDiffs(x, lag=0)
    with pytest.raises(ValueError, match="positive integer"):
        colDiffs(x, differences=-1)
    with pytest.raises(ValueError, match="dim."):
        rowDiffs(np.arange(12), dim=(-1, 3))
    with warnings.catch_warnings():
        warnings.simplefilter("error", RuntimeWarning)
        with pytest.raises(ValueError, match="positive integer"):
            rowDiffs(x, lag=float("nan"))
    with pytest.warns(RuntimeWarning, match="coercion to integer range"):
        with pytest.raises(ValueError, match="positive integer"):
            rowDiffs(x, lag=1e20)


def test_matches_r_on_subsets_na_and_the_timing_shape():
    x = np.array(
        [[1, 5, 9], [2, 6, 10], [3, 7, 11], [4, 8, 12]],
        dtype=np.int32,
    )
    _assert_r(x, "row")
    _assert_r(x, "col")
    _assert_r(x, "row", rows=np.array([2, 4]))
    _assert_r(x, "col", cols=np.array([3, 1]))
    _assert_r(x, "row", lag=2, differences=2)
    _assert_r(x, "col", differences=2)
    _assert_r(np.arange(1, 13), "row", dim=(4, 3))
    _assert_r(np.arange(1, 13), "col", dim=(4, 3))

    dirty = np.array([[1.0, 3.0, 5.0], [np.nan, 4.0, np.nan], [2.0, 8.0, 1.0]])
    _assert_r(dirty, "row")
    _assert_r(dirty, "col")
    _assert_r(dirty, "row", rows=np.array([np.nan, 2.0]))
    _assert_r(x, "row", cols=np.array([1, _NA], dtype=np.int32))
    _assert_r(x, "col", rows=[True, None, False])
    _assert_r(x, "row", cols=np.array([-4.9, -0.4]))
    _assert_r(x, "row", cols=np.array([1.9, 3.0]))

    stepped = np.array(
        [[1.0, 10.0], [4.0, 30.0], [9.0, 60.0], [16.0, 100.0], [25.0, 150.0], [36.0, 210.0]]
    )
    _assert_r(stepped, "col", differences=2)
    _assert_r(stepped, "col", differences=3, lag=1)
    _assert_r(stepped, "row", lag=2, differences=2)
    _assert_r(stepped, "col", rows=np.array([1, 2, 4, 6]), differences=2)
    _assert_r(stepped, "row", cols=np.array([2, 1, 2]), differences=2)

    wrapped = np.array([[-2_000_000_000, 2_000_000_000], [5, _NA]], dtype=np.int32)
    _assert_r(wrapped, "row")
    _assert_r(wrapped, "col")

    rng = np.random.default_rng(1)
    big = rng.standard_normal((400, 250))
    _assert_r(big, "row", lag=1, differences=1)
    _assert_r(big, "col", lag=1, differences=1)
    _assert_r(big, "row", rows=np.array([1, 50, 400]))
    _assert_r(big, "col", rows=np.array([1, 50, 400]))
    one_na = big.copy()
    one_na[3, 7] = np.nan
    _assert_r(one_na, "row")
    _assert_r(one_na, "col")


def _assert_r(x, kind, rows=None, cols=None, dim=None, lag=1, differences=1):
    reference = _r_diffs(
        x, kind, rows=rows, cols=cols, dim=dim, lag=lag, differences=differences
    )
    if kind == "row":
        got = rowDiffs(x, rows=rows, cols=cols, dim=dim, lag=lag, differences=differences)
    else:
        got = colDiffs(x, rows=rows, cols=cols, dim=dim, lag=lag, differences=differences)
    got = np.asarray(got)
    assert got.shape == reference.shape
    if np.issubdtype(reference.dtype, np.integer):
        assert got.dtype == np.int32
        assert np.array_equal(got, reference)
        return
    both_nan = np.isnan(got) & np.isnan(reference)
    assert np.array_equal(np.isnan(got), np.isnan(reference))
    if np.any(~both_nan):
        diff = np.abs(got[~both_nan] - reference[~both_nan])
        assert np.all(diff <= 1e-8)


def _r_diffs(x, kind, rows=None, cols=None, dim=None, lag=1, differences=1):
    values = np.asarray(x)
    logical = values.dtype == np.bool_
    integer = np.issubdtype(values.dtype, np.integer) and not logical
    if dim is None:
        nrow, ncol = values.shape
        if integer:
            payload = np.ravel(np.asfortranarray(values.astype(np.int32, copy=False)), order="F")
        else:
            payload = np.ravel(np.asfortranarray(values.astype(np.float64, copy=False)), order="F")
    else:
        nrow, ncol = (int(dim[0]), int(dim[1]))
        flat = np.asarray(values)
        if flat.ndim == 1:
            payload = np.ascontiguousarray(flat)
        else:
            payload = np.ravel(np.asfortranarray(flat), order="F")
        if integer:
            payload = np.ascontiguousarray(payload, dtype=np.int32)
        else:
            payload = np.ascontiguousarray(payload, dtype=np.float64)
    mode = "integer" if integer else "double"
    script = _r_script(kind, nrow, ncol, rows, cols, mode, lag, differences)
    result = subprocess.run(
        ["Rscript", "-e", script],
        input=payload.tobytes(),
        check=False,
        capture_output=True,
    )
    if result.returncode != 0:
        raise AssertionError(result.stderr.decode())
    lines = result.stdout.decode().splitlines()
    out_nrow, out_ncol, out_mode = lines[0].split()
    out_nrow = int(out_nrow)
    out_ncol = int(out_ncol)
    length = out_nrow * out_ncol
    if length == 0:
        dtype = np.int32 if out_mode == "integer" else np.float64
        return np.zeros((out_nrow, out_ncol), dtype=dtype)
    raw = bytes.fromhex(lines[1])
    if out_mode == "integer":
        flat = np.frombuffer(raw, dtype="<i4").copy()
    else:
        flat = np.frombuffer(raw, dtype="<f8").copy()
    assert flat.size == length
    return np.reshape(flat, (out_nrow, out_ncol), order="F")


def _r_script(kind, nrow, ncol, rows, cols, mode, lag, differences):
    fn = "rowDiffs" if kind == "row" else "colDiffs"
    rows_r = _r_index(rows)
    cols_r = _r_index(cols)
    if mode == "double":
        reader = f'readBin(input, "double", {nrow * ncol})'
        writer = "as.numeric(res)"
    else:
        reader = f'readBin(input, "integer", {nrow * ncol})'
        writer = "as.integer(res)"
    material = f"matrix({reader}, nrow = {nrow}, ncol = {ncol})"
    return textwrap.dedent(
        f"""
        library(matrixStats)
        input <- file("stdin", "rb")
        x <- {material}
        close(input)
        res <- {fn}(x, rows = {rows_r}, cols = {cols_r}, lag = {int(lag)}L, differences = {int(differences)}L, dim. = c({nrow}L, {ncol}L), useNames = FALSE)
        cat(nrow(res), ncol(res), storage.mode(res), "\\n", sep = " ")
        if (length(res)) {{
          raw <- writeBin({writer}, raw())
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
    if arr.dtype == object:
        parts = []
        for value in arr.tolist():
            if value is None:
                parts.append("NA")
            elif isinstance(value, (bool, np.bool_)):
                parts.append("TRUE" if bool(value) else "FALSE")
            else:
                parts.append(repr(value))
        return f"c({', '.join(parts)})"
    if arr.dtype == np.bool_:
        flags = ", ".join("TRUE" if flag else "FALSE" for flag in arr.tolist())
        return f"c({flags})"
    if np.issubdtype(arr.dtype, np.floating):
        parts = []
        for value in arr.tolist():
            if np.isnan(value):
                parts.append("NA_real_")
            else:
                parts.append(repr(float(value)))
        return f"c({', '.join(parts)})"
    parts = []
    for value in arr.tolist():
        if int(value) == _NA:
            parts.append("NA_integer_")
        else:
            parts.append(f"{int(value)}L")
    return f"c({', '.join(parts)})"
