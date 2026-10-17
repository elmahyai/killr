"""Checks for x_OP_y and t_tx_OP_y against matrixStats."""

from __future__ import annotations

import subprocess
import textwrap
import warnings

import numpy as np
import pytest

from matrixstats.x_op_y import t_tx_OP_y, x_OP_y

_NA = np.iinfo(np.int32).min
_NA_BITS = np.uint64(0x7FF00000000007A2)


def _r_na():
    return np.uint64(_NA_BITS).view(np.float64)


def _is_r_na(value):
    bits = np.asarray(value, dtype=np.float64).view(np.uint64)
    return bool(np.isnan(value) and (bits & np.uint64(0xFFFFFFFF)) == np.uint64(0x7A2))


def test_manual_example_matches_the_printed_matrix():
    na = _r_na()
    x = np.array([[1.0, na], [2.0, 5.0], [3.0, 6.0]])
    columns = x_OP_y(x, np.array([1, 2]), "+")
    rows = t_tx_OP_y(x, np.array([1, 2, 3]), "+")
    assert columns.dtype == np.float64
    assert columns.shape == (3, 2)
    assert rows.shape == (3, 2)
    assert columns[0, 0] == 2.0 and columns[1, 0] == 4.0 and columns[2, 0] == 4.0
    assert columns[1, 1] == 6.0 and columns[2, 1] == 8.0
    assert _is_r_na(columns[0, 1])
    assert rows[0, 0] == 2.0 and rows[1].tolist() == [5.0, 6.0] and rows[2].tolist() == [5.0, 9.0]
    assert _is_r_na(rows[0, 1])
    _assert_r(x, np.array([1, 2]), "+")
    _assert_r(x, np.array([1, 2, 3]), "+", by_row=True)


def test_operators_na_rm_commute_and_both_orders_match_r():
    x = np.array([[1.0, 4.0], [np.nan, 5.0], [3.0, 6.0]])
    y = np.array([10.0, np.nan, 30.0])
    for op in ("+", "-", "*", "/"):
        for na_rm in (False, True):
            for commute in (False, True):
                _assert_r(x, y, op, na_rm=na_rm, commute=commute)
                _assert_r(x, y, op, by_row=True, na_rm=na_rm, commute=commute)

    xi = np.array([[1, 4], [_NA, 5], [3, 6]], dtype=np.int32)
    yi = np.array([2, _NA, 4], dtype=np.int32)
    for op in ("+", "-", "*", "/"):
        for na_rm in (False, True):
            _assert_r(xi, yi, op, na_rm=na_rm)
            _assert_r(xi, yi, op, by_row=True, na_rm=na_rm)
    _assert_r(xi, yi, "-", commute=True)
    _assert_r(xi, np.array([8, 9], dtype=np.int32), "*", by_row=True, commute=True)


def test_logical_mixed_types_recycling_and_subsets_match_r():
    logical = np.array([[True, False], [False, True], [True, False]])
    _assert_r(logical, np.array([True, False, True]), "+")
    _assert_r(logical, np.array([False, True]), "/", by_row=True)
    _assert_r(logical, np.array([1, 0, 1], dtype=np.int32), "*")

    mixed_x = np.array([[_r_na(), 2.0], [4.0, 5.0]])
    mixed_y = np.array([_NA, 3], dtype=np.int32)
    _assert_r(mixed_x, mixed_y, "+", na_rm=True)
    _assert_r(mixed_x, mixed_y, "*", na_rm=True)
    _assert_r(
        np.array([[1, _NA], [4, 5]], dtype=np.int32),
        np.array([_r_na(), 3.0]),
        "+",
        na_rm=False,
    )

    base = np.arange(1, 13, dtype=np.float64).reshape(4, 3, order="F")
    _assert_r(base, np.array([10.0]), "+")
    _assert_r(base, np.array([1.0, 2.0, 3.0]), "-", by_row=True)
    _assert_r(np.ascontiguousarray(base), np.array([1.0, 2.0, 3.0, 4.0]), "*")
    _assert_r(base[::2, :], np.array([1.0, 2.0]), "/")
    _assert_r(base, np.arange(1, 5), "+", xrows=np.array([2, 4]), xcols=np.array([3, 1]))
    _assert_r(base, np.array([9.0, 8.0, 7.0]), "*", yidxs=np.array([3, 1, 2]), by_row=True)
    _assert_r(base, np.array([1.0, 2.0]), "+", xrows=np.array([-2]))
    _assert_r(base, np.array([1.0, 2.0, 3.0, 4.0]), "-", xcols=np.array([0, 2, 0]))
    _assert_r(base, np.array([4.0, 5.0]), "*", yidxs=np.array([1.9, 8.0]))
    _assert_r(base, np.array([1.0, 2.0, 3.0, 4.0]), "+", xrows=[True, None, False])
    _assert_r(
        np.array([[1, 5], [2, 6], [3, 7], [4, 8]], dtype=np.int32),
        np.array([_NA, 3, 4], dtype=np.int32),
        "+",
        xcols=np.array([1, _NA], dtype=np.int32),
    )


