"""Checks for rowWeightedMeans and colWeightedMeans against installed matrixStats."""

from __future__ import annotations

import subprocess
import textwrap
import warnings

import numpy as np
import pytest

from matrixstats.rowweightedmeans import colWeightedMeans, rowWeightedMeans

_NA = np.iinfo(np.int32).min


def _matrix_1_to_12():
    return np.arange(1, 13, dtype=float).reshape((3, 4), order="F")


def test_zero_weight_drops_a_column_and_matches_the_kept_mean():
    x = _matrix_1_to_12()
    got = rowWeightedMeans(x, w=np.array([1.0, 1.0, 0.0, 1.0]))
    assert got.tolist() == [5.0, 6.0, 7.0]
    cols = colWeightedMeans(x, w=np.array([1.0, 0.0, 1.0]))
    assert cols.tolist() == [2.0, 5.0, 8.0, 11.0]
    assert rowWeightedMeans(x, w=np.zeros(4)).shape == (3,)
    assert np.isnan(rowWeightedMeans(x, w=np.zeros(4))).all()
    assert np.array_equal(
        rowWeightedMeans(x, w=[1, 1, 0, 1], use_names=False),
        rowWeightedMeans(x, w=[1, 1, 0, 1], use_names=True),
    )
    assert rowWeightedMeans(x, w=[1, 1, 0, 1], ignored=True).tolist() == [5.0, 6.0, 7.0]


def test_missing_weights_follow_the_r_file():
    complete = np.arange(1, 7, dtype=float).reshape((2, 3), order="F")
    poisoned = rowWeightedMeans(complete, w=np.array([1.0, np.nan, 2.0]), na_rm=True)
    assert np.isnan(poisoned).all()
    partial = np.array([[1.0, np.nan, 3.0], [10.0, 20.0, 30.0]])
    mixed = rowWeightedMeans(partial, w=np.array([1.0, np.nan, 4.0]), na_rm=True)
    assert mixed[0] == pytest.approx(2.6)
    assert np.isnan(mixed[1])
    columns = np.arange(1, 13, dtype=float).reshape((3, 4), order="F")
    columns[1, 0] = np.nan
    got = colWeightedMeans(columns, w=np.array([1.0, np.nan, 2.0]), na_rm=True)
    assert got[0] == pytest.approx(2.3333333333333335)
    assert np.isnan(got[1:]).all()


def test_repeated_columns_keep_a_zero_weight_and_its_missing_value():
    x = np.array([[1.0, np.nan, 5.0], [2.0, 4.0, 6.0]])
    dropped = rowWeightedMeans(x, w=[1.0, 0.0, 1.0], na_rm=False)
    assert dropped[0] == pytest.approx(3.0)
    assert dropped[1] == pytest.approx(4.0)
    kept = rowWeightedMeans(x, w=[1.0, 0.0, 1.0], cols=[1, 2, 3, 1, 2, 3], na_rm=False)
    assert np.isnan(kept[0])
    assert kept[1] == pytest.approx(4.0)


