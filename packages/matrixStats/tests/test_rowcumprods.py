"""Checks for rowCumprods and colCumprods against R."""

from __future__ import annotations

import struct
import subprocess
import textwrap
import warnings

import numpy as np
import pytest

from matrixstats.rowcumprods import colCumprods, rowCumprods

NA_INTEGER = np.int32(np.iinfo(np.int32).min)
NA_REAL = np.array(struct.unpack("<d", bytes.fromhex("a20700000000f07f"))[0])[()]


def test_manual_integer_example():
    x = np.array(
        [[1, 5, 9], [2, 6, 10], [3, 7, 11], [4, 8, 12]],
        dtype=np.int32,
    )
    rows = rowCumprods(x)
    cols = colCumprods(x)
    assert rows.dtype == np.int32
    assert cols.dtype == np.int32
    assert rows.tolist() == [
        [1, 5, 45],
        [2, 12, 120],
        [3, 21, 231],
        [4, 32, 384],
    ]
    assert cols.tolist() == [
        [1, 5, 9],
        [2, 30, 90],
        [6, 210, 990],
        [24, 1680, 11880],
    ]


def test_logical_input_returns_integer():
    x = np.array([[True, False, True], [True, True, False]])
    rows = rowCumprods(x)
    cols = colCumprods(x)
    assert rows.dtype == np.int32
    assert cols.dtype == np.int32
    assert rows.tolist() == [[1, 0, 0], [1, 1, 0]]
    assert cols.tolist() == [[1, 0, 1], [1, 0, 0]]


def test_zero_negative_and_na():
    x = np.array(
        [[2, 0, -3], [NA_INTEGER, 4, 5], [-2, -2, 3]],
        dtype=np.int32,
    )
    rows = rowCumprods(x)
    cols = colCumprods(x)
    assert rows.tolist() == [
        [2, 0, 0],
        [int(NA_INTEGER), int(NA_INTEGER), int(NA_INTEGER)],
        [-2, 4, 12],
    ]
    assert cols.tolist() == [
        [2, 0, -3],
        [int(NA_INTEGER), 0, -15],
        [int(NA_INTEGER), 0, -45],
    ]
    _assert_r(x, "row")
    _assert_r(x, "col")

    real = np.array(
        [[1.0, 0.0, -2.0], [NA_REAL, -3.0, 4.0], [2.0, -0.0, 5.0]],
        dtype=np.float64,
    )
    _assert_r(real, "row")
    _assert_r(real, "col")


def test_integer_overflow_becomes_na():
    x = np.array([[46341, 46341, 1]], dtype=np.int32)
    with pytest.warns(UserWarning, match="Integer overflow"):
        got = rowCumprods(x)
    assert got.tolist() == [[46341, int(NA_INTEGER), int(NA_INTEGER)]]

    edge = np.array([[46340, 46340]], dtype=np.int32)
    assert rowCumprods(edge).tolist() == [[46340, 2147395600]]

    down = np.array([[46341], [46341]], dtype=np.int32)
    with pytest.warns(UserWarning, match="NA_integer_"):
        assert colCumprods(down).tolist() == [[46341], [int(NA_INTEGER)]]

    _assert_r(x, "row")
    _assert_r(down, "col")
    _assert_r(np.array([[1073741824, -2]], dtype=np.int32), "row")
    _assert_r(np.array([[2147483647, -1]], dtype=np.int32), "row")


