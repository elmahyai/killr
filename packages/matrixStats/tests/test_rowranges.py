"""Checks for rowRanges, rowMins, and rowMaxs, including a comparison with R."""

from __future__ import annotations

import shutil
import subprocess
import textwrap

import numpy as np
import pytest

from matrixstats.rowranges import rowMaxs, rowMins, rowRanges

TOL = 1e-8
NA_INTEGER = np.iinfo(np.int32).min
NA_REAL_BITS = np.uint64(0x7FF00000000007A2)


def test_printed_integer_matrix_returns_min_and_max():
    printed = _printed_1_to_12()
    ranges = rowRanges(printed)
    mins = rowMins(printed)
    maxs = rowMaxs(printed)
    assert ranges.dtype == np.int32
    assert ranges.shape == (4, 2)
    assert ranges.tolist() == [[1, 9], [2, 10], [3, 11], [4, 12]]
    assert mins.dtype == np.int32
    assert mins.tolist() == [1, 2, 3, 4]
    assert maxs.tolist() == [9, 10, 11, 12]
    assert rowRanges(np.arange(1, 13), dim=(4, 3)).tolist() == ranges.tolist()
    fortran = np.asfortranarray(printed)
    assert rowMins(fortran).tolist() == mins.tolist()
    assert rowMaxs(np.array(printed, order="C")).tolist() == maxs.tolist()


def test_double_matrix_and_column_subset():
    printed = np.array(
        [[1.0, 5.0, 9.0], [2.0, 6.0, 10.0], [3.0, 7.0, 11.0], [4.0, 8.0, 12.0]]
    )
    assert rowRanges(printed).tolist() == [
        [1.0, 9.0],
        [2.0, 10.0],
        [3.0, 11.0],
        [4.0, 12.0],
    ]
    subset = rowRanges(printed, cols=[3, 1])
    assert subset.tolist() == rowRanges(printed[:, [2, 0]]).tolist()
    assert rowMins(printed, cols=[0, 2]).tolist() == [5.0, 6.0, 7.0, 8.0]
    assert rowMaxs(printed, cols=[-2]).tolist() == [9.0, 10.0, 11.0, 12.0]


def test_r_na_stops_and_plain_nan_keeps_the_last_payload():
    na = np.array(np.uint64(NA_REAL_BITS).view(np.float64))
    quiet = np.array(np.uint64(0x7FF80000000007A2).view(np.float64))
    first = np.array(np.uint64(0x7FF8000000000001).view(np.float64))
    second = np.array(np.uint64(0x7FF8000000000002).view(np.float64))

    stopped = rowMins(np.array([[3.0, quiet, -9.0]]))
    assert stopped.dtype == np.float64
    assert stopped.view(np.uint64)[0] == np.uint64(quiet.view(np.uint64))

    both = rowRanges(np.array([[5.0, na, 9.0]]))
    assert np.all(both.view(np.uint64) == NA_REAL_BITS)

    overwritten = rowRanges(np.array([[8.0, first, -3.0, second, 4.0]]))
    assert np.all(overwritten.view(np.uint64) == np.uint64(second.view(np.uint64)))

    blocked = rowMins(np.array([[first, -5.0]]))
    assert blocked.view(np.uint64)[0] == np.uint64(first.view(np.uint64))

    kept = rowRanges(np.array([[5.0, np.nan, 1.0]]), na_rm=True)
    assert kept.tolist() == [[1.0, 5.0]]
    empty = rowRanges(np.array([[na, np.nan]]), na_rm=True)
    assert np.isposinf(empty[0, 0]) and np.isneginf(empty[0, 1])


def test_integer_na_promotes_only_when_a_row_counts_nothing():
    na = NA_INTEGER
    printed = np.array([[1, 3, na], [na, 2, 0], [4, 1, 5]], dtype=np.int32)
    mins = rowMins(printed)
    assert mins.dtype == np.int32
    assert mins.tolist() == [na, na, 1]
    assert rowMins(printed, na_rm=True).tolist() == [1, 0, 1]
    ranges = rowRanges(printed, na_rm=True)
    assert ranges.dtype == np.int32
    assert ranges.tolist() == [[1, 3], [0, 2], [1, 5]]

    mixed = np.array([[1, 2], [na, na]], dtype=np.int32)
    promoted = rowRanges(mixed, na_rm=True)
    assert promoted.dtype == np.float64
    assert promoted[0].tolist() == [1.0, 2.0]
    assert np.isposinf(promoted[1, 0]) and np.isneginf(promoted[1, 1])
    assert rowMaxs(mixed, na_rm=True).dtype == np.float64


