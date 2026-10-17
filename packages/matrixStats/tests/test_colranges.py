"""Checks for colRanges, colMins, and colMaxs, including a comparison with R."""

from __future__ import annotations

import shutil
import subprocess
import textwrap

import numpy as np
import pytest

from matrixstats.colranges import colMaxs, colMins, colRanges

TOL = 1e-8
NA_INTEGER = np.iinfo(np.int32).min
NA_REAL_BITS = np.uint64(0x7FF00000000007A2)


def test_printed_integer_matrix_returns_min_and_max():
    printed = _printed_1_to_12()
    ranges = colRanges(printed)
    mins = colMins(printed)
    maxs = colMaxs(printed)
    assert ranges.dtype == np.int32
    assert ranges.shape == (3, 2)
    assert ranges.tolist() == [[1, 4], [5, 8], [9, 12]]
    assert mins.dtype == np.int32
    assert mins.tolist() == [1, 5, 9]
    assert maxs.tolist() == [4, 8, 12]
    assert colRanges(np.arange(1, 13), dim=(4, 3)).tolist() == ranges.tolist()
    fortran = np.asfortranarray(printed)
    assert colMins(fortran).tolist() == mins.tolist()
    assert colMaxs(np.array(printed, order="C")).tolist() == maxs.tolist()


def test_double_matrix_and_row_subset():
    printed = np.array(
        [[1.0, 5.0, 9.0], [2.0, 6.0, 10.0], [3.0, 7.0, 11.0], [4.0, 8.0, 12.0]]
    )
    assert colRanges(printed).tolist() == [[1.0, 4.0], [5.0, 8.0], [9.0, 12.0]]
    subset = colRanges(printed, rows=[4, 1])
    assert subset.tolist() == [[1.0, 4.0], [5.0, 8.0], [9.0, 12.0]]
    assert colMins(printed, rows=[0, 3]).tolist() == [3.0, 7.0, 11.0]
    assert colMaxs(printed, rows=[-4]).tolist() == [3.0, 7.0, 11.0]


def test_r_na_stops_and_plain_nan_keeps_the_last_payload():
    na = np.array(np.uint64(NA_REAL_BITS).view(np.float64))
    quiet = np.array(np.uint64(0x7FF80000000007A2).view(np.float64))
    first = np.array(np.uint64(0x7FF8000000000001).view(np.float64))
    second = np.array(np.uint64(0x7FF8000000000002).view(np.float64))

    stopped = colMins(np.array([[3.0], [quiet], [-9.0]]))
    assert stopped.dtype == np.float64
    assert stopped.view(np.uint64)[0] == np.uint64(quiet.view(np.uint64))

    both = colRanges(np.array([[5.0], [na], [9.0]]))
    assert np.all(both.view(np.uint64) == NA_REAL_BITS)

    overwritten = colRanges(np.array([[8.0], [first], [-3.0], [second], [4.0]]))
    assert np.all(overwritten.view(np.uint64) == np.uint64(second.view(np.uint64)))

    blocked = colMins(np.array([[first], [-5.0]]))
    assert blocked.view(np.uint64)[0] == np.uint64(first.view(np.uint64))

    kept = colRanges(np.array([[5.0], [np.nan], [1.0]]), na_rm=True)
    assert kept.tolist() == [[1.0, 5.0]]
    empty = colRanges(np.array([[na], [np.nan]]), na_rm=True)
    assert np.isposinf(empty[0, 0]) and np.isneginf(empty[0, 1])


def test_integer_na_promotes_only_when_a_column_counts_nothing():
    na = NA_INTEGER
    printed = np.array([[1, 3, na], [na, 2, 0], [4, 1, 5]], dtype=np.int32)
    mins = colMins(printed)
    assert mins.dtype == np.int32
    assert mins.tolist() == [na, 1, na]
    assert colMins(printed, na_rm=True).tolist() == [1, 1, 0]
    ranges = colRanges(printed, na_rm=True)
    assert ranges.dtype == np.int32
    assert ranges.tolist() == [[1, 4], [1, 3], [0, 5]]

    mixed = np.array([[1, na], [2, na]], dtype=np.int32)
    promoted = colRanges(mixed, na_rm=True)
    assert promoted.dtype == np.float64
    assert promoted[0].tolist() == [1.0, 2.0]
    assert np.isposinf(promoted[1, 0]) and np.isneginf(promoted[1, 1])
    assert colMaxs(mixed, na_rm=True).dtype == np.float64