def test_subscripts_follow_base_extraction():
    x = _matrix_1_to_12()
    assert rowWeightedMeans(x, rows=True).tolist() == rowWeightedMeans(x).tolist()
    assert rowWeightedMeans(x, rows=1).shape == (1,)
    assert rowWeightedMeans(x, rows=False).size == 0
    assert rowWeightedMeans(x, rows=[]).size == 0
    assert rowWeightedMeans(x, rows=[-5]).tolist() == rowWeightedMeans(x).tolist()
    assert rowWeightedMeans(x, rows=[-1, -1, 0]).tolist() == pytest.approx([6.5, 7.5])
    assert rowWeightedMeans(x, w=[1, 2, 3, 4], rows=[1.9, 2.1]).tolist() == pytest.approx([7, 8])
    assert rowWeightedMeans(x, rows=[1.9, 0.2, -0.4]).tolist() == pytest.approx([5.5])
    assert rowWeightedMeans(x, rows=[True, False]).tolist() == pytest.approx([5.5, 7.5])
    logical_na = rowWeightedMeans(x, rows=[True, None])
    assert logical_na.tolist()[:1] == pytest.approx([5.5])
    assert np.isnan(logical_na[1])
    assert logical_na[2] == pytest.approx(7.5)
    numeric_na = rowWeightedMeans(x, w=[1, 2, 3, 4], rows=np.array([1.0, np.nan]))
    assert numeric_na[0] == pytest.approx(7.0)
    assert np.isnan(numeric_na[1])
    assert numeric_na.shape == (2,)
    with pytest.raises(ValueError, match="subscript out of bounds"):
        rowWeightedMeans(x, rows=[5])
    with pytest.raises(ValueError, match="only 0's may be mixed with negative subscripts"):
        rowWeightedMeans(x, rows=[-1, 2])
    with pytest.raises(ValueError, match="only 0's may be mixed with negative subscripts"):
        rowWeightedMeans(x, rows=np.array([np.nan, -1.0]))
    with pytest.raises(ValueError, match="logical subscript too long"):
        rowWeightedMeans(x, rows=[True, False, True, True])
    with pytest.raises(ValueError, match="dimnames"):
        rowWeightedMeans(x, rows=["b"])
    with pytest.warns(RuntimeWarning, match="integer range"):
        inserted = rowWeightedMeans(x, rows=[np.inf])
    assert inserted.shape == (1,) and np.isnan(inserted[0])
    with warnings.catch_warnings():
        warnings.simplefilter("error", RuntimeWarning)
        quiet = rowWeightedMeans(x, rows=np.array([1.0, np.nan]))
    assert quiet.shape == (2,)
    with pytest.raises(ValueError, match="subscript out of bounds"):
        rowWeightedMeans(x, rows=[2147483647.9])
    empty = np.zeros((0, 3))
    with pytest.raises(ValueError, match="logical subscript too long"):
        rowWeightedMeans(empty, rows=True)
    assert rowWeightedMeans(empty, rows=[-1]).size == 0
    inserted_empty = rowWeightedMeans(empty, rows=np.array([np.nan]))
    assert inserted_empty.shape == (1,) and np.isnan(inserted_empty[0])


def test_argument_errors_and_storage():
    x = _matrix_1_to_12()
    with pytest.raises(ValueError, match="negative values"):
        rowWeightedMeans(x, w=[1, -1, 1, 1])
    with pytest.raises(ValueError, match="negative values"):
        colWeightedMeans(x, w=[1.0, np.nan, -0.2])
    with pytest.raises(ValueError, match="columns"):
        rowWeightedMeans(x, w=[1, 1], cols=[1, 2])
    with pytest.raises(ValueError, match="rows"):
        colWeightedMeans(x, w=[1, 2, 3, 4])
    with pytest.raises(ValueError, match="not numeric: logical"):
        rowWeightedMeans(x, w=[True, False, True, True])
    with pytest.raises(ValueError, match="not numeric: character"):
        rowWeightedMeans(x, w=["a", "b", "c", "d"])
    with pytest.raises(ValueError, match="should be a matrix"):
        rowWeightedMeans(np.arange(4))
    with pytest.raises(ValueError, match="should be a matrix"):
        rowWeightedMeans(np.zeros((2, 2, 2)))
    with pytest.raises(ValueError, match="must be numeric"):
        rowWeightedMeans(np.array([["a", "b"], ["c", "d"]]))
    with pytest.raises(ValueError, match="na.rm"):
        rowWeightedMeans(x, na_rm=1)
    with pytest.raises(ValueError, match="useNames"):
        rowWeightedMeans(x, use_names="yes")
    logical = np.array([[True, True], [False, True]])
    assert rowWeightedMeans(logical, w=[1, 3]).tolist() == pytest.approx([1.0, 0.75])
    integer = np.array([[1, _NA, 5], [2, 4, 6]], dtype=np.int32)
    assert rowWeightedMeans(integer, w=[1, 1, 1], na_rm=True).tolist() == [3.0, 4.0]
    assert np.isnan(rowWeightedMeans(integer, w=[1, 1, 1], na_rm=False)[0])
    column = np.array([[1.0], [1.0], [0.0], [1.0]])
    assert rowWeightedMeans(x, w=column).tolist() == [5.0, 6.0, 7.0]


