"""Checks for rowCollapse and colCollapse against R's indexing."""

from __future__ import annotations

import subprocess
import textwrap

import numpy as np
import pytest

from matrixstats.rowcollapse import colCollapse, rowCollapse

_NA = np.int32(np.iinfo(np.int32).min)


def test_statement_example():
    x = np.arange(1, 13, dtype=np.int32).reshape((4, 3), order="F")
    rows = rowCollapse(x, [1, 2, 3])
    cols = colCollapse(x, [1, 2])
    assert rows.dtype == np.int32
    assert cols.dtype == np.int32
    assert rows.tolist() == [1, 6, 11, 4]
    assert cols.tolist() == [1, 6, 9]
    assert rowCollapse(x, 1).tolist() == [1, 2, 3, 4]
    assert colCollapse(x, [1, 3, 2]).tolist() == [1, 7, 10]


def test_dim_fills_a_vector_down_columns():
    flat = np.arange(1, 13)
    x = np.arange(1, 13, dtype=np.int32).reshape((4, 3), order="F")
    assert rowCollapse(flat, [1, 2, 3], dim=(4, 3)).tolist() == rowCollapse(x, [1, 2, 3]).tolist()
    assert colCollapse(flat, 2, dim=(4, 3)).tolist() == [2, 6, 10]
    wide = rowCollapse(x, 1, dim=(6, 2))
    assert wide.tolist() == [1, 2, 3, 4, 5, 6]


def test_index_edges_keep_r_recycling():
    x = np.arange(1, 13, dtype=np.int32).reshape((4, 3), order="F")
    with pytest.warns(RuntimeWarning, match="not a multiple"):
        assert rowCollapse(x, [1, 0, 2, 1]).tolist() == [1, 6, 3, 4]
    assert rowCollapse(x, [-1, -1, -1, -1]).tolist() == [5, 10, 7, 12]
    with pytest.warns(RuntimeWarning, match="not a multiple"):
        assert rowCollapse(x, [1.9, 2.1, 0.2, 3]).tolist() == [1, 6, 11, 4]
    assert rowCollapse(x, 4).tolist() == [_NA, _NA, _NA, _NA]
    assert rowCollapse(x, np.array([], dtype=np.int32)).tolist() == [_NA, _NA, _NA, _NA]
    assert rowCollapse(x, "a").tolist() == [_NA, _NA, _NA, _NA]
    assert rowCollapse(x, True).tolist() == [1, 6, 11, _NA]
    assert rowCollapse(x, False).size == 0
    assert rowCollapse(x, 0).size == 0
    with pytest.warns(RuntimeWarning, match="not a multiple"):
        assert colCollapse(x, [1, 0, 2]).tolist() == [1, 6, 9]
    assert colCollapse(x, -1).tolist() == [2, 7, 12]
    assert colCollapse(x, [4, 1, 2]).tolist() == [4, 5, 10]


def test_margin_subset_and_missing_values():
    x = np.arange(1, 13, dtype=np.int32).reshape((4, 3), order="F")
    assert rowCollapse(x, [1, 2, 3], rows=[2, 4]).tolist() == [6, 4]
    assert rowCollapse(x, [1, 2, 3], rows=[-2]).tolist() == [1, 11, 4]
    assert rowCollapse(x, [1, 2, 3], rows=[0, 2, 0, 4]).tolist() == [6, 4]
    assert rowCollapse(x, 1, rows=[True, False]).tolist() == [1, 3]
    na_rows = np.array([2, 2, _NA, 1], dtype=np.int32)
    assert rowCollapse(x, [1, 3, 2, 1], rows=na_rows).tolist() == [10, 10, int(_NA), 1]
    assert colCollapse(x, [1, 4, 2], cols=[3, 1, 3]).tolist() == [10, 1, 10]
    assert rowCollapse(np.arange(1, 13), [1, 2], dim=(4, 3), rows=[2, 4]).tolist() == [6, 8]

    dirty = np.array([[1.0, 5.0, 9.0], [np.nan, 6.0, 10.0], [3.0, 7.0, 11.0], [4.0, 8.0, 12.0]])
    got = rowCollapse(dirty, [1, 1, 2, 3])
    assert got[0] == 1.0
    assert np.isnan(got[1])
    assert got[2] == 7.0
    assert got[3] == 12.0
    assert np.isnan(rowCollapse(dirty, [1, np.nan, 2, 1])[1])