def test_subsets_dim_and_use_names():
    x = np.array([[1, 3, 5], [2, 4, 6]], dtype=np.int32)
    assert rowCumprods(x, rows=[2, 2], cols=[3, 1]).tolist() == [[6, 12], [6, 12]]
    assert rowCumprods(x, rows=[0, 2, 0]).tolist() == [[2, 8, 48]]
    assert rowCumprods(x, rows=[-1]).tolist() == [[2, 8, 48]]
    assert rowCumprods(x, rows=[False, True]).tolist() == [[2, 8, 48]]
    assert rowCumprods(x, rows=True).tolist() == rowCumprods(x).tolist()
    assert rowCumprods(x, rows=False).shape == (0, 3)
    assert colCumprods(x, cols=np.array([], dtype=np.int64)).shape == (2, 0)
    assert rowCumprods(x, use_names=False).tolist() == rowCumprods(x, use_names=True).tolist()

    flat = np.array([1, 2, 3, 4, 5, 6], dtype=np.int32)
    assert rowCumprods(flat, dim=(2, 3)).tolist() == [[1, 3, 15], [2, 8, 48]]
    assert colCumprods(flat, dim=np.array([2, 3], dtype=np.int32)).tolist() == [
        [1, 3, 5],
        [2, 12, 30],
    ]
    assert rowCumprods(flat, dim=(2.9, 3.2)).tolist() == [[1, 3, 15], [2, 8, 48]]


def test_storage_order_does_not_change_the_printed_result():
    x = np.array([[1.5, 0.0, -2.0], [4.0, -0.5, 3.0]], dtype=np.float64)
    rows_c = rowCumprods(np.ascontiguousarray(x))
    rows_f = rowCumprods(np.asfortranarray(x))
    cols_c = colCumprods(np.ascontiguousarray(x))
    cols_f = colCumprods(np.asfortranarray(x))
    assert np.array_equal(rows_c, rows_f)
    assert np.array_equal(cols_c, cols_f)
    _assert_r(x, "row")
    _assert_r(x, "col")


def test_errors():
    x = np.array([[1.0, 2.0], [3.0, 4.0]])
    with pytest.raises(ValueError, match="out of bounds"):
        rowCumprods(x, rows=[1, 9])
    with pytest.raises(ValueError, match="negative subscripts"):
        rowCumprods(x, rows=[-1, 1])
    with pytest.raises(ValueError, match="logical subscript too long"):
        rowCumprods(x, rows=[True, False, True])
    with pytest.raises(ValueError, match="dim\\."):
        rowCumprods(np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0]), dim=(2, 2))
    with pytest.raises(ValueError, match="character"):
        rowCumprods(np.array([["a", "b"], ["c", "d"]]))
    with pytest.raises(ValueError, match="useNames"):
        rowCumprods(x, use_names=1)


def test_matches_r_on_edges_and_the_timing_shape():
    rng = np.random.default_rng(1)
    x = rng.uniform(0.5, 1.5, size=(200, 80))
    _assert_r(x, "row")
    _assert_r(x, "col")
    _assert_r(x, "row", rows=np.array([1, 50, 200]))
    _assert_r(x, "col", cols=np.array([2, 10, 80]))
    _assert_r(x, "row", rows=np.array([1.9, 200.0]))
    _assert_r(x, "row", cols=np.array([-1, -80]))

    small = np.array([[1.0, 0.0, np.inf], [-2.0, np.nan, -0.0]])
    _assert_r(small, "row")
    _assert_r(small, "col")
    _assert_r(np.array([[NA_REAL, 2.0, 3.0]]), "row")
    _assert_r(np.array([[NA_REAL], [2.0]]), "col")
    _assert_r(np.array([[np.inf, -2.0, 0.0]]), "row")
    _assert_r(np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0]), "row", dim=(2, 3))
    _assert_r(np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0]), "col", dim=(2, 3))
    _assert_r(np.zeros((0, 3)), "row")
    _assert_r(np.zeros((4, 0)), "col")
    _assert_r(
        np.array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]]),
        "row",
        rows=np.array([np.nan, 2.0]),
    )


def _assert_r(x, kind, rows=None, cols=None, dim=None):
    reference = _r_cumprods(x, kind, rows=rows, cols=cols, dim=dim)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        if kind == "row":
            got = rowCumprods(x, rows=rows, cols=cols, dim=dim)
        else:
            got = colCumprods(x, rows=rows, cols=cols, dim=dim)
    _close(got, reference)


