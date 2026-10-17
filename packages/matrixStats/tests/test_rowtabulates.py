"""Checks for rowTabulates and colTabulates against R."""

from __future__ import annotations

import subprocess
import textwrap
import warnings

import numpy as np
import pytest

from matrixstats.rowtabulates import colTabulates, rowTabulates

_NA = np.int32(-2147483648)


def test_example_matrix_and_explicit_values():
    x = np.tile(np.arange(1, 6, dtype=np.int32), 10).reshape((10, 5), order="F")
    rows = rowTabulates(x)
    cols = colTabulates(x)
    assert rows.dtype == np.int32
    assert cols.dtype == np.int32
    expected_rows = np.zeros((10, 5), dtype=np.int32)
    for index in range(10):
        expected_rows[index, index % 5] = 5
    assert rows.tolist() == expected_rows.tolist()
    assert cols.tolist() == [[2, 2, 2, 2, 2]] * 5
    partial = rowTabulates(x, values=np.arange(1, 4))
    assert partial.tolist() == expected_rows[:, :3].tolist()
    assert np.array_equal(rowTabulates(x, use_names=False), rows)
    assert rowTabulates(x, values=5).tolist() == expected_rows[:, 4:].tolist()


def test_negatives_missing_and_column_order():
    x = np.array([[-2, 3], [0, -2], [_NA, 5]], dtype=np.int32)
    assert rowTabulates(x).tolist() == [
        [1, 0, 1, 0, 0],
        [1, 1, 0, 0, 0],
        [0, 0, 0, 1, 1],
    ]
    assert colTabulates(x).tolist() == [
        [1, 1, 0, 0, 1],
        [1, 0, 1, 1, 0],
    ]
    assert rowTabulates(x, values=[3, 1, 3, None]).tolist() == [
        [1, 0, 1, 0],
        [0, 0, 0, 0],
        [0, 0, 0, 1],
    ]
    assert colTabulates(x, values=[5, -2]).tolist() == [[0, 1], [1, 1]]


def test_coercion_logical_raw_and_empty_shapes():
    x = np.array([[1, 2], [1, 4]], dtype=np.int32)
    with pytest.warns(RuntimeWarning, match="integer range"):
        coerced = rowTabulates(x, values=[1.9, np.inf, -1.2])
    assert coerced.tolist() == [[1, 0, 0], [1, 0, 0]]
    assert rowTabulates(x, values=[True, False]).tolist() == [[1, 0], [1, 0]]

    raw = np.array([[0, 0], [255, 255], [10, 10]], dtype=np.uint8)
    assert rowTabulates(raw).tolist() == [[2, 0, 0], [0, 0, 2], [0, 2, 0]]
    with pytest.warns(RuntimeWarning, match="out-of-range"):
        edged = rowTabulates(raw, values=[256, -1, 10])
    assert edged.tolist() == [[2, 2, 0], [0, 0, 0], [0, 0, 2]]
    assert rowTabulates(raw, rows=[1, None]).tolist() == [[2], [2]]

    logical = np.array([[True, None], [False, True]], dtype=object)
    assert rowTabulates(logical).tolist() == [[0, 1, 1], [1, 1, 0]]
    assert rowTabulates(logical, values=[0, 1, 2]).tolist() == [[0, 1, 1], [1, 1, 1]]

    assert rowTabulates(x, values=np.array([], dtype=np.int32)).shape == (2, 0)
    assert rowTabulates(np.zeros((0, 3), dtype=np.int32)).shape == (0, 0)
    assert colTabulates(np.zeros((0, 3), dtype=np.int32)).shape == (3, 0)
    assert rowTabulates(np.zeros((3, 0), dtype=np.int32)).shape == (3, 0)
    assert colTabulates(np.zeros((3, 0), dtype=np.int32)).shape == (0, 0)
    assert rowTabulates(np.full((2, 3), _NA, dtype=np.int32)).tolist() == [[3], [3]]


