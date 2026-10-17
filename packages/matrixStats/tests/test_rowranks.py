"""Checks for rowRanks and colRanks, including ties and a comparison with R."""

from __future__ import annotations

import shutil
import subprocess
import textwrap

import numpy as np
import pytest

from matrixstats.rowranks import colRanks, rowRanks

TOL = 1e-8
NA_INTEGER = np.iinfo(np.int32).min
NA_REAL_BITS = np.uint64(0x7FF00000000007A2)


def test_ties_on_the_printed_matrix():
    printed = np.array([3, 1, 3, 2], dtype=np.int32).reshape((2, 2), order="F")
    assert rowRanks(printed, ties_method="max").tolist() == [[2, 2], [1, 2]]
    assert rowRanks(printed, ties_method="min").tolist() == [[1, 1], [1, 2]]
    assert rowRanks(printed, ties_method="first").tolist() == [[1, 2], [1, 2]]
    assert rowRanks(printed, ties_method="last").tolist() == [[2, 1], [1, 2]]
    assert rowRanks(printed, ties_method="dense").tolist() == [[1, 1], [1, 2]]
    average = rowRanks(printed, ties_method="average")
    assert average.dtype == np.float64
    assert average.tolist() == [[1.5, 1.5], [1.0, 2.0]]
    assert rowRanks(printed).dtype == np.int32
    assert rowRanks(printed).tolist() == rowRanks(printed, ties_method="ma").tolist()
    assert rowRanks(printed, ties_method="mi").tolist() == [[1, 1], [1, 2]]

    columns = colRanks(printed, ties_method="max")
    assert columns.shape == (2, 2)
    assert columns.tolist() == [[2, 1], [2, 1]]
    preserved = colRanks(printed, ties_method="max", preserve_shape=True)
    assert preserved.tolist() == [[2, 2], [1, 1]]
    assert colRanks(printed, ties_method="average").dtype == np.float64


def test_missing_values_and_signed_zero():
    na = np.array(np.uint64(NA_REAL_BITS).view(np.float64))
    row = np.array([[3.0, na, np.nan, 3.0, -0.0, 0.0]])
    first = rowRanks(row, ties_method="first")
    assert first.dtype == np.int32
    assert first.tolist() == [[3, NA_INTEGER, NA_INTEGER, 4, 1, 2]]
    assert rowRanks(row, ties_method="max").tolist() == [
        [4, NA_INTEGER, NA_INTEGER, 4, 2, 2]
    ]
    assert rowRanks(row, ties_method="dense").tolist() == [
        [2, NA_INTEGER, NA_INTEGER, 2, 1, 1]
    ]

    average = rowRanks(row, ties_method="average")
    assert average.dtype == np.float64
    assert average.reshape(-1).view(np.uint64)[1] == NA_REAL_BITS
    assert average.reshape(-1).view(np.uint64)[2] == NA_REAL_BITS
    assert average[0, 0] == 3.5
    assert average[0, 4] == 1.5

    ints = np.array([[2, NA_INTEGER, 2, 1]], dtype=np.int32)
    assert rowRanks(ints, ties_method="max").tolist() == [[3, NA_INTEGER, 3, 1]]
    assert rowRanks(ints, ties_method="last").tolist() == [[3, NA_INTEGER, 2, 1]]
    assert colRanks(ints, ties_method="min", preserve_shape=True).tolist() == [
        [1, NA_INTEGER, 1, 1]
    ]


def test_random_is_a_permutation_of_the_tie():
    row = np.array([[1, 5, 1, 1]], dtype=np.int32)
    ranks = rowRanks(row, ties_method="random")
    assert ranks[0, 1] == 4
    assert sorted(int(v) for v in ranks[0, [0, 2, 3]]) == [1, 2, 3]
    again = rowRanks(row, ties_method="random")
    assert sorted(again.reshape(-1).tolist()) == [1, 2, 3, 4]