def test_empty_margins_and_logical_matrix():
    empty_cols = np.zeros((3, 0), dtype=np.int32)
    assert rowCollapse(empty_cols, 2).size == 0
    with pytest.raises(ValueError, match="only 0's may be mixed"):
        rowCollapse(empty_cols, [1, 2, 1])
    assert colCollapse(empty_cols, [1, 2, 3, 4, 5]).size == 0
    assert rowCollapse(np.zeros((0, 3), dtype=np.int32), np.array([], dtype=np.int32)).size == 0

    logical = np.array([[True, True], [False, False]])
    assert rowCollapse(logical, 1).tolist() == [True, False]
    assert colCollapse(logical, [2, 1]).tolist() == [False, True]


def test_errors():
    x = np.arange(1, 13, dtype=np.int32).reshape((4, 3), order="F")
    with pytest.warns(RuntimeWarning, match="length.out"):
        with pytest.raises(ValueError, match="argument of length 0"):
            rowCollapse(np.arange(12), 1)
    with pytest.raises(ValueError, match="do not match"):
        rowCollapse(np.arange(12), 1, dim=(3, 3))
    with pytest.raises(ValueError, match="negative values"):
        rowCollapse(np.arange(12), 1, dim=(4, -1))
    with pytest.raises(ValueError, match="invalid 'length.out'"):
        colCollapse(np.arange(12), 1, dim=(4, -1))
    with pytest.raises(ValueError, match="NA/NaN argument"):
        rowCollapse(np.arange(4), 1, dim=4)
    with pytest.raises(ValueError, match="subscript out of bounds"):
        rowCollapse(x, 1, rows=[5])
    with pytest.raises(ValueError, match="only 0's may be mixed"):
        rowCollapse(x, [-1, 1, 1, 1])
    with pytest.raises(ValueError, match="logical subscript too long"):
        rowCollapse(x, 1, rows=[True, False, True, False, True])
    with pytest.raises(ValueError, match="matrix or a vector"):
        rowCollapse(np.arange(24).reshape(2, 3, 4), 1)
    with pytest.raises(ValueError, match="not 'character'"):
        rowCollapse(np.array(["a", "b"]), 1)
    with pytest.raises(ValueError, match="missing value"):
        rowCollapse(x, 1, use_names=float("nan"))
    with pytest.raises(ValueError, match="length > 1"):
        rowCollapse(x, 1, use_names=[True, False])
    with pytest.raises(ValueError, match="length zero"):
        colCollapse(x, 1, use_names=None)
    assert np.array_equal(rowCollapse(x, 1, use_names=False), rowCollapse(x, 1))


def test_null_index_is_an_empty_vector():
    x = np.arange(1, 13, dtype=np.int32).reshape((4, 3), order="F")
    with pytest.warns(RuntimeWarning, match="NULL"):
        assert rowCollapse(x, None).size == 0
        assert rowCollapse(x, None).dtype == np.int32


