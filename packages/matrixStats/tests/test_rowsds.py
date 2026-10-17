"""Checks for rowSds and colSds, including a comparison with R."""

from __future__ import annotations

import subprocess
import textwrap

import numpy as np
import pytest

from matrixstats.rowsds import colSds, rowSds

TOL = 1e-8
NA_REAL_BITS = np.uint64(0x7FF00000000007A2)


def test_integer_matrix_is_the_square_root_of_the_variance():
    printed = np.arange(1, 13, dtype=np.int32).reshape((4, 3), order="F")
    rows = rowSds(printed)
    cols = colSds(printed)
    assert rows.tolist() == [4.0, 4.0, 4.0, 4.0]
    assert cols.tolist() == pytest.approx([np.sqrt(5.0 / 3.0)] * 3)
    assert rowSds(np.arange(1, 13), dim=(4, 3)).tolist() == rows.tolist()


def test_square_root_keeps_r_na_bits():
    printed = np.arange(1, 13, dtype=np.float64).reshape((4, 3), order="F")
    printed[0, 1] = np.array(NA_REAL_BITS).view(np.float64)
    stopped = rowSds(printed)
    assert stopped[0].view(np.uint64) == NA_REAL_BITS
    assert stopped[1] == pytest.approx(4.0)
    empty = colSds(printed[:1, :])
    assert empty.shape == (3,)
    assert np.all(empty.view(np.uint64) == NA_REAL_BITS)


def test_matches_r():
    if subprocess.call(["Rscript", "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) != 0:
        pytest.skip("Rscript is unavailable")
    script = textwrap.dedent(
        r"""
        args <- commandArgs(trailingOnly=TRUE)
        bin <- args[[1]]
        if (!requireNamespace("matrixStats", quietly=TRUE)) quit(status=2)
        emit <- function(name, values) {
          mat <- as.matrix(as.double(values))
          cat(name, "\n", nrow(mat), " ", ncol(mat), "\n", sep="")
          raw <- writeBin(as.double(as.vector(mat)), raw())
          if (length(raw)) cat(sprintf("%02x", as.integer(raw)), sep="\n")
          cat("---\n")
        }
        x <- matrix(1:12, nrow=4)
        emit("row", matrixStats::rowSds(x))
        emit("col", matrixStats::colSds(x))
        na_x <- matrix(as.double(x), nrow=4)
        na_x[1, 2] <- NA_real_
        emit("na", matrixStats::rowSds(na_x))
        emit("na_rm", matrixStats::colSds(na_x, na.rm=TRUE))
        set.seed(1)
        big <- matrix(rnorm(40 * 25), nrow=40, ncol=25)
        writeBin(as.numeric(big), bin)
        emit("big", matrixStats::rowSds(big, na.rm=FALSE, refine=TRUE))
        emit("big_col", matrixStats::colSds(big, na.rm=FALSE, refine=TRUE))
        emit("center_mu", rowMeans(big))
        emit("center", matrixStats::rowSds(big, center=rowMeans(big)))
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
            pytest.skip("matrixStats is unavailable")
        if result.returncode != 0:
            raise RuntimeError(result.stderr)
        parsed = _parse_blocks(result.stdout)
        matrix = np.fromfile(data, dtype="<f8").reshape((40, 25), order="F")

    printed = np.arange(1, 13, dtype=np.int32).reshape((4, 3), order="F")
    _assert_match(rowSds(printed), parsed["row"])
    _assert_match(colSds(printed), parsed["col"])
    poisoned = printed.astype(np.float64)
    poisoned.view(np.uint64)[0, 1] = NA_REAL_BITS
    _assert_match(rowSds(poisoned), parsed["na"])
    _assert_match(colSds(poisoned, na_rm=True), parsed["na_rm"])
    _assert_match(rowSds(matrix, na_rm=False, refine=True), parsed["big"])
    _assert_match(colSds(matrix, na_rm=False, refine=True), parsed["big_col"])
    center = parsed["center_mu"][1].reshape(-1)
    _assert_match(rowSds(matrix, center=center), parsed["center"])


def _assert_match(actual, expected):
    actual = np.asarray(actual, dtype=np.float64)
    _nrow, values = expected
    values = np.asarray(values, dtype=np.float64).reshape(actual.shape)
    actual_f = actual.reshape(-1)
    expected_f = values.reshape(-1)
    actual_b = actual.reshape(-1).view(np.uint64)
    expected_b = values.reshape(-1).view(np.uint64)
    for got, want, got_bits, want_bits in zip(actual_f, expected_f, actual_b, expected_b):
        if not np.isfinite(want) or not np.isfinite(got):
            assert int(got_bits) == int(want_bits)
        else:
            assert abs(float(got) - float(want)) <= TOL


def _parse_blocks(text: str):
    parsed = {}
    chunks = text.split("---\n")
    for chunk in chunks:
        lines = [line for line in chunk.splitlines() if line != ""]
        if not lines:
            continue
        name = lines[0]
        nrow, ncol = (int(part) for part in lines[1].split())
        body = lines[2:]
        raw = bytes(int(line, 16) for line in body)
        values = np.frombuffer(raw, dtype="<f8").copy().reshape((nrow, ncol), order="F")
        parsed[name] = (nrow, values.reshape(-1))
    return parsed