def test_na_row_subset_respects_scan_order():
    printed = np.array([[1.0, np.nan, 4.0], [2.0, 3.0, 5.0]])
    stopped = colRanges(printed, rows=[1, 2])
    assert stopped[0].tolist() == [1.0, 2.0]
    assert np.isnan(stopped[1]).all()
    assert stopped[2].tolist() == [4.0, 5.0]
    dropped = colMins(printed, cols=[2, 3], na_rm=True)
    assert dropped.tolist() == [3.0, 4.0]
    early = colMaxs(printed, rows=[2, 1])
    assert early[0] == 2.0
    assert np.isnan(early[1])
    assert early[2] == 5.0


def test_signed_zero_cols_subset_and_empty_margins():
    neg = colRanges(np.array([[-0.0], [0.0]]))
    assert neg.reshape(-1).view(np.uint64).tolist() == [np.uint64(0x8000000000000000)] * 2
    assert colMins(np.array([[1.0], [-0.0]])).view(np.uint64)[0] == np.uint64(
        0x8000000000000000
    )
    printed = _printed_1_to_12()
    assert colMins(printed, cols=[3, 0, 1]).tolist() == [9, 1]
    assert colMaxs(printed, cols=[True, False]).tolist() == [4, 12]
    assert colRanges(printed, cols=[]).shape == (0, 2)
    assert colRanges(printed, cols=[]).dtype == np.int32
    empty_rows = colMins(np.zeros((0, 3), dtype=np.int32))
    assert empty_rows.dtype == np.float64
    assert empty_rows.shape == (3,)
    assert np.isposinf(empty_rows).all()
    empty_cols = colRanges(np.zeros((2, 0), dtype=np.int32))
    assert empty_cols.dtype == np.int32
    assert empty_cols.shape == (0, 2)
    assert colRanges(np.zeros((0, 0), dtype=np.int32)).dtype == np.int32
    assert colRanges(np.zeros((0, 0), dtype=float)).shape == (0, 2)
    no_rows = colRanges(np.zeros((0, 2), dtype=np.int32))
    assert no_rows.dtype == np.float64
    assert np.isposinf(no_rows[:, 0]).all()
    assert np.isneginf(no_rows[:, 1]).all()


def test_dim_reinterprets_column_major_storage():
    printed = _printed_1_to_12()
    got = colMins(printed, dim=(6, 2))
    assert got.shape == (2,)
    assert got.tolist() == [1, 7]
    sliced = printed[::2, :]
    assert colMaxs(sliced).tolist() == [3, 7, 11]


def test_rejects_logical_input_bad_flags_and_subscripts():
    with pytest.raises(ValueError, match="cannot be logical"):
        colMins(np.array([[True, False]]))
    with pytest.raises(ValueError, match="dim."):
        colRanges(np.arange(4.0), dim=(2, 3))
    with pytest.raises(ValueError, match="TRUE or FALSE"):
        colMins(_printed_1_to_12(), na_rm=2)
    with pytest.raises(ValueError, match="must be a logical"):
        colMaxs(_printed_1_to_12(), use_names=1.5)
    with pytest.raises(ValueError, match="subscript out of bounds"):
        colRanges(_printed_1_to_12(), cols=[5])
    with pytest.raises(ValueError, match="negative subscripts"):
        colMins(_printed_1_to_12(), rows=[-1.0, 1.0])
    with pytest.raises(ValueError, match="logical subscript too long"):
        colMaxs(_printed_1_to_12(), cols=[True, False, True, False])
    with pytest.raises(ValueError, match="character"):
        colRanges(np.array(["a", "b"]))
    assert colMins(_printed_1_to_12(), na_rm=0).tolist() == [1, 5, 9]
    assert colMins(_printed_1_to_12(), cols=True).tolist() == [1, 5, 9]
    assert colMins(_printed_1_to_12(), cols=False).shape == (0,)
    assert colMins(_printed_1_to_12(), cols=1).tolist() == [1]