def test_matches_r_including_the_timing_shape():
    script = textwrap.dedent(
        r"""
        library(matrixStats)
        report <- function(name, expr) {
          val <- tryCatch(suppressWarnings(expr), error = function(e) structure(conditionMessage(e), class = "err"))
          if (inherits(val, "err")) {
            cat("ERR\t", name, "\t", val, "\n", sep = "")
          } else {
            mode <- storage.mode(val)
            cat("OK\t", name, "\t", mode, "\t", length(val), "\n", sep = "")
            if (length(val)) {
              raw <- if (is.integer(val)) writeBin(val, raw()) else if (is.logical(val)) {
                codes <- ifelse(is.na(val), NA_integer_, as.integer(val))
                writeBin(codes, raw())
              } else writeBin(as.numeric(val), raw())
              cat(paste(sprintf("%02x", as.integer(raw)), collapse = ""), "\n", sep = "")
            } else {
              cat("\n")
            }
          }
          invisible(NULL)
        }
        x <- matrix(1:12, nrow = 4)
        report("row-1", rowCollapse(x, 1L))
        report("row-1:3", rowCollapse(x, 1:3))
        report("col-1", colCollapse(x, 1L))
        report("col-1:2", colCollapse(x, 1:2))
        report("col-1,3,2", colCollapse(x, c(1L, 3L, 2L)))
        report("row-rows", rowCollapse(x, 1:3, rows = c(2L, 4L)))
        report("row-rows-neg", rowCollapse(x, 1:3, rows = -2L))
        report("row-rows-zero", rowCollapse(x, 1:3, rows = c(0L, 2L, 0L, 4L)))
        report("row-rows-logical", rowCollapse(x, 1L, rows = c(TRUE, FALSE)))
        report("row-rows-na", rowCollapse(x, c(1L, 3L, 2L, 1L), rows = c(2L, 2L, NA_integer_, 1L)))
        report("col-cols", colCollapse(x, c(1L, 4L, 2L), cols = c(3L, 1L, 3L)))
        report("row-zero", rowCollapse(x, c(1, 0, 2, 1)))
        report("row-neg", rowCollapse(x, c(-1, -1, -1, -1)))
        report("row-frac", rowCollapse(x, c(1.9, 2.1, 0.2, 3)))
        report("row-oob", rowCollapse(x, 4))
        report("row-empty", rowCollapse(x, integer(0)))
        report("row-true", rowCollapse(x, TRUE))
        report("row-false", rowCollapse(x, FALSE))
        report("row-char", rowCollapse(x, "a"))
        report("row-null", rowCollapse(x, NULL))
        report("col-zero", colCollapse(x, c(1, 0, 2)))
        report("col-neg", colCollapse(x, -1))
        report("col-frac", colCollapse(x, c(1.2, 3.8, 0.4)))
        report("col-pick", colCollapse(x, c(4L, 1L, 2L)))
        report("dim-row", rowCollapse(1:12, 1:3, dim. = c(4L, 3L)))
        report("dim-col", colCollapse(1:12, 2L, dim. = c(4L, 3L)))
        report("dim-rows", rowCollapse(1:12, c(1L, 2L), dim. = c(4L, 3L), rows = c(2L, 4L)))
        report("dim-wide", rowCollapse(x, 1L, dim. = c(6L, 2L)))
        report("recycle-rows", rowCollapse(x, c(3L, 1L), rows = c(1L, 2L, 3L)))
        report("ncol0", rowCollapse(matrix(integer(0), nrow = 3, ncol = 0), 2L))
        report("ncol0-mix", rowCollapse(matrix(integer(0), nrow = 3, ncol = 0), c(1L, 2L, 1L)))
        report("col-0col", colCollapse(matrix(integer(0), nrow = 3, ncol = 0), 1:5))
        report("nrow0", rowCollapse(matrix(integer(0), nrow = 0, ncol = 3), integer(0)))
        xd <- matrix(as.numeric(1:12), nrow = 4)
        xd[2, 2] <- NA_real_
        report("double-cell", rowCollapse(xd, c(2, 2, 1, 3)))
        report("double-idx", rowCollapse(xd, c(1, NA_real_, 2, 3)))
        xl <- matrix(c(TRUE, FALSE, TRUE, FALSE), nrow = 2)
        report("logical", rowCollapse(xl, 1L))
        report("logical-col", colCollapse(xl, c(2L, 1L)))
        big <- matrix(as.numeric(seq_len(400 * 250)), nrow = 400, ncol = 250)
        report("big-row", rowCollapse(big, rep(seq_len(250), length.out = 400)))
        report("big-col", colCollapse(big, rep(seq_len(400), length.out = 250)))
        report("err-oob", rowCollapse(x, 1L, rows = 5L))
        report("err-mix", rowCollapse(x, c(-1, 1)))
        """
    )
    result = subprocess.run(
        ["Rscript", "-e", script],
        check=False,
        capture_output=True,
    )
    if result.returncode != 0:
        raise AssertionError(result.stderr.decode())
    got = _python_cases()
    lines = result.stdout.decode().splitlines()
    cursor = 0
    seen = set()
    while cursor < len(lines):
        parts = lines[cursor].split("\t")
        cursor += 1
        if parts[0] == "ERR":
            name = parts[1]
            seen.add(name)
            assert name not in got, name
            continue
        name, mode, length = parts[1], parts[2], int(parts[3])
        payload = lines[cursor]
        cursor += 1
        seen.add(name)
        reference = _decode(payload, mode, length)
        actual = got[name]
        _assert_close(name, actual, reference, mode)
    assert seen == set(got) | {"err-oob", "err-mix", "ncol0-mix"}