def test_subsets_dim_and_empty_margins():
    printed = np.array([3, 1, 3, 2, 5, 4], dtype=np.int32).reshape((2, 3), order="F")
    assert rowRanks(printed, rows=[2, 1], ties_method="max").tolist() == [
        [1, 2, 3],
        [2, 2, 3],
    ]
    assert rowRanks(printed, cols=[3, 1], ties_method="max").tolist() == [[2, 1], [2, 1]]
    assert rowRanks(printed, cols=[1, None], ties_method="max").tolist() == [
        [1, NA_INTEGER],
        [1, NA_INTEGER],
    ]
    assert rowRanks(printed, rows=[-1], ties_method="first").tolist() == [[1, 2, 3]]
    assert rowRanks(printed, cols=[0, 2, 0], ties_method="min").tolist() == [[1], [1]]
    assert rowRanks(printed, rows=[]).shape == (0, 3)
    assert rowRanks(printed, rows=[]).dtype == np.int32
    assert colRanks(np.zeros((2, 0), dtype=np.int32), ties_method="average").shape == (0, 2)
    assert colRanks(np.zeros((2, 0), dtype=np.int32), ties_method="average").dtype == np.float64
    flat = np.array([3, 1, 3, 2], dtype=np.int32)
    assert rowRanks(flat, dim=(2, 2), ties_method="dense").tolist() == [[1, 1], [1, 2]]
    assert rowRanks(printed, rows=1).tolist() == [[2, 2, 3]]


def test_infinities_and_rejections():
    row = np.array([[np.inf, -np.inf, 1.0, 1.0, 0.0, -0.0]])
    assert rowRanks(row, ties_method="max").tolist() == [[6, 1, 5, 5, 3, 3]]
    assert rowRanks(row, ties_method="dense").tolist() == [[4, 1, 3, 3, 2, 2]]
    with pytest.raises(ValueError, match="Unknown value of argument 'ties.method': m"):
        rowRanks(np.array([[1.0, 2.0]]), ties_method="m")
    with pytest.raises(ValueError, match="cannot be logical"):
        colRanks(np.array([[True, False]]))
    with pytest.raises(ValueError, match="subscript out of bounds"):
        rowRanks(np.array([[1, 2], [3, 4]]), rows=[5])
    with pytest.raises(ValueError, match="TRUE or FALSE"):
        colRanks(np.array([[1, 2], [3, 4]]), preserve_shape=2)


def test_matches_r_on_ties_missing_values_and_subsets():
    if shutil.which("Rscript") is None:
        pytest.skip("Rscript is unavailable")
    reference = _r_suite()
    if reference is None:
        pytest.skip("matrixStats is unavailable")

    printed = np.array([3, 1, 3, 2, 5, 4], dtype=np.int32).reshape((2, 3), order="F")
    for method in ("max", "min", "average", "first", "last", "dense", "ma", "av"):
        _assert_match(rowRanks(printed, ties_method=method), reference[f"row-{method}"])
        _assert_match(colRanks(printed, ties_method=method), reference[f"col-{method}"])
        _assert_match(
            colRanks(printed, ties_method=method, preserve_shape=True),
            reference[f"keep-{method}"],
        )

    _assert_match(rowRanks(printed), reference["row-default"])
    _assert_match(colRanks(printed), reference["col-default"])
    _assert_match(rowRanks(printed, rows=[2, 1], ties_method="max"), reference["rows"])
    _assert_match(rowRanks(printed, cols=[3, 1], ties_method="first"), reference["cols"])
    _assert_match(rowRanks(printed, cols=[1, None], ties_method="min"), reference["na-col"])
    _assert_match(
        colRanks(printed, rows=[None, 1], ties_method="average", preserve_shape=True),
        reference["na-row"],
    )
    _assert_match(rowRanks(np.array([3, 1, 3, 2]), dim=(2, 2), ties_method="dense"), reference["dim"])

    na = np.array(np.uint64(NA_REAL_BITS).view(np.float64))
    mixed = np.array([[3.0, na, np.nan, 3.0, -0.0, 0.0]])
    _assert_match(rowRanks(mixed, ties_method="first"), reference["nan-first"])
    _assert_match(rowRanks(mixed, ties_method="max"), reference["nan-max"])
    _assert_match(rowRanks(mixed, ties_method="average"), reference["nan-average"])
    _assert_match(rowRanks(mixed, ties_method="dense"), reference["nan-dense"])
    ints = np.array([[2, NA_INTEGER, 2, 1]], dtype=np.int32)
    _assert_match(rowRanks(ints, ties_method="last"), reference["int-last"])
    _assert_match(colRanks(ints, ties_method="average"), reference["int-col-average"])