def test_integer_overflow_warns_and_other_operators_stay_in_range():
    x = np.array([[2_000_000_000], [1]], dtype=np.int32)
    y = np.array([2_000_000_000], dtype=np.int32)
    with pytest.warns(RuntimeWarning, match="Integer overflow"):
        got = x_OP_y(x, y, "+")
    assert got.dtype == np.int32
    assert got.tolist() == [[_NA], [2_000_000_001]]
    _assert_r(x, y, "+")

    exact = np.array([[-2_147_483_647]], dtype=np.int32)
    with pytest.warns(RuntimeWarning, match="\\[-2147483647,2147483647\\]"):
        wrapped = x_OP_y(exact, np.array([-1], dtype=np.int32), "+")
    assert wrapped.tolist() == [[_NA]]

    both = np.array([[_NA]], dtype=np.int32)
    with pytest.warns(RuntimeWarning, match="Integer overflow"):
        added = x_OP_y(both, both.reshape(-1), "+", na_rm=True)
    assert added.tolist() == [[_NA]]
    with warnings.catch_warnings():
        warnings.simplefilter("error", RuntimeWarning)
        quiet = x_OP_y(both, both.reshape(-1), "+")
    assert quiet.tolist() == [[_NA]]

    divided = x_OP_y(np.array([[1, 0], [-1, 5]], dtype=np.int32), np.array([2, 0], dtype=np.int32), "/")
    assert divided.dtype == np.float64
    _assert_r(np.array([[1, 0], [-1, 5]], dtype=np.int32), np.array([2, 0], dtype=np.int32), "/")
    _assert_r(np.array([[1, 0], [-1, 5]], dtype=np.int32), np.array([2, 0], dtype=np.int32), "/", by_row=True)


def test_argument_errors():
    x = np.array([[1.0, 2.0], [3.0, 4.0]])
    y = np.array([1.0, 2.0])
    with pytest.raises(ValueError, match="subscript out of bounds"):
        x_OP_y(x, y, "+", xrows=[1, 9])
    with pytest.raises(ValueError, match="negative subscripts"):
        t_tx_OP_y(x, y, "-", xcols=[-1, 1])
    with pytest.raises(ValueError, match="logical subscript too long"):
        x_OP_y(x, y, "*", xrows=[True, False, True])
    with pytest.raises(ValueError, match="dim."):
        x_OP_y(np.array([1.0, 2.0, 3.0]), y, "+")
    with pytest.raises(ValueError, match="not 'character'"):
        x_OP_y(np.array([["a", "b"]]), y, "+")
    with pytest.raises(ValueError, match="Unknown value of argument 'OP'"):
        x_OP_y(x, y, "plus")
    with pytest.raises(ValueError, match="Unknown value on argument 'OP': 5L"):
        t_tx_OP_y(x, y, 5)
    with pytest.raises(ValueError, match="length zero"):
        x_OP_y(x, np.array([], dtype=np.float64), "+")
    with pytest.raises(ValueError, match="na.rm"):
        x_OP_y(x, y, "+", na_rm=float("nan"))


def _assert_r(
    x,
    y,
    op,
    by_row=False,
    xrows=None,
    xcols=None,
    yidxs=None,
    commute=False,
    na_rm=False,
):
    reference = _r_op(
        x,
        y,
        op,
        by_row=by_row,
        xrows=xrows,
        xcols=xcols,
        yidxs=yidxs,
        commute=commute,
        na_rm=na_rm,
    )
    fn = t_tx_OP_y if by_row else x_OP_y
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        got = fn(
            x,
            y,
            op,
            xrows=xrows,
            xcols=xcols,
            yidxs=yidxs,
            commute=commute,
            na_rm=na_rm,
        )
    got = np.asarray(got)
    assert got.shape == reference.shape
    if reference.dtype == np.int32:
        assert got.dtype == np.int32
        assert np.array_equal(got, reference)
        return
    assert got.dtype == np.float64
    _assert_float(got, reference)