def test_matches_installed_r():
    reference = _r_oracle()
    x = _matrix_1_to_12()
    dirty = np.array([[1.0, 3.0, 5.0], [np.nan, 4.0, np.nan]])
    partial = np.array([[1.0, np.nan, 3.0], [10.0, 20.0, 30.0]])
    repeated = np.array([[1.0, np.nan, 5.0], [2.0, 4.0, 6.0]])
    checks = {
        "row_w": rowWeightedMeans(x, w=[1, 1, 0, 1]),
        "col_w": colWeightedMeans(x, w=[1, 0, 1]),
        "row_plain": rowWeightedMeans(x),
        "col_plain": colWeightedMeans(x),
        "row_na_t": rowWeightedMeans(dirty, w=[1, 1, 1], na_rm=True),
        "row_na_f": rowWeightedMeans(dirty, w=[1, 1, 1], na_rm=False),
        "row_drop": rowWeightedMeans(dirty, w=[1, 0, 2], na_rm=False),
        "row_drop_t": rowWeightedMeans(dirty, w=[1, 0, 2], na_rm=True),
        "na_w": rowWeightedMeans(
            np.arange(1, 7, dtype=float).reshape((2, 3), order="F"),
            w=np.array([1.0, np.nan, 2.0]),
            na_rm=True,
        ),
        "partial": rowWeightedMeans(partial, w=np.array([1.0, np.nan, 4.0]), na_rm=True),
        "keep0": rowWeightedMeans(
            repeated, w=[1, 0, 1], cols=[1, 2, 3, 1, 2, 3], na_rm=False
        ),
        "both": rowWeightedMeans(x, w=[1, 2, 3, 4], rows=[3, 1], cols=[2, 4]),
        "col_both": colWeightedMeans(x, w=[1, 2, 3], rows=[3, 1], cols=[4, 2, 2]),
        "neg_idx": rowWeightedMeans(x, rows=[-5]),
        "logic": rowWeightedMeans(x, rows=[True, False]),
        "logic_na": rowWeightedMeans(x, rows=[True, None]),
        "num_na": rowWeightedMeans(x, w=[1, 2, 3, 4], rows=np.array([1.0, np.nan])),
        "col_na": rowWeightedMeans(x, w=[1, 2, 3, 4], cols=np.array([1.0, np.nan]), na_rm=True),
        "col_na_f": rowWeightedMeans(x, w=[1, 2, 3, 4], cols=np.array([1.0, np.nan]), na_rm=False),
        "zeros": rowWeightedMeans(x, cols=[0, 2, 0, 4], w=[1, 2, 3, 4]),
        "empty_rows": rowWeightedMeans(x, rows=[]),
        "empty_w": rowWeightedMeans(np.zeros((0, 3)), w=[1, 1, 1]),
        "empty_c": rowWeightedMeans(np.zeros((3, 0)), w=np.zeros(0)),
        "col_empty": colWeightedMeans(np.zeros((0, 3)), w=np.zeros(0)),
        "infw": rowWeightedMeans(
            np.arange(1, 7, dtype=float).reshape((2, 3), order="F"), w=[1, np.inf, 1]
        ),
        "neg0": rowWeightedMeans(
            np.arange(1, 7, dtype=float).reshape((2, 3), order="F"),
            w=np.array([1.0, -0.0, 2.0]),
        ),
        "logx": rowWeightedMeans(np.array([[True, True], [False, True]]), w=[1, 3]),
        "intna": rowWeightedMeans(
            np.array([[1, _NA, 5], [2, 4, 6]], dtype=np.int32), w=[1, 1, 1], na_rm=True
        ),
        "i32idx": rowWeightedMeans(x, w=[1, 2, 3, 4], rows=np.array([1, _NA], dtype=np.int32)),
        "frac": rowWeightedMeans(x, w=[1, 2, 3, 4], rows=[1.9, 2.1]),
        "subset_w": rowWeightedMeans(x, w=[1, 2, 3, 4], cols=[-1, -3]),
    }
    for name, got in checks.items():
        _assert_close(got, reference[name], name)
    assert reference["neg"].startswith("ERR ")
    assert "negative" in reference["neg"]
    assert reference["negcol"].startswith("ERR ")
    assert "negative" in reference["negcol"]
    with pytest.raises(ValueError, match="negative values"):
        rowWeightedMeans(x, w=[1, -1, 1, 1])
    with pytest.raises(ValueError, match="negative values"):
        colWeightedMeans(x, w=[-1, 1, 1])


def _assert_close(got, reference: np.ndarray, name: str):
    got = np.asarray(got, dtype=np.float64)
    assert got.shape == reference.shape, name
    assert np.array_equal(np.isnan(got), np.isnan(reference)), name
    finite = ~np.isnan(reference)
    if np.any(finite):
        diff = np.max(np.abs(got[finite] - reference[finite]))
        assert diff <= 1e-8, name