def _assert_match(actual, expected):
    actual = np.asarray(actual)
    kind, values = expected
    assert actual.shape == values.shape
    if kind == "integer":
        assert actual.dtype == np.int32
        assert np.array_equal(actual, values.astype(np.int32))
        return
    assert actual.dtype == np.float64
    actual_f = actual.reshape(-1)
    expected_f = values.reshape(-1)
    actual_b = actual.reshape(-1).view(np.uint64)
    expected_b = values.reshape(-1).view(np.uint64)
    for got, want, got_bits, want_bits in zip(actual_f, expected_f, actual_b, expected_b):
        if not np.isfinite(want) or not np.isfinite(got):
            assert got_bits == want_bits
        else:
            assert abs(float(got) - float(want)) <= TOL


def _r_suite():
    script = textwrap.dedent(
        r"""
        options(matrixStats.ties.method.missing = "ignore")
        if (!requireNamespace("matrixStats", quietly=TRUE)) quit(status=2)
        emit <- function(name, values) {
          mode <- storage.mode(values)
          mat <- as.matrix(values)
          cat(name, "\n", mode, "\n", nrow(mat), " ", ncol(mat), "\n", sep="")
          flat <- as.vector(mat)
          if (mode == "integer") {
            encoded <- ifelse(is.na(flat), "NA", as.character(flat))
          } else {
            raw <- writeBin(as.double(flat), raw())
            encoded <- sprintf("%02x", as.integer(raw))
          }
          if (length(encoded)) cat(encoded, sep="\n")
          cat("---\n")
        }
        x <- matrix(c(3L, 1L, 3L, 2L, 5L, 4L), nrow=2)
        for (method in c("max", "min", "average", "first", "last", "dense", "ma", "av")) {
          emit(paste0("row-", method), matrixStats::rowRanks(x, ties.method=method))
          emit(paste0("col-", method), matrixStats::colRanks(x, ties.method=method))
          emit(paste0("keep-", method), matrixStats::colRanks(x, ties.method=method, preserveShape=TRUE))
        }
        emit("row-default", matrixStats::rowRanks(x))
        emit("col-default", matrixStats::colRanks(x))
        emit("rows", matrixStats::rowRanks(x, rows=c(2, 1), ties.method="max"))
        emit("cols", matrixStats::rowRanks(x, cols=c(3, 1), ties.method="first"))
        emit("na-col", matrixStats::rowRanks(x, cols=c(1, NA), ties.method="min"))
        emit("na-row", matrixStats::colRanks(x, rows=c(NA, 1), ties.method="average", preserveShape=TRUE))
        emit("dim", matrixStats::rowRanks(c(3L, 1L, 3L, 2L), dim.=c(2L, 2L), ties.method="dense"))
        na_bits <- writeBin(as.double(NA_real_), raw())
        nan <- readBin(as.raw(c(0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xf8, 0x7f)), "double")
        na <- NA_real_
        mixed <- matrix(c(3, na, nan, 3, -0, 0), nrow=1)
        emit("nan-first", matrixStats::rowRanks(mixed, ties.method="first"))
        emit("nan-max", matrixStats::rowRanks(mixed, ties.method="max"))
        emit("nan-average", matrixStats::rowRanks(mixed, ties.method="average"))
        emit("nan-dense", matrixStats::rowRanks(mixed, ties.method="dense"))
        ints <- matrix(c(2L, NA_integer_, 2L, 1L), nrow=1)
        emit("int-last", matrixStats::rowRanks(ints, ties.method="last"))
        emit("int-col-average", matrixStats::colRanks(ints, ties.method="average"))
        """
    )
    result = subprocess.run(
        ["Rscript", "-e", script],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode == 2:
        return None
    if result.returncode != 0:
        raise RuntimeError(result.stderr)
    return _parse_blocks(result.stdout)


def _parse_blocks(text: str):
    parsed = {}
    chunks = text.split("---\n")
    for chunk in chunks:
        lines = [line for line in chunk.splitlines() if line != ""]
        if not lines:
            continue
        name = lines[0]
        kind = lines[1]
        nrow, ncol = (int(part) for part in lines[2].split())
        body = lines[3:]
        if kind == "integer":
            values = np.empty(nrow * ncol, dtype=np.int32)
            for i, line in enumerate(body):
                values[i] = NA_INTEGER if line == "NA" else int(line)
            parsed[name] = (kind, values.reshape((nrow, ncol), order="F"))
        else:
            raw = bytes(int(line, 16) for line in body)
            values = np.frombuffer(raw, dtype="<f8").reshape((nrow, ncol), order="F")
            parsed[name] = (kind, np.array(values, copy=True))
    return parsed