def test_subscripts_follow_base_r():
    x = np.arange(1, 13, dtype=np.int32).reshape((4, 3), order="F")
    assert rowTabulates(x, rows=[3, 1]).tolist() == rowTabulates(x[[2, 0], :]).tolist()
    assert colTabulates(x, cols=[3, 1]).shape == (2, 8)
    assert rowTabulates(x, rows=[-2, 0, -2]).shape[0] == 3
    assert rowTabulates(x, rows=0).shape == (0, 0)
    assert rowTabulates(x, rows=[]).shape == (0, 0)
    assert rowTabulates(x, rows=[None, 2]).shape == (2, 4)
    assert rowTabulates(x, rows=[True, False]).shape[0] == 2
    assert rowTabulates(x, rows=[2.9, 0.2, 1]).shape[0] == 2
    with pytest.warns(RuntimeWarning, match="integer range"):
        assert rowTabulates(x, rows=[np.inf]).tolist() == [[3]]
    with pytest.raises(ValueError, match="subscript out of bounds"):
        rowTabulates(x, rows=[5])
    with pytest.raises(ValueError, match="only 0's may be mixed with negative subscripts"):
        rowTabulates(x, rows=[-1, 1])
    with pytest.raises(ValueError, match="logical subscript too long"):
        rowTabulates(x, rows=[True, False, True, False, True])
    with pytest.raises(ValueError, match="only 0's may be mixed with negative subscripts"):
        colTabulates(x, cols=[None, -2])


def test_rejected_types():
    with pytest.raises(ValueError, match="not integer, logical, or raw: double"):
        rowTabulates(np.ones((2, 2)))
    with pytest.raises(ValueError, match="not integer, logical, or raw: character"):
        colTabulates(np.array([["a", "b"]]))
    with pytest.raises(ValueError, match="not integer, logical, or raw: NULL"):
        rowTabulates(None)
    with pytest.raises(ValueError, match="non-numeric matrix extent"):
        rowTabulates(np.arange(5))
    with pytest.raises(ValueError, match="not logical"):
        rowTabulates(np.arange(4, dtype=np.int32).reshape(2, 2), use_names=1)


def test_matches_r_for_both_margins_and_both_value_modes():
    example = np.tile(np.arange(1, 6, dtype=np.int32), 10).reshape((10, 5), order="F")
    _assert_r(example, "row")
    _assert_r(example, "col")
    _assert_r(example, "row", values=[1, 2, 3])

    signed = np.array([[-2, 3], [0, -2], [_NA, 5]], dtype=np.int32)
    _assert_r(signed, "row")
    _assert_r(signed, "col")
    _assert_r(signed, "row", values=[3, 1, 3, None])
    _assert_r(signed, "col", values=[1.9, np.inf])
    _assert_r(signed, "row", values=[True, False])
    _assert_r(signed, "row", values=np.array([1, 10], dtype=np.uint8))
    _assert_r(signed, "row", values=["1", "a", "NA"])
    _assert_r(signed, "row", rows=[3, 1, 3], cols=[2, 2])
    _assert_r(signed, "col", rows=[-1], cols=[1])
    _assert_r(signed, "row", rows=[None, 2])
    _assert_r(signed, "col", cols=[True, False])
    _assert_r(signed, "row", rows=[2.9, 0.2])
    _assert_r(signed, "row", values=[1, 100000])

    logical = np.array(
        [[True, False, None], [False, True, True], [None, False, False]],
        dtype=object,
    )
    _assert_r(logical, "row", mode="logical")
    _assert_r(logical, "col", mode="logical")
    _assert_r(logical, "row", mode="logical", values=[True, False, None])
    _assert_r(logical, "col", mode="logical", values=[0, 1, 2])

    raw = np.array([[0, 16], [10, 255], [15, 0]], dtype=np.uint8)
    _assert_r(raw, "row", mode="raw")
    _assert_r(raw, "col", mode="raw")
    _assert_r(raw, "row", mode="raw", values=np.array([255, 0, 10], dtype=np.uint8))
    _assert_r(raw, "col", mode="raw", values=[0, 10, 256, -1])
    _assert_r(raw, "row", mode="raw", rows=[1, None])

    sparse = np.array([[1, 7, 1], [8, 7, 3], [_NA, 1, 8]], dtype=np.int32)
    _assert_r(sparse, "row", rows=[True, None, False])
    _assert_r(sparse, "col", cols=[-4, 0, -1])
    _assert_r(sparse, "row", rows=0, values=[1, 8, None])
    _assert_r(np.zeros((0, 3), dtype=np.int32), "row")
    _assert_r(np.zeros((0, 3), dtype=np.int32), "col")
    _assert_r(np.zeros((3, 0), dtype=np.int32), "row")
    _assert_r(np.zeros((3, 0), dtype=np.int32), "col")

    rng = np.random.default_rng(1)
    big = rng.integers(0, 12, size=(40, 25), dtype=np.int32)
    big[0, 4] = _NA
    big[7, 9] = _NA
    big[20, 20] = _NA
    _assert_r(big, "row")
    _assert_r(big, "col")
    _assert_r(big, "row", values=[0, 11, 4, None, 4])
    _assert_r(big, "col", rows=[1, 40, 7, 7], cols=[3, 25, 3])


