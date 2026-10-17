"""Checks for rowMedians and colMedians, including one comparison with R."""

from __future__ import annotations

import shutil
import subprocess
import textwrap

import numpy as np
import pytest

from matrixstats.rowmedians import colMedians, rowMedians

TOL = 1e-8
NA_INTEGER = np.iinfo(np.int32).min
NA_REAL_BITS = np.uint64(0x7FF00000000007A2)
PLAIN_NAN_BITS = np.uint64(0x7FF8000000000000)
NEG_NAN_BITS = np.uint64(0xFFF8000000000000)


def test_printed_integer_matrix():
    printed = np.arange(1, 13, dtype=np.int32).reshape((4, 3), order="F")
    rows = rowMedians(printed)
    cols = colMedians(printed)
    assert rows.dtype == np.float64
    assert cols.dtype == np.float64
    assert rows.tolist() == [5.0, 6.0, 7.0, 8.0]
    assert cols.tolist() == [2.5, 6.5, 10.5]
    vector = rowMedians(np.arange(1, 13), dim=(4, 3))
    assert vector.tolist() == rows.tolist()
    assert colMedians(np.asfortranarray(printed)).tolist() == cols.tolist()
    assert rowMedians(np.array(printed, order="C")).tolist() == rows.tolist()


def test_even_integer_average_and_duplicates():
    wide = np.array([[2_147_483_646, 2_147_483_647]], dtype=np.int32)
    assert rowMedians(wide).tolist() == [2_147_483_646.5]
    assert rowMedians(np.array([[1.0, 2.0, 2.0, 9.0]])).tolist() == [2.0]
    assert rowMedians(np.array([[1.0, 100.0, 2.0, 200.0]])).tolist() == [51.0]
    assert colMedians(np.array([[1.0, 5.0], [9.0, 7.0]])).tolist() == [5.0, 6.0]


def test_nan_becomes_na_real_and_empty_is_plain_nan():
    stopped = rowMedians(np.array([[1.0, np.nan, 3.0]]))
    assert stopped.view(np.uint64)[0] == NA_REAL_BITS
    assert rowMedians(np.array([[1.0, np.nan, 3.0]]), na_rm=True).tolist() == [2.0]
    empty = rowMedians(np.array([[np.nan, np.nan]]), na_rm=True)
    assert empty.view(np.uint64)[0] == PLAIN_NAN_BITS
    no_cols = rowMedians(np.zeros((2, 0)))
    assert no_cols.shape == (2,)
    assert np.all(no_cols.view(np.uint64) == PLAIN_NAN_BITS)
    no_rows = colMedians(np.zeros((0, 3)))
    assert no_rows.shape == (3,)
    assert np.all(no_rows.view(np.uint64) == PLAIN_NAN_BITS)
    assert rowMedians(np.zeros((0, 3))).shape == (0,)
    assert colMedians(np.zeros((2, 0))).shape == (0,)


def test_opposite_infinities_and_integer_na():
    infs = rowMedians(np.array([[-np.inf, np.inf]]))
    assert infs.view(np.uint64)[0] == NEG_NAN_BITS
    ints = np.array([[1, 4], [NA_INTEGER, 2]], dtype=np.int32)
    kept_na = rowMedians(ints)
    assert kept_na[0] == 2.5
    assert kept_na.view(np.uint64)[1] == NA_REAL_BITS
    assert rowMedians(ints, na_rm=True).tolist() == [2.5, 2.0]
    only = rowMedians(np.array([[NA_INTEGER]], dtype=np.int32), na_rm=True)
    assert only.view(np.uint64)[0] == PLAIN_NAN_BITS


def test_subscripts_follow_r():
    printed = np.arange(1, 13, dtype=np.int32).reshape((4, 3), order="F")
    assert rowMedians(printed, cols=[0, 2]).tolist() == [5.0, 6.0, 7.0, 8.0]
    assert rowMedians(printed, cols=[-2]).tolist() == [5.0, 6.0, 7.0, 8.0]
    assert rowMedians(printed, rows=[3, 0, 1]).tolist() == [7.0, 5.0]
    assert rowMedians(printed, rows=[False, True]).tolist() == [6.0, 8.0]
    assert rowMedians(printed, rows=1.9).tolist() == [5.0]
    assert colMedians(printed, rows=[1, 4], cols=[3, 1]).tolist() == [10.5, 2.5]
    assert rowMedians(printed, rows=[]).shape == (0,)
    dropped = rowMedians(printed, cols=[1, None], na_rm=True)
    assert dropped.tolist() == [1.0, 2.0, 3.0, 4.0]
    na_col = rowMedians(printed, cols=[1, None])
    assert np.all(na_col.view(np.uint64) == NA_REAL_BITS)