def test_na_column_subset_respects_scan_order():
    printed = np.array([[1.0, np.nan, 4.0], [2.0, 3.0, 5.0]])
    stopped = rowRanges(printed, cols=[2, 3])
    assert np.isnan(stopped[0]).all()
    assert stopped[1].tolist() == [3.0, 5.0]
    dropped = rowMins(printed, cols=[2, 3], na_rm=True)
    assert dropped.tolist() == [4.0, 3.0]
    early = rowMaxs(printed, cols=[2, 1])
    assert np.isnan(early[0])
    assert early[1] == 3.0


def test_signed_zero_rows_subset_and_empty_margins():
    neg = rowRanges(np.array([[-0.0, 0.0]]))
    assert neg.reshape(-1).view(np.uint64).tolist() == [
        np.uint64(0x8000000000000000)
    ] * 2
    assert rowMins(np.array([[1.0, -0.0]])).view(np.uint64)[0] == np.uint64(
        0x8000000000000000
    )
    printed = _printed_1_to_12()
    assert rowMins(printed, rows=[3, 0, 1]).tolist() == [3, 1]
    assert rowMaxs(printed, rows=[False, True]).tolist() == [10, 12]
    assert rowRanges(printed, rows=[]).shape == (0, 2)
    assert rowMins(np.zeros((0, 3), dtype=np.int32)).shape == (0,)
    assert rowMins(np.zeros((0, 3), dtype=np.int32)).dtype == np.int32
    empty_cols = rowRanges(np.zeros((2, 0), dtype=np.int32))
    assert empty_cols.dtype == np.float64
    assert np.isposinf(empty_cols[:, 0]).all()
    assert np.isneginf(empty_cols[:, 1]).all()
    assert rowRanges(np.zeros((0, 0), dtype=np.int32)).dtype == np.int32
    assert rowRanges(np.zeros((0, 0), dtype=float)).shape == (0, 2)


def test_dim_reinterprets_column_major_storage():
    printed = _printed_1_to_12()
    got = rowMins(printed, dim=(6, 2))
    assert got.shape == (6,)
    assert got[0] == 1 and got[5] == 6
    sliced = printed[::1, :]
    assert rowMaxs(sliced).tolist() == [9, 10, 11, 12]


def test_rejects_logical_input_bad_flags_and_subscripts():
    with pytest.raises(ValueError, match="cannot be logical"):
        rowMins(np.array([[True, False]]))
    with pytest.raises(ValueError, match="dim."):
        rowRanges(np.arange(4.0), dim=(2, 3))
    with pytest.raises(ValueError, match="TRUE or FALSE"):
        rowMins(_printed_1_to_12(), na_rm=2)
    with pytest.raises(ValueError, match="must be a logical"):
        rowMaxs(_printed_1_to_12(), use_names=1.5)
    with pytest.raises(ValueError, match="subscript out of bounds"):
        rowRanges(_printed_1_to_12(), rows=[5])
    with pytest.raises(ValueError, match="negative subscripts"):
        rowMins(_printed_1_to_12(), cols=[-1.0, 1.0])
    with pytest.raises(ValueError, match="logical subscript too long"):
        rowMaxs(_printed_1_to_12(), rows=[True, False, True, False, True])
    with pytest.raises(ValueError, match="character"):
        rowRanges(np.array(["a", "b"]))
    assert rowMins(_printed_1_to_12(), na_rm=0).tolist() == [1, 2, 3, 4]
    assert rowMins(_printed_1_to_12(), rows=True).tolist() == [1, 2, 3, 4]
    assert rowMins(_printed_1_to_12(), rows=False).shape == (0,)
    assert rowMins(_printed_1_to_12(), rows=1).tolist() == [1]


