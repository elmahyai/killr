"""Checks for rowOrderStats and colOrderStats, including a comparison with R."""

from __future__ import annotations

import math
import shutil
import subprocess
import tempfile
import textwrap
import warnings
from pathlib import Path

import numpy as np
import pytest

from matrixstats.roworderstats import colOrderStats, rowOrderStats

TOL = 1e-8
NA_INTEGER = np.iinfo(np.int32).min


def test_printed_integer_matrix_returns_each_order():
    printed = _printed_1_to_12()
    assert rowOrderStats(printed, which=1).dtype == np.int32
    assert rowOrderStats(printed, which=1).tolist() == [1, 2, 3, 4]
    assert rowOrderStats(printed, which=2).tolist() == [5, 6, 7, 8]
    assert rowOrderStats(printed, which=3).tolist() == [9, 10, 11, 12]
    assert colOrderStats(printed, which=1).dtype == np.int32
    assert colOrderStats(printed, which=1).tolist() == [1, 5, 9]
    assert colOrderStats(printed, which=2).tolist() == [2, 6, 10]
    assert colOrderStats(printed, which=4).tolist() == [4, 8, 12]
    assert rowOrderStats(np.arange(1, 13), dim=(4, 3), which=1).tolist() == [1, 2, 3, 4]
    assert colOrderStats(np.arange(1, 13), dim=(4, 3), which=2).tolist() == [2, 6, 10]
    fortran = np.asfortranarray(printed)
    assert rowOrderStats(fortran, which=2).tolist() == [5, 6, 7, 8]
    assert colOrderStats(np.array(printed, order="C"), which=1).tolist() == [1, 5, 9]


def test_ties_keep_the_repeated_order_statistic():
    printed = np.array(
        [[5, 5, 5], [1, 2, 1], [3, 3, 0], [2, 2, 2]],
        dtype=np.int32,
    )
    assert rowOrderStats(printed, which=1).tolist() == [5, 1, 0, 2]
    assert rowOrderStats(printed, which=2).tolist() == [5, 1, 3, 2]
    assert rowOrderStats(printed, which=3).tolist() == [5, 2, 3, 2]
    assert colOrderStats(printed, which=2).tolist() == [2, 2, 1]
    duplicated = rowOrderStats(printed, cols=[1, 1, 1], which=2)
    assert duplicated.tolist() == [5, 1, 3, 2]


def test_subsets_zeros_negatives_and_logical_indices():
    printed = _printed_1_to_12()
    assert rowOrderStats(printed, rows=[3, 1], which=2).tolist() == [7, 5]
    assert rowOrderStats(printed, cols=[3, 1], which=1).tolist() == [1, 2, 3, 4]
    assert rowOrderStats(printed, cols=[3, 1], which=2).tolist() == [9, 10, 11, 12]
    assert rowOrderStats(printed, cols=[-2], which=1).tolist() == [1, 2, 3, 4]
    assert rowOrderStats(printed, rows=[False, True], which=1).tolist() == [2, 4]
    assert rowOrderStats(printed, rows=[0, 2], which=1).tolist() == [2]
    assert rowOrderStats(printed, rows=0, which=1).shape == (0,)
    assert rowOrderStats(printed, rows=0, which=1).dtype == np.int32
    assert rowOrderStats(printed, rows=1.9, which=1).tolist() == [1]
    assert colOrderStats(printed, rows=[1, 3], which=1).tolist() == [1, 5, 9]
    assert colOrderStats(printed, rows=[1, 3], which=2).tolist() == [3, 7, 11]
    assert colOrderStats(printed, cols=[3, 1], which=1).tolist() == [9, 1]
    assert rowOrderStats(printed, rows=[], which=1).shape == (0,)
    assert colOrderStats(printed, cols=[], which=1).shape == (0,)