def _python_cases():
    x = np.arange(1, 13, dtype=np.int32).reshape((4, 3), order="F")
    flat = np.arange(1, 13)
    empty_cols = np.zeros((3, 0), dtype=np.int32)
    xd = np.arange(1, 13, dtype=np.float64).reshape((4, 3), order="F")
    xd[1, 1] = np.nan
    logical = np.array([[True, True], [False, False]])
    big = np.arange(1, 400 * 250 + 1, dtype=np.float64).reshape((400, 250), order="F")
    row_idxs = np.resize(np.arange(1, 251), 400)
    col_idxs = np.resize(np.arange(1, 401), 250)
    with warnings_quiet():
        return {
            "row-1": rowCollapse(x, 1),
            "row-1:3": rowCollapse(x, [1, 2, 3]),
            "col-1": colCollapse(x, 1),
            "col-1:2": colCollapse(x, [1, 2]),
            "col-1,3,2": colCollapse(x, [1, 3, 2]),
            "row-rows": rowCollapse(x, [1, 2, 3], rows=[2, 4]),
            "row-rows-neg": rowCollapse(x, [1, 2, 3], rows=-2),
            "row-rows-zero": rowCollapse(x, [1, 2, 3], rows=[0, 2, 0, 4]),
            "row-rows-logical": rowCollapse(x, 1, rows=[True, False]),
            "row-rows-na": rowCollapse(x, [1, 3, 2, 1], rows=np.array([2, 2, _NA, 1], dtype=np.int32)),
            "col-cols": colCollapse(x, [1, 4, 2], cols=[3, 1, 3]),
            "row-zero": rowCollapse(x, [1, 0, 2, 1]),
            "row-neg": rowCollapse(x, [-1, -1, -1, -1]),
            "row-frac": rowCollapse(x, [1.9, 2.1, 0.2, 3]),
            "row-oob": rowCollapse(x, 4),
            "row-empty": rowCollapse(x, np.array([], dtype=np.int32)),
            "row-true": rowCollapse(x, True),
            "row-false": rowCollapse(x, False),
            "row-char": rowCollapse(x, "a"),
            "row-null": rowCollapse(x, None),
            "col-zero": colCollapse(x, [1, 0, 2]),
            "col-neg": colCollapse(x, -1),
            "col-frac": colCollapse(x, [1.2, 3.8, 0.4]),
            "col-pick": colCollapse(x, [4, 1, 2]),
            "dim-row": rowCollapse(flat, [1, 2, 3], dim=(4, 3)),
            "dim-col": colCollapse(flat, 2, dim=(4, 3)),
            "dim-rows": rowCollapse(flat, [1, 2], dim=(4, 3), rows=[2, 4]),
            "dim-wide": rowCollapse(x, 1, dim=(6, 2)),
            "recycle-rows": rowCollapse(x, [3, 1], rows=[1, 2, 3]),
            "ncol0": rowCollapse(empty_cols, 2),
            "col-0col": colCollapse(empty_cols, [1, 2, 3, 4, 5]),
            "nrow0": rowCollapse(np.zeros((0, 3), dtype=np.int32), np.array([], dtype=np.int32)),
            "double-cell": rowCollapse(xd, [2, 2, 1, 3]),
            "double-idx": rowCollapse(xd, [1, np.nan, 2, 3]),
            "logical": rowCollapse(logical, 1),
            "logical-col": colCollapse(logical, [2, 1]),
            "big-row": rowCollapse(big, row_idxs),
            "big-col": colCollapse(big, col_idxs),
        }


class warnings_quiet:
    def __enter__(self):
        import warnings

        self._catch = warnings.catch_warnings()
        self._catch.__enter__()
        warnings.simplefilter("ignore", RuntimeWarning)
        return self

    def __exit__(self, *args):
        return self._catch.__exit__(*args)


def _decode(payload: str, mode: str, length: int) -> np.ndarray:
    if length == 0:
        if mode == "integer":
            return np.array([], dtype=np.int32)
        if mode == "logical":
            return np.array([], dtype=bool)
        return np.array([], dtype=np.float64)
    raw = bytes.fromhex(payload)
    if mode == "double":
        values = np.frombuffer(raw, dtype="<f8").copy()
    else:
        values = np.frombuffer(raw, dtype="<i4").copy()
    assert values.size == length
    if mode == "logical":
        out = np.empty(length, dtype=object)
        for i, value in enumerate(values.tolist()):
            if value == int(_NA):
                out[i] = None
            else:
                out[i] = bool(value)
        return out
    return values


def _assert_close(name: str, actual, reference, mode: str) -> None:
    if isinstance(actual, str):
        raise AssertionError(f"{name} was an error in Python and a value in R")
    actual = np.asarray(actual)
    if mode == "logical":
        assert actual.shape == reference.shape, name
        for got, want in zip(actual.tolist(), reference.tolist()):
            assert got is want or got == want, (name, got, want)
        return
    assert actual.shape == reference.shape, (name, actual.shape, reference.shape)
    if mode == "integer":
        assert actual.dtype == np.int32, (name, actual.dtype)
        assert np.array_equal(actual, reference), name
        return
    assert actual.dtype == np.float64, (name, actual.dtype)
    both_nan = np.isnan(actual) & np.isnan(reference)
    assert np.array_equal(np.isnan(actual), np.isnan(reference)), name
    if np.any(~both_nan):
        diff = np.abs(actual[~both_nan] - reference[~both_nan])
        assert np.all(diff <= 1e-8), (name, float(diff.max()))