def test_matches_r_on_na_row_subsets_and_types():
    if shutil.which("Rscript") is None:
        pytest.skip("Rscript is unavailable")
    reference = _r_suite()
    if reference is None:
        pytest.skip("matrixStats is unavailable")

    printed = _printed_1_to_12()
    _assert_match(colRanges(printed), reference["ranges"])
    _assert_match(colMins(printed), reference["mins"])
    _assert_match(colMaxs(printed), reference["maxs"])
    _assert_match(colRanges(printed, rows=[4, 1]), reference["rows"])
    _assert_match(colMins(printed, rows=[0, 3]), reference["rows_zero"])
    _assert_match(colMaxs(printed, rows=[-4]), reference["rows_neg"])
    _assert_match(colMins(printed, cols=[3, 0, 1]), reference["cols"])
    _assert_match(colRanges(np.arange(1, 13), dim=(4, 3)), reference["vector"])
    _assert_match(colMins(printed, rows=1.9), reference["frac"])

    na = np.array([[1.0, 0.0, 9.0], [2.0, 6.0, 10.0], [4.0, 1.0, 5.0]])
    na.view(np.uint64)[0, 1] = NA_REAL_BITS
    _assert_match(colRanges(na), reference["na_ranges"])
    _assert_match(colMins(na, na_rm=True), reference["na_mins"])
    _assert_match(colMaxs(na, rows=[2, 3, 1]), reference["na_rows"])
    _assert_match(colRanges(na, cols=[2, 3], na_rm=True), reference["na_cols_rm"])

    ints = np.array([[1, 3, NA_INTEGER], [NA_INTEGER, 2, 0], [4, 1, 5]], dtype=np.int32)
    _assert_match(colRanges(ints), reference["int_ranges"])
    _assert_match(colMins(ints, na_rm=True), reference["int_mins"])
    mixed = np.array([[1, NA_INTEGER], [2, NA_INTEGER]], dtype=np.int32)
    _assert_match(colRanges(mixed, na_rm=True), reference["promoted"])
    _assert_match(colMaxs(mixed, na_rm=True), reference["promoted_max"])

    _assert_match(colRanges(reference["matrix"]), reference["big_ranges"])
    _assert_match(colMins(reference["matrix"], rows=[4, 2, 7]), reference["big_rows"])
    poisoned = np.array(reference["matrix"], order="C", copy=True)
    poisoned.view(np.uint64)[1, 3] = NA_REAL_BITS
    poisoned.view(np.uint64)[5, 0] = NA_REAL_BITS
    _assert_match(colRanges(poisoned, na_rm=False), reference["poison"])
    _assert_match(colMins(poisoned, rows=[4, 1, 2], na_rm=True), reference["poison_rows"])

    _assert_match(colRanges(reference["check"]), reference["check_ranges"])
    _assert_match(colMins(reference["check"], na_rm=False), reference["check_mins"])
    _assert_match(colMaxs(reference["check"], na_rm=False), reference["check_maxs"])


def _printed_1_to_12():
    return np.arange(1, 13, dtype=np.int32).reshape((4, 3), order="F")


def _assert_match(actual, expected):
    actual = np.asarray(actual)
    kind, values = expected
    if values.ndim == 2 and values.shape[1] == 1 and actual.ndim == 1:
        values = values.reshape(-1)
    assert actual.shape == values.shape
    if kind == "integer":
        assert actual.dtype == np.int32
        assert np.array_equal(actual, values.astype(np.int32))
        return
    assert actual.dtype == np.float64
    actual_bits = actual.view(np.uint64)
    expected_bits = values.view(np.uint64)
    actual_f = actual.reshape(-1)
    expected_f = values.reshape(-1)
    actual_b = actual_bits.reshape(-1)
    expected_b = expected_bits.reshape(-1)
    worst = 0.0
    for got, want, got_bits, want_bits in zip(actual_f, expected_f, actual_b, expected_b):
        if not np.isfinite(want) or not np.isfinite(got):
            assert got_bits == want_bits
        else:
            worst = max(worst, abs(float(got) - float(want)))
            assert abs(float(got) - float(want)) <= TOL
    return worst


