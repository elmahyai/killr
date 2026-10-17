"""Checks for rowVars and colVars, including a comparison with R."""

from __future__ import annotations

import subprocess
import textwrap

import numpy as np
import pytest
import rowvars as _rowvars

from matrixstats.rowvars import colVars, rowVars

TOL = 1e-8
NA_INTEGER = np.iinfo(np.int32).min
NA_REAL_BITS = np.uint64(0x7FF00000000007A2)


def test_printed_integer_matrix():
    printed = _printed_1_to_12()
    rows = rowVars(printed)
    cols = colVars(printed)
    assert rows.dtype == np.float64
    assert rows.tolist() == [16.0, 16.0, 16.0, 16.0]
    assert np.allclose(cols, [5.0 / 3.0, 5.0 / 3.0, 5.0 / 3.0])
    assert rowVars(np.arange(1, 13), dim=(4, 3)).tolist() == rows.tolist()
    assert colVars(np.array(printed, dtype=float)).tolist() == cols.tolist()
    assert rowVars(printed, refine=False).tolist() == rows.tolist()
    assert rowVars(printed, na_rm=0).tolist() == rows.tolist()
    assert rowVars(printed, rows=1).tolist() == [16.0]


def test_missing_values_subsets_and_short_margins():
    printed = _printed_1_to_12().astype(np.float64)
    printed[0, 1] = np.nan
    stopped = rowVars(printed)
    assert stopped[0].view(np.uint64) == NA_REAL_BITS
    assert stopped[1:].tolist() == [16.0, 16.0, 16.0]
    assert rowVars(printed, na_rm=True)[0] == 32.0

    na = np.array(np.uint64(NA_REAL_BITS).view(np.float64))
    real_na = printed.copy()
    real_na[0, 1] = na
    assert rowVars(real_na)[0].view(np.uint64) == NA_REAL_BITS

    ints = _printed_1_to_12()
    ints[0, 1] = NA_INTEGER
    assert rowVars(ints)[0].view(np.uint64) == NA_REAL_BITS
    assert rowVars(ints, na_rm=True)[0] == 32.0

    one_col = rowVars(printed[:, :1])
    assert one_col.shape == (4,)
    assert np.all(one_col.view(np.uint64) == NA_REAL_BITS)
    assert rowVars(np.zeros((2, 0))).shape == (2,)
    assert np.all(rowVars(np.zeros((2, 0))).view(np.uint64) == NA_REAL_BITS)
    assert colVars(np.zeros((0, 3))).shape == (3,)
    assert rowVars(np.zeros((0, 3))).shape == (0,)

    base = _printed_1_to_12()
    assert rowVars(base, cols=[1, 1, 2]).tolist() == pytest.approx([16.0 / 3.0] * 4)
    assert rowVars(base, cols=[0, 2]).shape == (4,)
    assert np.all(np.isnan(rowVars(base, cols=[0, 2])))
    dropped = rowVars(base, cols=[-1])
    assert dropped.shape == (4,)
    assert rowVars(base, rows=[2, 0, 4]).tolist() == [16.0, 16.0]
    assert rowVars(base, rows=[]).shape == (0,)
    assert colVars(base, rows=[False, True]).shape == (3,)


def test_center_matches_the_mean_and_rejects_a_scalar():
    _rowvars.reset_formula_check_py()
    printed = _printed_1_to_12().astype(np.float64)
    center = printed.mean(axis=1)
    assert rowVars(printed, center=center).tolist() == [16.0, 16.0, 16.0, 16.0]
    with pytest.raises(ValueError, match="scalar value is defunct"):
        rowVars(printed, center=1.0)
    with pytest.raises(ValueError, match="2 != 4"):
        rowVars(printed, center=[1.0, 2.0])
    with pytest.raises(ValueError, match="incorrect use of argument 'center'"):
        _rowvars.reset_formula_check_py()
        rowVars(printed, center=np.ones(4))
    _rowvars.reset_formula_check_py()
    with pytest.raises(ValueError, match="colVars\\(\\) or colSds\\(\\)"):
        colVars(printed, center=np.ones(3))
    # The check already ran, so a later incorrect center is the primary formula.
    biased = rowVars(printed, center=np.ones(4))
    assert biased[0] == pytest.approx(40.0)
    assert rowVars(printed[:, :1], center=np.array([9.0, 9.0, 9.0, 9.0])).view(np.uint64).tolist() == [
        int(NA_REAL_BITS)
    ] * 4