def _assert_r(x, kind, rows=None, cols=None, values=None, mode="integer"):
    reference = _r_tabulate(x, kind, rows, cols, values, mode)
    kwargs = {"rows": rows, "cols": cols, "values": values}
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        got = rowTabulates(x, **kwargs) if kind == "row" else colTabulates(x, **kwargs)
    got = np.asarray(got)
    assert got.dtype == np.int32
    assert got.shape == reference.shape
    assert np.array_equal(got, reference)


def _r_tabulate(x, kind, rows, cols, values, mode):
    payload, nrow, ncol = _payload(x, mode)
    script = _r_script(kind, nrow, ncol, rows, cols, values, mode)
    result = subprocess.run(
        ["Rscript", "-e", script],
        input=payload.tobytes(),
        check=False,
        capture_output=True,
    )
    if result.returncode != 0:
        raise AssertionError(result.stderr.decode() or result.stdout.decode())
    lines = result.stdout.decode().splitlines()
    out_nrow, out_ncol = (int(part) for part in lines[0].split())
    length = out_nrow * out_ncol
    if length == 0:
        return np.zeros((out_nrow, out_ncol), dtype=np.int32)
    flat = np.frombuffer(bytes.fromhex(lines[1]), dtype="<i4").copy()
    assert flat.size == length
    return np.reshape(flat, (out_nrow, out_ncol), order="F")


def _payload(x, mode):
    if mode == "raw":
        array = np.asarray(x, dtype=np.uint8)
        flat = np.ravel(np.asfortranarray(array), order="F")
        return flat, array.shape[0], array.shape[1]
    if mode == "logical":
        array = np.asarray(x, dtype=object)
        flat = np.ravel(np.array(array, dtype=object), order="F")
        codes = np.empty(flat.shape, dtype=np.int32)
        for index, value in enumerate(flat.tolist()):
            if value is None:
                codes[index] = _NA
            else:
                codes[index] = 1 if value else 0
        return codes, array.shape[0], array.shape[1]
    array = np.asarray(x)
    if array.dtype == object:
        flat_obj = np.ravel(array, order="F")
        codes = np.empty(flat_obj.shape, dtype=np.int32)
        for index, value in enumerate(flat_obj.tolist()):
            codes[index] = _NA if value is None else int(value)
        return codes, array.shape[0], array.shape[1]
    array = np.asarray(array, dtype=np.int32)
    flat = np.ravel(np.asfortranarray(array), order="F")
    return np.ascontiguousarray(flat), array.shape[0], array.shape[1]