def _close(got, reference):
    got = np.asarray(got)
    reference = np.asarray(reference)
    assert got.shape == reference.shape
    if np.issubdtype(reference.dtype, np.integer):
        assert np.issubdtype(got.dtype, np.integer)
        assert np.array_equal(got.astype(np.int32), reference.astype(np.int32))
        return
    g = np.asarray(got, dtype=np.float64)
    r = np.asarray(reference, dtype=np.float64)
    assert np.array_equal(np.isnan(g), np.isnan(r))
    assert np.array_equal(np.isposinf(g), np.isposinf(r))
    assert np.array_equal(np.isneginf(g), np.isneginf(r))
    finite = np.isfinite(g) & np.isfinite(r)
    zeros = finite & (g == 0.0) & (r == 0.0)
    if np.any(zeros):
        assert np.array_equal(np.signbit(g[zeros]), np.signbit(r[zeros]))
    if np.any(finite):
        diff = np.abs(g[finite] - r[finite])
        assert np.all(diff <= 1e-8)


def _r_cumprods(x, kind, rows=None, cols=None, dim=None):
    values = np.asarray(x)
    if values.dtype == np.bool_:
        mode = "logical"
        payload = np.asfortranarray(values.astype(np.int32))
    elif np.issubdtype(values.dtype, np.integer):
        mode = "integer"
        payload = np.asfortranarray(values.astype(np.int32, copy=False))
    else:
        mode = "double"
        payload = np.asfortranarray(np.asarray(values, dtype=np.float64))
    if dim is None:
        if values.ndim != 2:
            raise AssertionError("dim required")
        nrow, ncol = values.shape
        if values.ndim == 2 and mode != "logical":
            payload = np.asfortranarray(payload)
        flat = np.ravel(payload, order="F")
    else:
        nrow, ncol = int(dim[0]), int(dim[1])
        flat = np.asarray(payload).reshape(-1)
        if mode == "double":
            flat = np.ascontiguousarray(flat, dtype=np.float64)
        else:
            flat = np.ascontiguousarray(flat, dtype=np.int32)
    script = _r_script(kind, mode, nrow, ncol, rows, cols)
    result = subprocess.run(
        ["Rscript", "-e", script],
        input=flat.tobytes(),
        check=False,
        capture_output=True,
    )
    if result.returncode != 0:
        raise AssertionError(result.stderr.decode())
    lines = result.stdout.decode().splitlines()
    storage = lines[0]
    out_nrow, out_ncol = (int(part) for part in lines[1].split())
    if out_nrow * out_ncol == 0:
        if storage == "integer":
            return np.zeros((out_nrow, out_ncol), dtype=np.int32)
        return np.zeros((out_nrow, out_ncol), dtype=np.float64)
    raw = bytes.fromhex(lines[2])
    if storage == "integer":
        out = np.frombuffer(raw, dtype=np.int32).copy()
    else:
        out = np.frombuffer(raw, dtype=np.float64).copy()
    return np.reshape(out, (out_nrow, out_ncol), order="F")


def _r_script(kind, mode, nrow, ncol, rows, cols):
    fn = "rowCumprods" if kind == "row" else "colCumprods"
    rows_r = _r_index(rows)
    cols_r = _r_index(cols)
    reader = "double" if mode == "double" else "integer"
    logical = "x <- as.logical(x)\n" if mode == "logical" else ""
    return textwrap.dedent(
        f"""
        library(matrixStats)
        input <- file("stdin", "rb")
        x <- readBin(input, "{reader}", {nrow * ncol})
        close(input)
        {logical}res <- suppressWarnings({fn}(x, rows = {rows_r}, cols = {cols_r}, dim. = c({nrow}L, {ncol}L), useNames = FALSE))
        cat(typeof(res), "\\n", sep = "")
        cat(nrow(res), " ", ncol(res), "\\n", sep = "")
        if (length(res)) {{
          raw <- writeBin(as.vector(res), raw())
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
            elif np.isposinf(value):
                parts.append("Inf")
            elif np.isneginf(value):
                parts.append("-Inf")
            else:
                parts.append(repr(float(value)))
        return f"c({', '.join(parts)})"
    parts = []
    for value in arr.astype(np.int64).tolist():
        if value == int(NA_INTEGER):
            parts.append("NA_integer_")
        else:
            parts.append(f"{int(value)}L")
    return f"c({', '.join(parts)})"
