"""Checks for rowCumsums and colCumsums against the printed matrix and R."""

from __future__ import annotations

import subprocess
import textwrap

import numpy as np
import pytest

from matrixstats.rowcumsums import colCumsums, rowCumsums

_NA = np.iinfo(np.int32).min


def test_full_sums_match_the_printed_matrix():
    x = np.array(
        [[1, 5, 9], [2, 6, 10], [3, 7, 11], [4, 8, 12]],
        dtype=np.int32,
    )
    assert rowCumsums(x).dtype == np.int32
    assert rowCumsums(x).tolist() == [
        [1, 6, 15],
        [2, 8, 18],
        [3, 10, 21],
        [4, 12, 24],
    ]
    assert colCumsums(x).tolist() == [
        [1, 5, 9],
        [3, 11, 19],
        [6, 18, 30],
        [10, 26, 42],
    ]
    assert rowCumsums(x).shape == x.shape
    assert colCumsums(x, use_names=False).shape == x.shape


def test_logical_input_returns_integer():
    x = np.array([[True, False, True], [False, True, False]])
    rows = rowCumsums(x)
    cols = colCumsums(x)
    assert rows.dtype == np.int32
    assert cols.dtype == np.int32
    assert rows.tolist() == [[1, 1, 2], [0, 1, 1]]
    assert cols.tolist() == [[1, 0, 1], [1, 1, 1]]


def test_double_na_propagates_and_integer_na_is_the_sentinel():
    x = np.array([[1.0, 3.0, 5.0], [np.nan, 4.0, np.nan]])
    rows = rowCumsums(x)
    cols = colCumsums(x)
    assert rows.tolist()[0] == [1.0, 4.0, 9.0]
    assert np.isnan(rows[1]).all()
    assert cols[:, 0].tolist()[0] == 1.0
    assert np.isnan(cols[1, 0])
    assert cols[:, 1].tolist() == [3.0, 7.0]
    assert np.isnan(cols[1, 2])

    xi = np.array([[1, 3, 5], [_NA, 4, _NA]], dtype=np.int32)
    assert rowCumsums(xi)[1].tolist() == [_NA, _NA, _NA]
    assert colCumsums(xi).tolist() == [[1, 3, 5], [_NA, 7, _NA]]


def test_integer_overflow_warns_and_sets_na():
    x = np.array([[2_000_000_000, 2_000_000_000]], dtype=np.int32)
    with pytest.warns(UserWarning, match="Integer overflow"):
        got = rowCumsums(x)
    assert got.tolist() == [[2_000_000_000, _NA]]


def test_subsets_dim_and_empty_margins():
    x = np.array(
        [[1.0, 5.0, 9.0], [2.0, 6.0, 10.0], [3.0, 7.0, 11.0], [4.0, 8.0, 12.0]]
    )
    assert rowCumsums(x, rows=[2, 4]).tolist() == [[2.0, 8.0, 18.0], [4.0, 12.0, 24.0]]
    assert colCumsums(x, cols=[3, 1]).tolist() == [
        [9.0, 1.0],
        [19.0, 3.0],
        [30.0, 6.0],
        [42.0, 10.0],
    ]
    assert rowCumsums(x, rows=[1, 1], cols=[3, 1, 2]).tolist() == [
        [9.0, 10.0, 15.0],
        [9.0, 10.0, 15.0],
    ]
    assert rowCumsums(x, rows=[-2]).shape == (3, 3)
    assert colCumsums(x, cols=[0, 2, 0]).shape == (4, 1)
    assert rowCumsums(x, rows=np.array([], dtype=np.int64)).shape == (0, 3)
    assert colCumsums(x, cols=np.array([], dtype=np.int64)).shape == (4, 0)

    flat = np.arange(1, 13)
    assert rowCumsums(flat, dim=(4, 3)).tolist() == rowCumsums(x).tolist()
    assert colCumsums(flat, dim=np.array([4, 3], dtype=np.int32)).tolist() == colCumsums(x).tolist()