def test_rejects_bad_input():
    printed = np.arange(1, 13, dtype=np.int32).reshape((4, 3), order="F")
    with pytest.raises(ValueError, match="cannot be logical"):
        rowMedians(np.array([[True, False]]))
    with pytest.raises(ValueError, match="dim."):
        rowMedians(np.arange(12), dim=(2, 3))
    with pytest.raises(ValueError, match="TRUE or FALSE"):
        colMedians(printed, na_rm=2)
    with pytest.raises(ValueError, match="must be a logical"):
        rowMedians(printed, use_names=1.5)
    with pytest.raises(ValueError, match="subscript out of bounds"):
        rowMedians(printed, rows=[5])
    with pytest.raises(ValueError, match="negative subscripts"):
        colMedians(printed, cols=[-1.0, 1.0])
    with pytest.raises(ValueError, match="logical subscript too long"):
        rowMedians(printed, rows=[True, False, True, False, True])
    assert rowMedians(printed, na_rm=0).tolist() == [5.0, 6.0, 7.0, 8.0]
    assert rowMedians(printed, rows=True).tolist() == [5.0, 6.0, 7.0, 8.0]
    assert colMedians(printed, cols=False).shape == (0,)


def test_matches_r_on_the_seeded_matrix_and_the_small_matrix():
    if shutil.which("Rscript") is None:
        pytest.skip("Rscript is unavailable")
    reference = _r_reference()
    if reference is None:
        pytest.skip("matrixStats is unavailable")

    small = np.arange(1, 13).reshape((4, 3), order="F")
    _assert_match(rowMedians(small), reference["small_row"])
    _assert_match(colMedians(small), reference["small_col"])
    _assert_match(rowMedians(reference["matrix"]), reference["big_row"])
    _assert_match(colMedians(reference["matrix"]), reference["big_col"])
    _assert_match(
        rowMedians(reference["matrix"], cols=[4, 2, 7]),
        reference["big_cols"],
    )
    _assert_match(
        colMedians(reference["matrix"], rows=[3, 1, 9]),
        reference["big_rows"],
    )

    poisoned = np.array(reference["matrix"], order="C", copy=True)
    poisoned.view(np.uint64)[1, 3] = NA_REAL_BITS
    poisoned.view(np.uint64)[5, 0] = NA_REAL_BITS
    _assert_match(rowMedians(poisoned), reference["poison_row"])
    _assert_match(colMedians(poisoned, na_rm=True), reference["poison_col"])

    ints = np.array([[1, 4], [NA_INTEGER, 2]], dtype=np.int32)
    _assert_match(rowMedians(ints), reference["int_row"])
    _assert_match(colMedians(ints, na_rm=True), reference["int_col"])
    _assert_match(rowMedians(np.array([[-np.inf, np.inf]])), reference["infs"])


def _assert_match(actual, expected):
    actual = np.asarray(actual, dtype=np.float64).reshape(-1)
    expected = np.asarray(expected, dtype=np.float64).reshape(-1)
    assert actual.shape == expected.shape
    finite = np.isfinite(actual) & np.isfinite(expected)
    if finite.any():
        diff = np.max(np.abs(actual[finite] - expected[finite]))
        assert diff <= TOL
    actual_bits = actual.view(np.uint64)
    expected_bits = expected.view(np.uint64)
    assert np.array_equal(actual_bits[~finite], expected_bits[~finite])


def _r_reference():
    script = textwrap.dedent(
        r"""
        args <- commandArgs(trailingOnly=TRUE)
        out <- args[[1]]
        if (!requireNamespace("matrixStats", quietly=TRUE)) quit(status=2)
        save <- function(name, values) {
          writeBin(as.double(values), file.path(out, paste0(name, ".bin")))
        }
        small <- matrix(1:12, nrow=4)
        save("small_row", matrixStats::rowMedians(small))
        save("small_col", matrixStats::colMedians(small))
        set.seed(1)
        big <- matrix(rnorm(400 * 250), nrow=400, ncol=250)
        writeBin(as.numeric(big), file.path(out, "matrix.bin"))
        save("big_row", matrixStats::rowMedians(big))
        save("big_col", matrixStats::colMedians(big))
        save("big_cols", matrixStats::rowMedians(big, cols=c(4, 2, 7)))
        save("big_rows", matrixStats::colMedians(big, rows=c(3, 1, 9)))
        big[2, 4] <- NA
        big[6, 1] <- NA
        save("poison_row", matrixStats::rowMedians(big))
        save("poison_col", matrixStats::colMedians(big, na.rm=TRUE))
        ints <- matrix(c(1L, NA_integer_, 4L, 2L), nrow=2)
        save("int_row", matrixStats::rowMedians(ints))
        save("int_col", matrixStats::colMedians(ints, na.rm=TRUE))
        save("infs", matrixStats::rowMedians(matrix(c(-Inf, Inf), nrow=1)))
        """
    )
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        program = root / "check.R"
        program.write_text(script)
        result = subprocess.run(
            ["Rscript", str(program), str(root)],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode == 2:
            return None
        if result.returncode != 0:
            raise RuntimeError(result.stderr)
        parsed = {}
        matrix = np.fromfile(root / "matrix.bin", dtype="<f8").reshape((400, 250), order="F")
        parsed["matrix"] = np.array(matrix, order="C", copy=True)
        for path in root.glob("*.bin"):
            if path.name == "matrix.bin":
                continue
            parsed[path.stem] = np.fromfile(path, dtype="<f8")
        return parsed