def _r_oracle() -> dict:
    script = textwrap.dedent(
        r"""
        library(matrixStats)
        emit <- function(name, value) {
          cat(name, "\n", sep="")
          if (inherits(value, "error")) {
            cat("ERR ", conditionMessage(value), "\n", sep="")
          } else if (length(value) == 0) {
            cat("EMPTY\n")
          } else {
            cat(sprintf("%.17g\n", value), sep="")
          }
          cat("---\n")
        }
        x <- matrix(1:12, nrow=3)
        emit("row_w", rowWeightedMeans(x, w=c(1, 1, 0, 1)))
        emit("col_w", colWeightedMeans(x, w=c(1, 0, 1)))
        emit("row_plain", rowWeightedMeans(x))
        emit("col_plain", colWeightedMeans(x))
        dirty <- matrix(c(1, NA, 3, 4, 5, NA), nrow=2)
        emit("row_na_t", rowWeightedMeans(dirty, w=c(1, 1, 1), na.rm=TRUE))
        emit("row_na_f", rowWeightedMeans(dirty, w=c(1, 1, 1), na.rm=FALSE))
        emit("row_drop", rowWeightedMeans(dirty, w=c(1, 0, 2), na.rm=FALSE))
        emit("row_drop_t", rowWeightedMeans(dirty, w=c(1, 0, 2), na.rm=TRUE))
        complete <- matrix(1:6, nrow=2)
        emit("na_w", rowWeightedMeans(complete, w=c(1, NA, 2), na.rm=TRUE))
        partial <- matrix(c(1, 10, NA, 20, 3, 30), nrow=2)
        emit("partial", rowWeightedMeans(partial, w=c(1, NA, 4), na.rm=TRUE))
        repeated <- matrix(c(1, 2, NA, 4, 5, 6), nrow=2)
        emit("keep0", rowWeightedMeans(repeated, w=c(1, 0, 1), cols=c(1, 2, 3, 1, 2, 3), na.rm=FALSE))
        emit("both", rowWeightedMeans(x, w=1:4, rows=c(3, 1), cols=c(2, 4)))
        emit("col_both", colWeightedMeans(x, w=1:3, rows=c(3, 1), cols=c(4, 2, 2)))
        emit("neg_idx", rowWeightedMeans(x, rows=-5))
        emit("logic", rowWeightedMeans(x, rows=c(TRUE, FALSE)))
        emit("logic_na", rowWeightedMeans(x, rows=c(TRUE, NA)))
        emit("num_na", rowWeightedMeans(x, w=1:4, rows=c(1, NA_real_)))
        emit("col_na", rowWeightedMeans(x, w=1:4, cols=c(1, NA_real_), na.rm=TRUE))
        emit("col_na_f", rowWeightedMeans(x, w=1:4, cols=c(1, NA_real_), na.rm=FALSE))
        emit("zeros", rowWeightedMeans(x, cols=c(0, 2, 0, 4), w=1:4))
        emit("empty_rows", rowWeightedMeans(x, rows=integer(0)))
        emit("empty_w", rowWeightedMeans(matrix(numeric(0), nrow=0, ncol=3), w=c(1, 1, 1)))
        emit("empty_c", rowWeightedMeans(matrix(numeric(0), nrow=3, ncol=0), w=numeric(0)))
        emit("col_empty", colWeightedMeans(matrix(numeric(0), nrow=0, ncol=3), w=numeric(0)))
        emit("infw", rowWeightedMeans(matrix(1:6, nrow=2), w=c(1, Inf, 1)))
        emit("neg0", rowWeightedMeans(matrix(1:6, nrow=2), w=c(1, -0, 2)))
        emit("logx", rowWeightedMeans(matrix(c(TRUE, FALSE, TRUE, TRUE), nrow=2), w=c(1, 3)))
        xi <- matrix(as.integer(1:6), nrow=2)
        xi[1, 2] <- NA
        emit("intna", rowWeightedMeans(xi, w=c(1, 1, 1), na.rm=TRUE))
        emit("i32idx", rowWeightedMeans(x, w=1:4, rows=c(1L, NA_integer_)))
        emit("frac", rowWeightedMeans(x, w=1:4, rows=c(1.9, 2.1)))
        emit("subset_w", rowWeightedMeans(x, w=1:4, cols=c(-1, -3)))
        emit("neg", tryCatch(rowWeightedMeans(x, w=c(1, -1, 1, 1)), error=function(e) e))
        emit("negcol", tryCatch(colWeightedMeans(x, w=c(-1, 1, 1)), error=function(e) e))
        """
    )
    result = subprocess.run(
        ["Rscript", "-e", script],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr)
    return _parse_blocks(result.stdout)


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


def _numbers(lines: list[str]) -> np.ndarray | str:
    if len(lines) == 1 and lines[0] == "EMPTY":
        return np.zeros(0, dtype=np.float64)
    if len(lines) == 1 and lines[0].startswith("ERR "):
        return lines[0]
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