def test_rejects_logical_bad_flags_and_subscripts():
    with pytest.raises(ValueError, match="cannot be logical"):
        rowVars(np.array([[True, False], [False, True]]))
    with pytest.raises(ValueError, match="dim."):
        rowVars(np.arange(4.0), dim=(2, 3))
    with pytest.raises(ValueError, match="TRUE or FALSE"):
        rowVars(_printed_1_to_12(), na_rm=2)
    with pytest.raises(ValueError, match="must be a logical"):
        colVars(_printed_1_to_12(), refine=1.5)
    with pytest.raises(ValueError, match="subscript out of bounds"):
        rowVars(_printed_1_to_12(), rows=[5])
    with pytest.raises(ValueError, match="negative subscripts"):
        colVars(_printed_1_to_12(), cols=[-1.0, 1.0])
    with pytest.raises(ValueError, match="logical subscript too long"):
        rowVars(_printed_1_to_12(), rows=[True, False, True, False, True])
    with pytest.raises(ValueError, match="character"):
        rowVars(np.array([["a", "b"], ["c", "d"]]))
    with pytest.raises(ValueError, match="non-numeric argument"):
        rowVars(_printed_1_to_12(), center=["a", "b", "c", "d"])


def test_matches_r_on_types_center_and_subsets():
    if subprocess.call(["Rscript", "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) != 0:
        pytest.skip("Rscript is unavailable")
    reference = _r_suite()
    if reference is None:
        pytest.skip("matrixStats is unavailable")

    printed = _printed_1_to_12()
    _assert_match(rowVars(printed), reference["row_int"])
    _assert_match(colVars(printed), reference["col_int"])
    _assert_match(rowVars(np.arange(1, 13), dim=(4, 3)), reference["vector"])
    _assert_match(colVars(np.arange(1, 13), dim=(4, 3)), reference["col_vector"])
    _assert_match(rowVars(printed, cols=[3, 1]), reference["cols"])
    _assert_match(rowVars(printed, cols=[1, 1, 2]), reference["repeat"])
    _assert_match(rowVars(printed, cols=[-1]), reference["neg"])
    _assert_match(rowVars(printed, rows=[2, 0, 4]), reference["rows"])
    _assert_match(colVars(printed, rows=1.9), reference["frac"])

    poisoned = printed.astype(np.float64)
    poisoned.view(np.uint64)[0, 1] = NA_REAL_BITS
    _assert_match(rowVars(poisoned), reference["na_row"])
    _assert_match(rowVars(poisoned, na_rm=True), reference["na_row_rm"])
    _assert_match(colVars(poisoned, na_rm=True), reference["na_col_rm"])
    ints = printed.copy()
    ints[0, 1] = NA_INTEGER
    _assert_match(rowVars(ints, na_rm=True), reference["int_na"])

    _assert_match(rowVars(reference["matrix"], na_rm=False, refine=True), reference["big"])
    _assert_match(colVars(reference["matrix"], na_rm=False, refine=True), reference["big_col"])
    _assert_match(rowVars(reference["matrix"], refine=False), reference["big_norefine"])
    _assert_match(rowVars(reference["offset_x"], refine=True), reference["offset"])
    _assert_match(rowVars(reference["offset_x"], refine=False), reference["offset_off"])
    _assert_match(
        rowVars(reference["matrix"], center=reference["center_row"][1].reshape(-1)),
        reference["center_row_var"],
    )
    _assert_match(
        colVars(reference["matrix"], center=reference["center_col"][1].reshape(-1)),
        reference["center_col_var"],
    )
    partial = reference["matrix"].copy()
    partial[1, 4] = np.nan
    _assert_match(rowVars(partial, na_rm=True), reference["partial"])


def _printed_1_to_12():
    return np.arange(1, 13, dtype=np.int32).reshape((4, 3), order="F")


def _assert_match(actual, expected):
    actual = np.asarray(actual, dtype=np.float64)
    _kind, values = expected
    values = np.asarray(values, dtype=np.float64).reshape(actual.shape, order="F")
    assert actual.shape == values.shape
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
        args <- commandArgs(trailingOnly=TRUE)
        bin <- args[[1]]
        off <- args[[2]]
        if (!requireNamespace("matrixStats", quietly=TRUE)) quit(status=2)
        emit <- function(name, values) {
          mat <- as.matrix(as.double(values))
          cat(name, "\n", "double", "\n", nrow(mat), " ", ncol(mat), "\n", sep="")
          raw <- writeBin(as.double(as.vector(mat)), raw())
          if (length(raw)) cat(sprintf("%02x", as.integer(raw)), sep="\n")
          cat("---\n")
        }
        x <- matrix(1:12, nrow=4)
        emit("row_int", matrixStats::rowVars(x))
        emit("col_int", matrixStats::colVars(x))
        emit("vector", matrixStats::rowVars(1:12, dim.=c(4, 3)))
        emit("col_vector", matrixStats::colVars(1:12, dim.=c(4, 3)))
        emit("cols", matrixStats::rowVars(x, cols=c(3, 1)))
        emit("repeat", matrixStats::rowVars(x, cols=c(1, 1, 2)))
        emit("neg", matrixStats::rowVars(x, cols=-1))
        emit("rows", matrixStats::rowVars(x, rows=c(2, 0, 4)))
        emit("frac", matrixStats::colVars(x, rows=1.9))

        na_x <- matrix(as.double(x), nrow=4)
        na_x[1, 2] <- NA_real_
        emit("na_row", matrixStats::rowVars(na_x))
        emit("na_row_rm", matrixStats::rowVars(na_x, na.rm=TRUE))
        emit("na_col_rm", matrixStats::colVars(na_x, na.rm=TRUE))
        int_x <- x
        int_x[1, 2] <- NA_integer_
        emit("int_na", matrixStats::rowVars(int_x, na.rm=TRUE))

        set.seed(1)
        big <- matrix(rnorm(40 * 25), nrow=40, ncol=25)
        writeBin(as.numeric(big), bin)
        emit("big", matrixStats::rowVars(big, na.rm=FALSE, refine=TRUE))
        emit("big_col", matrixStats::colVars(big, na.rm=FALSE, refine=TRUE))
        emit("big_norefine", matrixStats::rowVars(big, refine=FALSE))
        emit("center_row", rowMeans(big))
        emit("center_col", colMeans(big))
        emit("center_row_var", matrixStats::rowVars(big, center=rowMeans(big)))
        emit("center_col_var", matrixStats::colVars(big, center=colMeans(big)))
        partial <- big
        partial[2, 5] <- NA_real_
        emit("partial", matrixStats::rowVars(partial, na.rm=TRUE))

        offset <- matrix(1e8 + c(0, 1, -1, 2, -2), nrow=1)
        writeBin(as.numeric(offset), off)
        emit("offset", matrixStats::rowVars(offset, refine=TRUE))
        emit("offset_off", matrixStats::rowVars(offset, refine=FALSE))
        """
    )
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        program = root / "check.R"
        data = root / "big.bin"
        offset = root / "offset.bin"
        program.write_text(script)
        result = subprocess.run(
            ["Rscript", str(program), str(data), str(offset)],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode == 2:
            return None
        if result.returncode != 0:
            raise RuntimeError(result.stderr)
        parsed = _parse_blocks(result.stdout)
        parsed["matrix"] = np.fromfile(data, dtype="<f8").reshape((40, 25), order="F")
        parsed["offset_x"] = np.fromfile(offset, dtype="<f8").reshape((1, 5), order="F")
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
        raw = bytes(int(line, 16) for line in body)
        values = np.frombuffer(raw, dtype="<f8").reshape((nrow, ncol), order="F")
        parsed[name] = (kind, np.array(values, copy=True))
    return parsed
