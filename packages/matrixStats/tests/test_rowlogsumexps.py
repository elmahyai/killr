"""Checks for rowLogSumExps and colLogSumExps against the installed R package."""

from __future__ import annotations

import subprocess
import textwrap

import numpy as np
import pytest

from matrixstats.rowlogsumexps import colLogSumExps, rowLogSumExps


def test_printed_matrix_matches_log_of_the_sum():
    lx = np.array([[0.0, np.log(2.0)], [0.0, np.log(3.0)]])
    rows = rowLogSumExps(lx)
    cols = colLogSumExps(lx)
    assert _close(rows, [np.log(3.0), np.log(4.0)])
    assert _close(cols, [np.log(2.0), np.log(5.0)])


def test_c_order_and_f_order_agree():
    lx = np.array([[0.0, np.log(2.0)], [0.0, np.log(3.0)]])
    fortran = np.asfortranarray(lx)
    assert _close(rowLogSumExps(lx), rowLogSumExps(fortran))
    assert _close(colLogSumExps(lx), colLogSumExps(fortran))


def test_missing_values_and_empty_margins():
    lx = np.array([[np.nan, 2.0], [1.0, 3.0]])
    assert _close(rowLogSumExps(lx, na_rm=True), [2.0, np.log(np.exp(1.0) + np.exp(3.0))])
    dropped = rowLogSumExps(lx, na_rm=False)
    assert np.isnan(dropped[0])
    assert dropped[1] == pytest.approx(np.log(np.exp(1.0) + np.exp(3.0)))

    blank = np.full((2, 2), np.nan)
    assert np.all(rowLogSumExps(blank, na_rm=True) == -np.inf)
    assert np.isnan(rowLogSumExps(blank)).all()
    assert np.all(colLogSumExps(blank, na_rm=True) == -np.inf)

    x = np.array([[0.0, 2.0], [1.0, 3.0]])
    assert rowLogSumExps(x, rows=np.array([], dtype=np.int64)).size == 0
    assert np.all(rowLogSumExps(x, cols=np.array([], dtype=np.int64)) == -np.inf)
    assert np.all(colLogSumExps(x, rows=np.array([], dtype=np.int64)) == -np.inf)
    assert colLogSumExps(x, cols=np.array([], dtype=np.int64)).size == 0
    assert np.all(colLogSumExps(np.zeros((0, 3))) == -np.inf)
    assert np.all(rowLogSumExps(np.zeros((4, 0))) == -np.inf)


def test_subsets_dim_and_index_errors():
    x = np.array([[0.0, 2.0], [1.0, 3.0]])
    assert _close(rowLogSumExps(x, rows=[2, 2], cols=[2]), [3.0, 3.0])
    assert _close(rowLogSumExps(x, rows=[0, 2, 0]), [np.log(np.exp(1.0) + np.exp(3.0))])
    assert _close(rowLogSumExps(x, rows=[-1]), [np.log(np.exp(1.0) + np.exp(3.0))])
    assert _close(rowLogSumExps(x, rows=[False, True]), [np.log(np.exp(1.0) + np.exp(3.0))])
    assert rowLogSumExps(x, rows=False).size == 0
    assert _close(rowLogSumExps(np.array([0.0, 1.0, 2.0, 3.0]), dim=(2, 2)), rowLogSumExps(x))
    assert _close(colLogSumExps(np.array([0.0, 1.0, 2.0, 3.0]), dim=(2, 2)), colLogSumExps(x))

    missing = np.array([np.nan, 2.0])
    na_false = rowLogSumExps(x, rows=missing, na_rm=False)
    na_true = rowLogSumExps(x, rows=missing, na_rm=True)
    assert np.isnan(na_false[0])
    assert na_true[0] == -np.inf
    assert na_false[1] == pytest.approx(na_true[1])

    with pytest.raises(ValueError, match="out of bounds"):
        rowLogSumExps(x, rows=[1, 9])
    with pytest.raises(ValueError, match="negative subscripts"):
        rowLogSumExps(x, rows=[-1, 1])
    with pytest.raises(ValueError, match="logical subscript too long"):
        rowLogSumExps(x, rows=[True, False, True])
    with pytest.raises(ValueError, match="idxs can only be integer, numeric, or logical"):
        rowLogSumExps(x, rows=["a"])
    with pytest.raises(ValueError, match="does not match length"):
        rowLogSumExps(np.array([1.0, 2.0, 3.0]), dim=(2, 2))