def test_missing_values_are_rejected_even_outside_the_subset():
    printed = np.array([[1.0, 2.0], [3.0, 4.0]])
    printed[0, 0] = np.nan
    with pytest.raises(ValueError, match="must not contain missing values"):
        rowOrderStats(printed, cols=[2], which=1)
    with pytest.raises(ValueError, match="must not contain missing values"):
        colOrderStats(printed, which=1)
    ints = np.array([[1, 2], [3, 4]], dtype=np.int32)
    ints[1, 1] = NA_INTEGER
    with pytest.raises(ValueError, match="must not contain missing values"):
        rowOrderStats(ints, which=1)
    with pytest.raises(ValueError, match="must not contain missing value"):
        rowOrderStats(_printed_1_to_12(), rows=[1, NA_INTEGER], which=1)
    with pytest.raises(ValueError, match="must not contain missing value"):
        colOrderStats(_printed_1_to_12(), cols=[1, None], which=1)


def test_which_follows_as_integer_and_rejects_a_bad_range():
    printed = _printed_1_to_12()
    assert rowOrderStats(printed, which=True).tolist() == [1, 2, 3, 4]
    assert rowOrderStats(printed, which=1.9).tolist() == [1, 2, 3, 4]
    assert rowOrderStats(printed, which=2.9).tolist() == [5, 6, 7, 8]
    with pytest.raises(ValueError, match=r"out of range: 0"):
        rowOrderStats(printed, which=False)
    with pytest.raises(ValueError, match=r"out of range: 4"):
        rowOrderStats(printed, which=4)
    with pytest.raises(ValueError, match=r"out of range: 5"):
        colOrderStats(printed, which=5)
    with pytest.raises(ValueError, match=r"out of range: -2147483648"):
        rowOrderStats(printed, which=NA_INTEGER)
    with pytest.raises(ValueError, match=r"out of range: -2147483648"):
        colOrderStats(printed, which=float("nan"))
    with pytest.raises(ValueError, match="single number"):
        rowOrderStats(printed, which=[1, 2])
    with pytest.raises(ValueError, match="numeric number"):
        colOrderStats(printed, which="a")
    with pytest.warns(RuntimeWarning, match="coercion to integer range"):
        with pytest.raises(ValueError, match=r"out of range: -2147483648"):
            rowOrderStats(printed, which=1e20)
    with pytest.raises(ValueError, match=r"out of range: 1"):
        rowOrderStats(printed, cols=[], which=1)
    with pytest.raises(ValueError, match=r"out of range: 1"):
        colOrderStats(printed, rows=[], which=1)


def test_signed_zeros_follow_r_psort():
    printed = np.array([[-0.0, 0.0], [0.0, -0.0]])
    first = rowOrderStats(printed, which=1)
    second = rowOrderStats(printed, which=2)
    assert first[0].view(np.uint64) == np.uint64(0)
    assert first[1].view(np.uint64) == np.uint64(0x8000000000000000)
    assert second[0].view(np.uint64) == np.uint64(0x8000000000000000)
    assert second[1].view(np.uint64) == np.uint64(0)
    columns = colOrderStats(printed, which=1)
    assert columns[0].view(np.uint64) == np.uint64(0)
    assert columns[1].view(np.uint64) == np.uint64(0x8000000000000000)


def test_rejects_logical_input_bad_flags_and_subscripts():
    with pytest.raises(ValueError, match="cannot be logical"):
        rowOrderStats(np.array([[True, False]]), which=1)
    with pytest.raises(ValueError, match="character"):
        colOrderStats(np.array(["a", "b"]), dim=(2, 1), which=1)
    with pytest.raises(ValueError, match="dim."):
        rowOrderStats(np.arange(4.0), dim=(2, 3), which=1)
    with pytest.raises(ValueError, match="TRUE or FALSE"):
        rowOrderStats(_printed_1_to_12(), which=1, use_names=2)
    with pytest.raises(ValueError, match="must be a logical"):
        colOrderStats(_printed_1_to_12(), which=1, use_names=1.5)
    with pytest.raises(ValueError, match="subscript out of bounds"):
        rowOrderStats(_printed_1_to_12(), rows=[5], which=1)
    with pytest.raises(ValueError, match="negative subscripts"):
        colOrderStats(_printed_1_to_12(), cols=[-1.0, 1.0], which=1)
    with pytest.raises(ValueError, match="logical subscript too long"):
        rowOrderStats(_printed_1_to_12(), rows=[True, False, True, False, True], which=1)
    assert rowOrderStats(_printed_1_to_12(), which=1, use_names=0).tolist() == [1, 2, 3, 4]
    empty = rowOrderStats(np.zeros((0, 3), dtype=np.int32), which=1)
    assert empty.shape == (0,)
    assert empty.dtype == np.int32
    assert colOrderStats(np.zeros((4, 0), dtype=np.float64), which=1).shape == (0,)