def _r_suite():
    script = textwrap.dedent(
        r"""
        args <- commandArgs(trailingOnly=TRUE)
        bin <- args[[1]]
        check <- args[[2]]
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
        x <- matrix(1:12, nrow=4)
        emit("ranges", matrixStats::colRanges(x))
        emit("mins", matrixStats::colMins(x))
        emit("maxs", matrixStats::colMaxs(x))
        emit("rows", matrixStats::colRanges(x, rows=c(4, 1)))
        emit("rows_zero", matrixStats::colMins(x, rows=c(0, 3)))
        emit("rows_neg", matrixStats::colMaxs(x, rows=c(-4)))
        emit("cols", matrixStats::colMins(x, cols=c(3, 0, 1)))
        emit("vector", matrixStats::colRanges(as.integer(x), dim.=c(4L, 3L)))
        emit("frac", matrixStats::colMins(x, rows=1.9))

        na_x <- matrix(c(1, 2, 4, NA, 6, 1, 9, 10, 5), nrow=3)
        emit("na_ranges", matrixStats::colRanges(na_x))
        emit("na_mins", matrixStats::colMins(na_x, na.rm=TRUE))
        emit("na_rows", matrixStats::colMaxs(na_x, rows=c(2, 3, 1)))
        emit("na_cols_rm", matrixStats::colRanges(na_x, cols=c(2, 3), na.rm=TRUE))

        int_x <- matrix(c(1L, NA_integer_, 4L, 3L, 2L, 1L, NA_integer_, 0L, 5L), nrow=3)
        emit("int_ranges", matrixStats::colRanges(int_x))
        emit("int_mins", matrixStats::colMins(int_x, na.rm=TRUE))
        mixed <- matrix(c(1L, 2L, NA_integer_, NA_integer_), nrow=2)
        emit("promoted", matrixStats::colRanges(mixed, na.rm=TRUE))
        emit("promoted_max", matrixStats::colMaxs(mixed, na.rm=TRUE))

        set.seed(1)
        big <- matrix(rnorm(40 * 25), nrow=40, ncol=25)
        writeBin(as.numeric(big), bin)
        emit("big_ranges", matrixStats::colRanges(big, na.rm=FALSE))
        emit("big_rows", matrixStats::colMins(big, rows=c(4, 2, 7)))
        big[2, 4] <- NA
        big[6, 1] <- NA
        emit("poison", matrixStats::colRanges(big))
        emit("poison_rows", matrixStats::colMins(big, rows=c(4, 1, 2), na.rm=TRUE))

        set.seed(1)
        wide <- matrix(rnorm(400 * 250), nrow=400, ncol=250)
        writeBin(as.numeric(wide), check)
        emit("check_ranges", matrixStats::colRanges(wide, na.rm=FALSE))
        emit("check_mins", matrixStats::colMins(wide, na.rm=FALSE))
        emit("check_maxs", matrixStats::colMaxs(wide, na.rm=FALSE))
        """
    )
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        program = root / "check.R"
        data = root / "big.bin"
        check = root / "check.bin"
        program.write_text(script)
        result = subprocess.run(
            ["Rscript", str(program), str(data), str(check)],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode == 2:
            return None
        if result.returncode != 0:
            raise RuntimeError(result.stderr)
        parsed = _parse_blocks(result.stdout)
        matrix = np.fromfile(data, dtype="<f8").reshape((40, 25), order="F")
        parsed["matrix"] = np.array(matrix, order="C", copy=True)
        check_matrix = np.fromfile(check, dtype="<f8").reshape((400, 250), order="F")
        parsed["check"] = np.array(check_matrix, order="C", copy=True)
        return parsed


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