def test_index_errors():
    x = np.array([[1.0, 5.0], [2.0, 6.0]])
    with pytest.raises(ValueError, match="out of bounds"):
        rowCumsums(x, rows=[1, 9])
    with pytest.raises(ValueError, match="negative subscripts"):
        rowCumsums(x, cols=[-1, 1])
    with pytest.raises(ValueError, match="logical subscript too long"):
        colCumsums(x, rows=[True, False, True])
    with pytest.raises(ValueError, match="dim"):
        rowCumsums(np.array([1.0, 2.0, 3.0]))


def test_matches_r_on_subsets_na_and_the_timing_shape():
    x = np.array(
        [[1, 5, 9], [2, 6, 10], [3, 7, 11], [4, 8, 12]],
        dtype=np.int32,
    )
    _assert_r(x, "row")
    _assert_r(x, "col")
    _assert_r(x, "row", rows=np.array([2, 4]))
    _assert_r(x, "col", cols=np.array([3, 1]))
    _assert_r(np.arange(1, 13), "row", dim=(4, 3))
    _assert_r(np.arange(1, 13), "col", dim=(4, 3))

    logical = np.array([[True, False, True], [False, True, False]])
    _assert_r(logical, "row")
    _assert_r(logical, "col")

    dirty = np.array([[1.0, 3.0, 5.0], [np.nan, 4.0, np.nan]])
    _assert_r(dirty, "row")
    _assert_r(dirty, "col")
    _assert_r(dirty, "row", rows=np.array([np.nan, 2.0]))
    _assert_r(x, "row", cols=np.array([1, _NA], dtype=np.int32))

    rng = np.random.default_rng(1)
    big = rng.standard_normal((400, 250))
    _assert_r(big, "row")
    _assert_r(big, "col")
    _assert_r(big, "row", rows=np.array([1, 50, 400]))
    _assert_r(big, "col", cols=np.array([2, 10, 250]))
    one_na = big.copy()
    one_na[3, 7] = np.nan
    _assert_r(one_na, "row")
    _assert_r(one_na, "col")


def _assert_r(x, kind, rows=None, cols=None, dim=None):
    reference = _r_cumsums(x, kind, rows=rows, cols=cols, dim=dim)
    if kind == "row":
        got = rowCumsums(x, rows=rows, cols=cols, dim=dim, use_names=False)
    else:
        got = colCumsums(x, rows=rows, cols=cols, dim=dim, use_names=False)
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


def _r_cumsums(x, kind, rows=None, cols=None, dim=None):
    values = np.asarray(x)
    logical = values.dtype == np.bool_
    integer = np.issubdtype(values.dtype, np.integer) and not logical
    if dim is None:
        nrow, ncol = values.shape
        if logical:
            payload = np.where(np.asfortranarray(values), 1, 0).astype(np.int32, copy=False)
            payload = np.ravel(payload, order="F")
        elif integer:
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
        if logical:
            payload = np.where(payload, 1, 0).astype(np.int32, copy=False)
        elif integer:
            payload = np.ascontiguousarray(payload, dtype=np.int32)
        else:
            payload = np.ascontiguousarray(payload, dtype=np.float64)
    mode = "logical" if logical else "integer" if integer else "double"
    script = _r_script(kind, nrow, ncol, rows, cols, mode)
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
        flat = np.frombuffer(raw, dtype=np.int32).copy()
    else:
        flat = np.frombuffer(raw, dtype=np.float64).copy()
    assert flat.size == length
    return np.reshape(flat, (out_nrow, out_ncol), order="F")


def _r_script(kind, nrow, ncol, rows, cols, mode):
    fn = "rowCumsums" if kind == "row" else "colCumsums"
    rows_r = _r_index(rows)
    cols_r = _r_index(cols)
    if mode == "double":
        reader = f'readBin(input, "double", {nrow * ncol})'
        writer = "as.numeric(res)"
    else:
        reader = f'readBin(input, "integer", {nrow * ncol})'
        writer = "as.integer(res)"
    if mode == "logical":
        material = f"matrix(as.logical({reader}), nrow = {nrow}, ncol = {ncol})"
    else:
        material = f"matrix({reader}, nrow = {nrow}, ncol = {ncol})"
    return textwrap.dedent(
        f"""
        library(matrixStats)
        input <- file("stdin", "rb")
        x <- {material}
        close(input)
        res <- {fn}(x, rows = {rows_r}, cols = {cols_r}, dim. = c({nrow}L, {ncol}L), useNames = FALSE)
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