def test_matches_r_on_na_column_subsets_and_types():
    if shutil.which("Rscript") is None:
        pytest.skip("Rscript is unavailable")
    reference = _r_suite()
    if reference is None:
        pytest.skip("matrixStats is unavailable")

    printed = _printed_1_to_12()
    _assert_match(rowRanges(printed), reference["ranges"])
    _assert_match(rowMins(printed), reference["mins"])
    _assert_match(rowMaxs(printed), reference["maxs"])
    _assert_match(rowRanges(printed, cols=[3, 1]), reference["cols"])
    _assert_match(rowMins(printed, cols=[0, 2]), reference["cols_zero"])
    _assert_match(rowMaxs(printed, cols=[-2]), reference["cols_neg"])
    _assert_match(rowMins(printed, rows=[3, 0, 1]), reference["rows"])
    _assert_match(rowRanges(np.arange(1, 13), dim=(4, 3)), reference["vector"])
    _assert_match(rowMins(printed, rows=1.9), reference["frac"])

    na = np.array([[1.0, 0.0, 9.0], [2.0, 6.0, 10.0], [4.0, 1.0, 5.0]])
    na.view(np.uint64)[0, 1] = NA_REAL_BITS
    _assert_match(rowRanges(na), reference["na_ranges"])
    _assert_match(rowMins(na, na_rm=True), reference["na_mins"])
    _assert_match(rowMaxs(na, cols=[2, 3, 1]), reference["na_cols"])
    _assert_match(rowRanges(na, cols=[2, 3], na_rm=True), reference["na_cols_rm"])

    ints = np.array([[1, 3, NA_INTEGER], [NA_INTEGER, 2, 0], [4, 1, 5]], dtype=np.int32)
    _assert_match(rowRanges(ints), reference["int_ranges"])
    _assert_match(rowMins(ints, na_rm=True), reference["int_mins"])
    mixed = np.array([[1, 2], [NA_INTEGER, NA_INTEGER]], dtype=np.int32)
    _assert_match(rowRanges(mixed, na_rm=True), reference["promoted"])
    _assert_match(rowMaxs(mixed, na_rm=True), reference["promoted_max"])

    _assert_match(rowRanges(reference["matrix"]), reference["big_ranges"])
    _assert_match(rowMins(reference["matrix"], cols=[4, 2, 7]), reference["big_cols"])
    poisoned = np.array(reference["matrix"], order="C", copy=True)
    poisoned.view(np.uint64)[1, 3] = NA_REAL_BITS
    poisoned.view(np.uint64)[5, 0] = NA_REAL_BITS
    _assert_match(rowRanges(poisoned, na_rm=False), reference["poison"])
    _assert_match(rowMins(poisoned, cols=[4, 1, 2], na_rm=True), reference["poison_cols"])


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
    for got, want, got_bits, want_bits in zip(actual_f, expected_f, actual_b, expected_b):
        if not np.isfinite(want) or not np.isfinite(got):
            assert got_bits == want_bits
        else:
            assert abs(float(got) - float(want)) <= TOL


def _r_suite():
    script = textwrap.dedent(
        r"""
        args <- commandArgs(trailingOnly=TRUE)
        bin <- args[[1]]
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
        emit("ranges", matrixStats::rowRanges(x))
        emit("mins", matrixStats::rowMins(x))
        emit("maxs", matrixStats::rowMaxs(x))
        emit("cols", matrixStats::rowRanges(x, cols=c(3, 1)))
        emit("cols_zero", matrixStats::rowMins(x, cols=c(0, 2)))
        emit("cols_neg", matrixStats::rowMaxs(x, cols=c(-2)))
        emit("rows", matrixStats::rowMins(x, rows=c(3, 0, 1)))
        emit("vector", matrixStats::rowRanges(as.integer(x), dim.=c(4L, 3L)))
        emit("frac", matrixStats::rowMins(x, rows=1.9))

        na_x <- matrix(c(1, 2, 4, NA, 6, 1, 9, 10, 5), nrow=3)
        emit("na_ranges", matrixStats::rowRanges(na_x))
        emit("na_mins", matrixStats::rowMins(na_x, na.rm=TRUE))
        emit("na_cols", matrixStats::rowMaxs(na_x, cols=c(2, 3, 1)))
        emit("na_cols_rm", matrixStats::rowRanges(na_x, cols=c(2, 3), na.rm=TRUE))

        int_x <- matrix(c(1L, NA_integer_, 4L, 3L, 2L, 1L, NA_integer_, 0L, 5L), nrow=3)
        emit("int_ranges", matrixStats::rowRanges(int_x))
        emit("int_mins", matrixStats::rowMins(int_x, na.rm=TRUE))
        mixed <- matrix(c(1L, NA_integer_, 2L, NA_integer_), nrow=2)
        emit("promoted", matrixStats::rowRanges(mixed, na.rm=TRUE))
        emit("promoted_max", matrixStats::rowMaxs(mixed, na.rm=TRUE))

        set.seed(1)
        big <- matrix(rnorm(40 * 25), nrow=40, ncol=25)
        writeBin(as.numeric(big), bin)
        emit("big_ranges", matrixStats::rowRanges(big, na.rm=FALSE))
        emit("big_cols", matrixStats::rowMins(big, cols=c(4, 2, 7)))
        big[2, 4] <- NA
        big[6, 1] <- NA
        emit("poison", matrixStats::rowRanges(big))
        emit("poison_cols", matrixStats::rowMins(big, cols=c(4, 1, 2), na.rm=TRUE))
        """
    )
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        program = root / "check.R"
        data = root / "big.bin"
        program.write_text(script)
        result = subprocess.run(
            ["Rscript", str(program), str(data)],
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