def test_matches_r_on_ties_subsets_zeros_and_errors():
    if shutil.which("Rscript") is None:
        pytest.skip("Rscript is unavailable")
    with tempfile.TemporaryDirectory() as tmp:
        _matches_r(Path(tmp))


def _matches_r(tmp: Path):
    draw_path = tmp / "draw.bin"
    script = textwrap.dedent(
        """
        suppressPackageStartupMessages(library(matrixStats))
        fail <- function(expr) {
          message <- tryCatch({
            force(expr)
            "OK"
          }, error = function(e) conditionMessage(e))
          cat(message, "\\n", sep = "")
        }
        x <- matrix(1:12, nrow = 4, ncol = 3)
        ties <- matrix(c(5, 5, 5, 1, 2, 1, 3, 3, 0, 2, 2, 2), nrow = 4, byrow = TRUE)
        zeros <- matrix(c(-0, 0, 0, -0), nrow = 2, byrow = TRUE)
        set.seed(1)
        draw <- matrix(rnorm(30 * 18), nrow = 30, ncol = 18)
        draw[c(3, 8, 21)] <- draw[1]
        writeBin(as.numeric(draw), "DRAWPATH")
        emit <- function(name, values) {
          cat("VAL ", name, " ", storage.mode(values), "\\n", sep = "")
          cat(sprintf("%.17g", as.numeric(values)), sep = "\\n")
          cat("END\\n")
        }
        emit("row1", rowOrderStats(x, which = 1))
        emit("row2", rowOrderStats(x, which = 2))
        emit("col1", colOrderStats(x, which = 1))
        emit("col4", colOrderStats(x, which = 4))
        emit("ties1", rowOrderStats(ties, which = 1))
        emit("ties2", rowOrderStats(ties, which = 2))
        emit("ties3", rowOrderStats(ties, which = 3))
        emit("colties", colOrderStats(ties, which = 2))
        emit("rows", rowOrderStats(x, rows = c(3, 1), which = 2))
        emit("cols", rowOrderStats(x, cols = c(3, 1), which = 2))
        emit("neg", rowOrderStats(x, cols = -2, which = 1))
        emit("frac", rowOrderStats(x, rows = 1.9, which = 1))
        emit("vector", rowOrderStats(1:12, dim. = c(4, 3), which = 1))
        emit("colrows", colOrderStats(x, rows = c(1, 3), which = 2))
        emit("zrow1", rowOrderStats(zeros, which = 1))
        emit("zrow2", rowOrderStats(zeros, which = 2))
        emit("zcol1", colOrderStats(zeros, which = 1))
        emit("zcol2", colOrderStats(zeros, which = 2))
        emit("drawrow1", rowOrderStats(draw, which = 1))
        emit("drawrow9", rowOrderStats(draw, which = 9))
        emit("drawcol1", colOrderStats(draw, which = 1))
        emit("drawcol15", colOrderStats(draw, which = 15))
        cat("ERR na\\n")
        bad <- x
        bad[1, 1] <- NA
        fail(rowOrderStats(bad, cols = 2:3, which = 1))
        cat("ERR which\\n")
        fail(colOrderStats(x, which = 5))
        cat("ERR rowsna\\n")
        fail(rowOrderStats(x, rows = c(1, NA), which = 1))
        """
    ).replace("DRAWPATH", draw_path.as_posix())
    completed = subprocess.run(
        ["Rscript", "--vanilla", "-"],
        input=script,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        pytest.skip(completed.stderr.strip() or "matrixStats is unavailable")
    blocks = _parse_r(completed.stdout)
    printed = _printed_1_to_12()
    _assert_values(rowOrderStats(printed, which=1), blocks["row1"])
    _assert_values(rowOrderStats(printed, which=2), blocks["row2"])
    _assert_values(colOrderStats(printed, which=1), blocks["col1"])
    _assert_values(colOrderStats(printed, which=4), blocks["col4"])
    ties = np.array([[5, 5, 5], [1, 2, 1], [3, 3, 0], [2, 2, 2]], dtype=np.int32)
    _assert_values(rowOrderStats(ties, which=1), blocks["ties1"])
    _assert_values(rowOrderStats(ties, which=2), blocks["ties2"])
    _assert_values(rowOrderStats(ties, which=3), blocks["ties3"])
    _assert_values(colOrderStats(ties, which=2), blocks["colties"])
    _assert_values(rowOrderStats(printed, rows=[3, 1], which=2), blocks["rows"])
    _assert_values(rowOrderStats(printed, cols=[3, 1], which=2), blocks["cols"])
    _assert_values(rowOrderStats(printed, cols=[-2], which=1), blocks["neg"])
    _assert_values(rowOrderStats(printed, rows=1.9, which=1), blocks["frac"])
    _assert_values(rowOrderStats(np.arange(1, 13), dim=(4, 3), which=1), blocks["vector"])
    _assert_values(colOrderStats(printed, rows=[1, 3], which=2), blocks["colrows"])
    zeros = np.array([[-0.0, 0.0], [0.0, -0.0]])
    _assert_values(rowOrderStats(zeros, which=1), blocks["zrow1"])
    _assert_values(rowOrderStats(zeros, which=2), blocks["zrow2"])
    _assert_values(colOrderStats(zeros, which=1), blocks["zcol1"])
    _assert_values(colOrderStats(zeros, which=2), blocks["zcol2"])
    draw = np.reshape(np.fromfile(draw_path, dtype="<f8"), (30, 18), order="F")
    _assert_values(rowOrderStats(draw, which=1), blocks["drawrow1"])
    _assert_values(rowOrderStats(draw, which=9), blocks["drawrow9"])
    _assert_values(colOrderStats(draw, which=1), blocks["drawcol1"])
    _assert_values(colOrderStats(draw, which=15), blocks["drawcol15"])
    with pytest.raises(ValueError, match="must not contain missing values"):
        poisoned = printed.astype(np.float64)
        poisoned[0, 0] = np.nan
        rowOrderStats(poisoned, cols=[2, 3], which=1)
    assert "must not contain missing values" in blocks["na"]
    assert blocks["which"] == "Argument 'which' is out of range: 5"
    assert blocks["rowsna"] == "Argument 'rows' must not contain missing value"


def _printed_1_to_12():
    return np.arange(1, 13, dtype=np.int32).reshape((4, 3), order="F")


def _parse_r(text):
    blocks = {}
    lines = text.splitlines()
    index = 0
    while index < len(lines):
        line = lines[index]
        if line.startswith("VAL "):
            _, name, mode = line.split(" ", 2)
            index += 1
            values = []
            while lines[index] != "END":
                values.append(float(lines[index]))
                index += 1
            blocks[name] = (mode, np.array(values, dtype=np.float64))
        elif line.startswith("ERR "):
            name = line.split(" ", 1)[1]
            index += 1
            blocks[name] = lines[index]
        index += 1
    return blocks


def _assert_values(actual, expected):
    mode, values = expected
    actual = np.asarray(actual).reshape(-1)
    assert actual.shape == values.shape
    if mode == "integer":
        assert actual.dtype == np.int32
        assert np.array_equal(actual, values.astype(np.int32))
        return
    for got, want in zip(actual, values):
        got_f = float(got)
        want_f = float(want)
        if (
            not math.isfinite(want_f)
            or not math.isfinite(got_f)
            or (got_f == 0.0 and want_f == 0.0)
        ):
            assert np.array(got_f).view(np.uint64) == np.array(want_f).view(np.uint64)
        else:
            assert abs(got_f - want_f) <= TOL


def test_warning_filter_stays_quiet_for_an_ordinary_which():
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        rowOrderStats(_printed_1_to_12(), which=2)
