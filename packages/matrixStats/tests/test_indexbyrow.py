"""Checks for indexByRow against the installed matrixStats 1.5.0."""

from __future__ import annotations

import shutil
import subprocess

import numpy as np
import pytest

from matrixstats.indexbyrow import indexByRow

NA_INTEGER = -2147483648


def test_null_returns_column_major_indexes_in_row_major_order():
    got = indexByRow((5, 4))
    assert got.dtype == np.int32
    assert got.ndim == 1
    assert got.tolist() == [
        1, 6, 11, 16, 2, 7, 12, 17, 3, 8, 13, 18, 4, 9, 14, 19, 5, 10, 15, 20
    ]
    assert indexByRow(np.array([2, 3])).tolist() == [1, 3, 5, 2, 4, 6]
    assert indexByRow((1, 1)).tolist() == [1]
    assert indexByRow((4, 1)).tolist() == [1, 2, 3, 4]
    assert indexByRow((1, 4)).tolist() == [1, 2, 3, 4]


def test_short_idxs_keep_order_and_duplicates():
    assert indexByRow((5, 4), idxs=[1, 3, 7]).tolist() == [1, 11, 12]
    assert indexByRow((2, 3), idxs=np.array([2, 2, 1], dtype=np.int32)).tolist() == [3, 3, 1]
    assert indexByRow((2, 3), idxs=[6, 1, 4]).tolist() == [6, 1, 2]
    assert indexByRow((2, 3), idxs=np.array([], dtype=np.int32)).size == 0
    assert indexByRow((2.9, 3.2), idxs=[1.2, 5.9, 6.1]).tolist() == [1, 4, 6]


def test_negative_zero_and_out_of_range_idxs_error():
    with pytest.raises(ValueError, match="may only contain positive indices: -1"):
        indexByRow((5, 4), idxs=[-1, -2])
    with pytest.raises(ValueError, match="may only contain positive indices: 0"):
        indexByRow((1, 1), idxs=[0])
    with pytest.raises(ValueError, match="may only contain positive indices: -3"):
        indexByRow((2, 2), idxs=[1, -3, 2])
    with pytest.raises(ValueError, match="larger than 6: 7"):
        indexByRow((2, 3), idxs=[7])
    with pytest.raises(ValueError, match="larger than 6: -2147483648"):
        indexByRow((2, 3), idxs=[NA_INTEGER])
    with pytest.raises(ValueError, match="larger than 6: 2147483647"):
        indexByRow((2, 3), idxs=[2147483647])


def test_empty_dimensions_defunct_matrix_and_bad_dim():
    assert indexByRow((0, 4)).size == 0
    assert indexByRow((3, 0)).size == 0
    assert indexByRow((-0.2, 3)).size == 0
    with pytest.raises(ValueError, match="larger than 0: 1"):
        indexByRow((0, 4), idxs=[1])
    with pytest.raises(ValueError, match="negative value: -1"):
        indexByRow((-1, 2))
    with pytest.raises(ValueError, match="negative value: -2147483648"):
        indexByRow((np.nan, 2))
    with pytest.raises(ValueError, match="length two"):
        indexByRow((2,))
    with pytest.raises(ValueError, match="length two"):
        indexByRow((2, 3, 1))
    with pytest.raises(ValueError, match="more than 2\\^31-1 elements: 4294967294"):
        indexByRow((2147483647, 2), idxs=[1])
    with pytest.raises(ValueError, match="defunct"):
        indexByRow(np.array([[5, 4]]))
    assert indexByRow((2147483647, 1), idxs=[1]).tolist() == [1]


def test_logical_idxs_are_coerced_like_as_integer():
    assert indexByRow((2, 3), idxs=True).tolist() == [1]
    with pytest.raises(ValueError, match="may only contain positive indices: 0"):
        indexByRow((2, 3), idxs=False)
    with pytest.raises(ValueError, match="may only contain positive indices: 0"):
        indexByRow((2, 3), idxs=[True, False, True])