def test_large_values_do_not_overflow():
    lx = np.array([[1000.01, 1000.02]])
    assert rowLogSumExps(lx)[0] == pytest.approx(1000.7081596805078)
    lx = np.array([[-1000.01, -1000.02]])
    assert rowLogSumExps(lx)[0] == pytest.approx(-999.32184031949214)


def test_matches_r_on_edges_and_the_timing_shape():
    lx = np.array([[0.0, np.log(2.0)], [0.0, np.log(3.0)]])
    _assert_r(lx, "row")
    _assert_r(lx, "col")

    dirty = np.array([[np.nan, 2.0], [1.0, 3.0]])
    _assert_r(dirty, "row", na_rm=False)
    _assert_r(dirty, "row", na_rm=True)
    _assert_r(dirty, "col", na_rm=False)
    _assert_r(dirty, "col", na_rm=True)
    _assert_r(np.full((2, 2), np.nan), "row", na_rm=True)
    _assert_r(np.full((2, 2), np.nan), "col", na_rm=False)

    small = np.array([[0.0, 2.0], [1.0, 3.0]])
    _assert_r(small, "row", rows=np.array([], dtype=np.int64))
    _assert_r(small, "col", cols=np.array([], dtype=np.int64))
    _assert_r(small, "row", cols=np.array([], dtype=np.int64))
    _assert_r(small, "col", rows=np.array([], dtype=np.int64))
    _assert_r(small, "row", rows=np.array([2, 2]), cols=np.array([1, 1]))
    _assert_r(small, "row", rows=np.array([0, 2, 0]))
    _assert_r(small, "row", rows=np.array([-1]))
    _assert_r(small, "row", rows=np.array([False, True]))
    _assert_r(small, "row", rows=np.array([np.nan, 2.0]), na_rm=False)
    _assert_r(small, "row", rows=np.array([np.nan, 2.0]), na_rm=True)
    _assert_r(small, "col", cols=np.array([np.nan, 1.0]), na_rm=True)
    _assert_r(np.array([0.0, 1.0, 2.0, 3.0]), "row", dim=(2, 2))
    _assert_r(np.array([0.0, 1.0, 2.0, 3.0]), "col", dim=(2, 2))
    _assert_r(np.zeros((0, 3)), "col")
    _assert_r(np.zeros((4, 0)), "row")
    _assert_r(np.array([[0.0, np.inf], [1.0, 2.0]]), "row")
    _assert_r(np.array([[-np.inf, 5.0], [-np.inf, -np.inf]]), "row")

    rng = np.random.default_rng(1)
    big = np.log(np.abs(rng.standard_normal((400, 250))) + 1e-12)
    _assert_r(big, "row", na_rm=False)
    _assert_r(big, "col", na_rm=False)


def _assert_r(lx, kind, rows=None, cols=None, na_rm=False, dim=None):
    reference = _r_values(lx, kind, rows=rows, cols=cols, na_rm=na_rm, dim=dim)
    if kind == "row":
        got = rowLogSumExps(lx, rows=rows, cols=cols, na_rm=na_rm, dim=dim)
    else:
        got = colLogSumExps(lx, rows=rows, cols=cols, na_rm=na_rm, dim=dim)
    _close(got, reference)


def _close(got, reference):
    got = np.asarray(got, dtype=np.float64)
    reference = np.asarray(reference, dtype=np.float64)
    assert got.shape == reference.shape
    assert np.array_equal(np.isnan(got), np.isnan(reference))
    finite = np.isfinite(got) & np.isfinite(reference)
    if np.any(finite):
        assert np.max(np.abs(got[finite] - reference[finite])) <= 1e-8
    other = ~np.isnan(got)
    if np.any(other & ~finite):
        assert np.array_equal(got[other & ~finite], reference[other & ~finite])
    return True


def _r_values(lx, kind, rows=None, cols=None, na_rm=False, dim=None):
    values = np.asarray(lx, dtype=np.float64)
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
    fn = "rowLogSumExps" if kind == "row" else "colLogSumExps"
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
    values = ", ".join(str(int(v)) for v in arr.tolist())
    return f"c({values})"