def _r_script(kind, nrow, ncol, rows, cols, values, mode):
    fn = "rowTabulates" if kind == "row" else "colTabulates"
    if mode == "raw":
        reader = f'readBin(input, "raw", {nrow * ncol})'
    else:
        reader = f'readBin(input, "integer", {nrow * ncol})'
    material = f"matrix({reader}, nrow = {nrow}, ncol = {ncol})"
    if mode == "logical":
        material = f"{{v <- {material}; storage.mode(v) <- 'logical'; v}}"
    return textwrap.dedent(
        f"""
        library(matrixStats)
        options(warn = -1)
        input <- file("stdin", "rb")
        x <- {material}
        close(input)
        res <- {fn}(x, rows = {_r_index(rows)}, cols = {_r_index(cols)}, values = {_r_values(values)}, useNames = FALSE)
        cat(nrow(res), ncol(res), "\\n", sep = " ")
        if (length(res)) {{
          raw <- writeBin(as.integer(res), raw())
          cat(paste(sprintf("%02x", as.integer(raw)), collapse = ""), "\\n", sep = "")
        }}
        """
    )


def _r_index(index):
    if index is None:
        return "NULL"
    if isinstance(index, (bool, np.bool_)):
        return "TRUE" if index else "FALSE"
    if isinstance(index, (int, np.integer)) and not isinstance(index, bool):
        return "0L" if int(index) == 0 else f"{int(index)}L"
    if isinstance(index, (float, np.floating)):
        if math_isnan(index):
            return "NA_real_"
        return repr(float(index))
    if isinstance(index, (list, tuple)):
        values = list(index)
    else:
        array = np.asarray(index)
        if array.dtype == object:
            values = array.reshape(-1).tolist()
        elif array.dtype == np.bool_:
            flags = ", ".join("TRUE" if flag else "FALSE" for flag in array.reshape(-1).tolist())
            return f"c({flags})" if array.size else "logical(0)"
        elif np.issubdtype(array.dtype, np.floating):
            values = array.reshape(-1).tolist()
        else:
            values = [int(value) for value in array.reshape(-1).tolist()]
    if isinstance(index, (list, tuple)) or (
        isinstance(index, np.ndarray) and index.dtype == object
    ):
        if not values:
            return "integer(0)"
        if all(value is None or isinstance(value, (bool, np.bool_)) for value in values):
            parts = []
            for value in values:
                if value is None:
                    parts.append("NA")
                else:
                    parts.append("TRUE" if value else "FALSE")
            return f"c({', '.join(parts)})"
    parts = []
    for value in values:
        if value is None:
            parts.append("NA_integer_")
        elif isinstance(value, (bool, np.bool_)):
            parts.append("TRUE" if value else "FALSE")
        elif isinstance(value, (float, np.floating)) or (
            isinstance(value, float)
        ):
            if math_isnan(value):
                parts.append("NA_real_")
            else:
                parts.append(repr(float(value)))
        else:
            number = int(value)
            parts.append("NA_integer_" if number == int(_NA) else f"{number}L")
    if not parts:
        return "integer(0)"
    return f"c({', '.join(parts)})"


def _r_values(values):
    if values is None:
        return "NULL"
    if isinstance(values, (bytes, bytearray)):
        body = ", ".join(str(int(byte)) for byte in values)
        return f"as.raw(c({body}))"
    if isinstance(values, np.ndarray) and values.dtype == np.uint8:
        body = ", ".join(str(int(byte)) for byte in values.reshape(-1).tolist())
        return f"as.raw(c({body}))"
    if isinstance(values, (list, tuple)):
        items = list(values)
    else:
        array = np.asarray(values)
        items = array.reshape(-1).tolist()
    if len(items) == 0:
        return "integer(0)"
    parts = []
    for value in items:
        if value is None:
            parts.append("NA")
        elif isinstance(value, (bool, np.bool_)):
            parts.append("TRUE" if value else "FALSE")
        elif isinstance(value, str):
            parts.append('"' + value.replace('"', '\\"') + '"')
        elif isinstance(value, (float, np.floating)):
            number = float(value)
            if math_isnan(number):
                parts.append("NA_real_")
            elif math_isinf(number):
                parts.append("Inf" if number > 0 else "-Inf")
            else:
                parts.append(repr(number))
        else:
            number = int(value)
            parts.append("NA_integer_" if number == int(_NA) else f"{number}L")
    return f"c({', '.join(parts)})"


def math_isnan(value):
    try:
        return bool(np.isnan(value))
    except TypeError:
        return False


def math_isinf(value):
    try:
        return bool(np.isinf(value))
    except TypeError:
        return False