def test_matches_installed_r_including_the_timing_shape():
    if shutil.which("Rscript") is None:
        pytest.skip("Rscript is unavailable")
    script = r"""
    library(matrixStats)
    emit <- function(name, expr) {
      val <- tryCatch(expr, error = function(e) paste0("ERR ", conditionMessage(e)))
      if (is.integer(val)) val <- paste(sprintf("%d", val), collapse = " ")
      cat(name, "\t", val, "\n", sep = "")
    }
    emit("null54", indexByRow(c(5, 4)))
    emit("null23", indexByRow(c(2L, 3L)))
    emit("short", indexByRow(c(5, 4), idxs = c(1, 3, 7)))
    emit("dup", indexByRow(c(2, 3), idxs = c(2, 2, 1)))
    emit("order", indexByRow(c(2, 3), idxs = c(6, 1, 4)))
    emit("frac", indexByRow(c(2.9, 3.2), idxs = c(1.2, 5.9, 6.1)))
    emit("empty", indexByRow(c(2, 3), idxs = integer(0)))
    emit("dim0", indexByRow(c(0, 4)))
    emit("onecol", indexByRow(c(4, 1)))
    emit("neg", indexByRow(c(5, 4), idxs = c(-1, -2)))
    emit("zero", indexByRow(c(1, 1), idxs = 0L))
    emit("oob", indexByRow(c(2, 3), idxs = 7L))
    emit("na", indexByRow(c(2, 3), idxs = NA_integer_))
    emit("big", indexByRow(c(.Machine$integer.max, 2L), idxs = 1L))
    emit("huge", indexByRow(c(100000001, 100000001), idxs = 1L))
    emit("negdim", indexByRow(c(-1, 2)))
    emit("mat", indexByRow(matrix(c(2, 3), nrow = 1)))
    emit("lgl", indexByRow(c(2, 3), idxs = TRUE))
    emit("posneg", indexByRow(c(2, 2), idxs = c(1L, -3L, 2L)))
    y <- indexByRow(c(500L, 400L))
    writeBin(y, "/tmp/indexByRow-r-full.bin")
    emit("timed_short", indexByRow(c(500L, 400L), idxs = c(1L, 7L, 400L, 200000L)))
    emit("timed_neg", indexByRow(c(500L, 400L), idxs = c(-1L, -2L)))
    """
    result = subprocess.run(
        ["Rscript", "-e", script],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise AssertionError(result.stderr)
    got = {}
    for line in result.stdout.splitlines():
        name, value = line.split("\t", 1)
        got[name] = value

    def indexes(expr):
        return " ".join(str(int(v)) for v in expr)

    assert indexes(indexByRow((5, 4))) == got["null54"]
    assert indexes(indexByRow((2, 3))) == got["null23"]
    assert indexes(indexByRow((5, 4), idxs=[1, 3, 7])) == got["short"]
    assert indexes(indexByRow((2, 3), idxs=[2, 2, 1])) == got["dup"]
    assert indexes(indexByRow((2, 3), idxs=[6, 1, 4])) == got["order"]
    assert indexes(indexByRow((2.9, 3.2), idxs=[1.2, 5.9, 6.1])) == got["frac"]
    assert indexes(indexByRow((2, 3), idxs=np.array([], dtype=np.int32))) == got["empty"]
    assert indexes(indexByRow((0, 4))) == got["dim0"]
    assert indexes(indexByRow((4, 1))) == got["onecol"]
    assert indexes(indexByRow((2, 3), idxs=True)) == got["lgl"]

    def message(call):
        with pytest.raises(ValueError) as caught:
            call()
        return "ERR " + str(caught.value)

    assert message(lambda: indexByRow((5, 4), idxs=[-1, -2])) == got["neg"]
    assert message(lambda: indexByRow((1, 1), idxs=[0])) == got["zero"]
    assert message(lambda: indexByRow((2, 3), idxs=[7])) == got["oob"]
    assert message(lambda: indexByRow((2, 3), idxs=[NA_INTEGER])) == got["na"]
    assert message(lambda: indexByRow((2147483647, 2), idxs=[1])) == got["big"]
    assert message(lambda: indexByRow((100000001, 100000001), idxs=[1])) == got["huge"]
    assert message(lambda: indexByRow((-1, 2))) == got["negdim"]
    assert message(lambda: indexByRow(np.array([[2, 3]]))) == got["mat"]
    assert message(lambda: indexByRow((2, 2), idxs=[1, -3, 2])) == got["posneg"]

    reference = np.fromfile("/tmp/indexByRow-r-full.bin", dtype=np.int32)
    translated = indexByRow((500, 400))
    assert translated.shape == reference.shape
    assert np.array_equal(translated, reference)
    assert int(np.max(np.abs(translated.astype(np.int64) - reference.astype(np.int64)))) == 0
    assert indexes(indexByRow((500, 400), idxs=[1, 7, 400, 200000])) == got["timed_short"]
    assert message(lambda: indexByRow((500, 400), idxs=[-1, -2])) == got["timed_neg"]