def _assert_float(got, reference):
    got = np.ascontiguousarray(got)
    reference = np.ascontiguousarray(reference)
    finite = np.isfinite(got) & np.isfinite(reference)
    if np.any(finite):
        diff = np.abs(got[finite] - reference[finite])
        assert np.all(diff <= 1e-8)
    rest = ~finite
    if np.any(rest):
        assert np.array_equal(got.view(np.uint64)[rest], reference.view(np.uint64)[rest])


def _r_op(x, y, op, by_row, xrows, xcols, yidxs, commute, na_rm):
    x_values = np.asarray(x)
    y_values = np.asarray(y)
    x_logical = x_values.dtype == np.bool_
    y_logical = y_values.dtype == np.bool_
    x_integer = (np.issubdtype(x_values.dtype, np.integer) and not x_logical) or x_logical
    y_integer = (np.issubdtype(y_values.dtype, np.integer) and not y_logical) or y_logical
    if x_values.ndim != 2:
        raise AssertionError("x must be a matrix")
    nrow, ncol = x_values.shape
    if x_logical:
        x_payload = np.ravel(np.asfortranarray(x_values.astype(np.int32)), order="F")
    elif x_integer:
        x_payload = np.ravel(np.asfortranarray(x_values.astype(np.int32, copy=False)), order="F")
    else:
        x_payload = np.ravel(np.asfortranarray(x_values.astype(np.float64, copy=False)), order="F")
    if y_values.ndim == 0:
        y_values = y_values.reshape(1)
    elif y_values.ndim == 2:
        y_values = np.ravel(np.asfortranarray(y_values), order="F")
    if y_logical:
        y_payload = np.ascontiguousarray(y_values.astype(np.int32))
    elif y_integer:
        y_payload = np.ascontiguousarray(y_values.astype(np.int32, copy=False))
    else:
        y_payload = np.ascontiguousarray(y_values.astype(np.float64, copy=False))
    script = _r_script(
        nrow,
        ncol,
        y_payload.size,
        "integer" if x_integer else "double",
        "integer" if y_integer else "double",
        "logical" if x_logical else None,
        "logical" if y_logical else None,
        op,
        by_row,
        xrows,
        xcols,
        yidxs,
        commute,
        na_rm,
    )
    result = subprocess.run(
        ["Rscript", "-e", script],
        input=x_payload.tobytes() + y_payload.tobytes(),
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


def _r_script(
    nrow,
    ncol,
    ny,
    x_mode,
    y_mode,
    x_storage,
    y_storage,
    op,
    by_row,
    xrows,
    xcols,
    yidxs,
    commute,
    na_rm,
):
    fn = "t_tx_OP_y" if by_row else "x_OP_y"
    x_reader = f'readBin(input, "{"integer" if x_mode == "integer" else "double"}", {nrow * ncol})'
    y_reader = f'readBin(input, "{"integer" if y_mode == "integer" else "double"}", {ny})'
    x_mode_line = ""
    y_mode_line = ""
    if x_storage == "logical":
        x_mode_line = 'storage.mode(x) <- "logical"'
    if y_storage == "logical":
        y_mode_line = 'storage.mode(y) <- "logical"'
    return textwrap.dedent(
        f"""
        library(matrixStats)
        input <- file("stdin", "rb")
        x <- matrix({x_reader}, nrow = {nrow}, ncol = {ncol})
        y <- {y_reader}
        close(input)
        {x_mode_line}
        {y_mode_line}
        res <- {fn}(x, y, OP = "{op}", xrows = {_r_index(xrows)}, xcols = {_r_index(xcols)}, yidxs = {_r_index(yidxs)}, commute = {"TRUE" if commute else "FALSE"}, na.rm = {"TRUE" if na_rm else "FALSE"})
        cat(nrow(res), ncol(res), storage.mode(res), "\\n", sep = " ")
        if (length(res)) {{
          raw <- writeBin(if (storage.mode(res) == "integer") as.integer(res) else as.numeric(res), raw())
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
