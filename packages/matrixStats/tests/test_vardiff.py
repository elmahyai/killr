"""Checks for the matrixStats difference scale estimates against R."""

from __future__ import annotations

import math
import subprocess

import numpy as np
import pytest

from matrixstats.vardiff import (
    colIQRDiffs,
    colMadDiffs,
    colSdDiffs,
    colVarDiffs,
    iqrDiff,
    madDiff,
    rowIQRDiffs,
    rowMadDiffs,
    rowSdDiffs,
    rowVarDiffs,
    sdDiff,
    varDiff,
)

_NA = np.iinfo(np.int32).min


def test_short_vector_matches_the_scale_formulas():
    x = np.array([1.0, 3.0, 6.0, 10.0])
    assert varDiff(x) == 0.5
    assert sdDiff(x) == pytest.approx(1.0 / math.sqrt(2.0))
    assert madDiff(x) == pytest.approx(1.4826 / math.sqrt(2.0))
    assert iqrDiff(x) == pytest.approx(1.0 / math.sqrt(2.0))
    assert varDiff(x, diff=0) == pytest.approx(15.333333333333334)
    assert math.isnan(varDiff(np.array([], dtype=float)))
    assert math.isnan(sdDiff(np.array([5.0])))
    assert iqrDiff(np.array([5.0])) == 0.0
    assert madDiff(np.array([5.0]), diff=0) == 0.0
    assert math.isnan(varDiff(np.array([1.0, np.nan, 3.0])))
    assert varDiff(np.array([1.0, np.nan, 4.0, 8.0, 9.0]), na_rm=True) == pytest.approx(
        1.1666666666666667
    )
    assert math.isnan(varDiff(np.arange(1.0, 11.0), trim=0.5))


def test_integer_missing_and_argument_errors():
    assert varDiff(np.array([1, 3, 6, 10], dtype=np.int32)) == 0.5
    dirty = np.array([1, _NA, 4, 8, 9], dtype=np.int32)
    assert math.isnan(varDiff(dirty))
    assert varDiff(dirty, na_rm=True) == pytest.approx(1.1666666666666667)
    assert varDiff(np.array([True, False, True, False]), diff=0) == pytest.approx(1.0 / 3.0)
    with pytest.raises(ValueError, match="cannot be logical"):
        varDiff(np.array([True, False, True, False]))
    with pytest.raises(ValueError, match="must not be negative: -1"):
        sdDiff(np.arange(5), diff=-1)
    with pytest.raises(ValueError, match="not scalar: 2"):
        madDiff(np.arange(5), diff=[1, 2])
    with pytest.raises(ValueError, match="only 0's may be mixed"):
        iqrDiff(np.arange(5), idxs=[-1, 2])
    with pytest.raises(ValueError, match="missing value where TRUE/FALSE needed"):
        varDiff(np.arange(1, 4.0), trim=np.nan)
    assert math.isnan(varDiff(np.array([1.0, 2.0]), trim=np.nan))
    with pytest.raises(ValueError, match="NaN's not allowed"):
        iqrDiff(np.array([1.0, np.inf, np.inf, 3.0, 4.0]))
    with pytest.raises(ValueError, match="incorrect number of dimensions"):
        rowVarDiffs(np.arange(4.0))
    with pytest.raises(ValueError, match="both TRUE"):
        madDiff(np.arange(1, 5.0), diff=0, low=True, high=True)


def test_matrix_margins_follow_printed_rows():
    values = np.array([1, 5, 2, 8, 4, 1, 9, 3, 2, 6, 4, 7], dtype=float)
    matrix = values.reshape((4, 3), order="F")
    rows = rowVarDiffs(matrix)
    assert rows.tolist() == pytest.approx([6.25, 20.25, 36.0, 20.25])
    assert rowVarDiffs(
        [[1, 4, 2], [5, 1, 6], [2, 9, 4], [8, 3, 7]]
    ).tolist() == pytest.approx(rows.tolist())
    assert rowVarDiffs(matrix, rows=[1, 3]).tolist() == pytest.approx([6.25, 36.0])
    assert colVarDiffs(matrix, cols=[3, 1]).shape == (2,)
    assert math.isnan(rowVarDiffs(np.zeros((1, 1)))[0])
    assert rowIQRDiffs(np.zeros((1, 1)))[0] == 0.0
    assert rowVarDiffs(np.zeros((0, 3))).shape == (0,)
    assert colVarDiffs(np.zeros((0, 3))).shape == (3,)
    assert np.isnan(rowVarDiffs(np.zeros((2, 0)))).all()
    assert colSdDiffs(np.zeros((2, 0))).shape == (0,)
    assert rowMadDiffs(np.zeros((0, 0)), trim=np.nan).shape == (0,)
    with pytest.raises(ValueError, match="missing value where TRUE/FALSE needed"):
        rowVarDiffs(np.zeros((0, 3)), trim=np.nan)
    with pytest.raises(ValueError, match="missing value where TRUE/FALSE needed"):
        colVarDiffs(matrix, use_names=np.nan)


def test_matches_r_on_subsets_trim_and_margins():
    rng = np.random.default_rng(1)
    z = rng.standard_normal(80)
    matrix = z[:48].reshape((6, 8), order="F").copy()
    matrix[1, 2] = np.nan
    matrix[4, 6] = np.inf
    reference = _r_battery(z, matrix)
    got = {
        "var": varDiff(z),
        "sd": sdDiff(z),
        "mad": madDiff(z),
        "iqr": iqrDiff(z),
        "var19": varDiff(z, diff=1.9),
        "sd2": sdDiff(z, diff=2),
        "mad2": madDiff(z, diff=2, constant=1),
        "iqr0": iqrDiff(z, diff=0),
        "trim": varDiff(z, trim=0.1),
        "trimMad": madDiff(z, trim=0.2),
        "trimIqr": iqrDiff(z, trim=0.15, type=4),
        "idxs": varDiff(z, idxs=[1, 2, 4, 8, 15, 16, 40]),
        "neg": sdDiff(z, idxs=[-1.2, -5, 0]),
        "oob": iqrDiff(z, idxs=[1, 200, np.nan]),
        "logical": varDiff(z, idxs=[True, False, False]),
        "row": rowVarDiffs(matrix),
        "col": colSdDiffs(matrix),
        "rowMad": rowMadDiffs(matrix, na_rm=True),
        "colIqr": colIQRDiffs(matrix, na_rm=True, type=5),
        "rowNa": rowIQRDiffs(matrix),
        "sub": rowVarDiffs(matrix, rows=[1, 1, 6], cols=[8, 1, 2, 2]),
        "drop": colMadDiffs(matrix, rows=[-2, -5], cols=[True, False]),
        "low": madDiff(z, diff=0, low=True),
        "high": madDiff(z, diff=0, high=True),
        "center": madDiff(z, diff=0, center=0),
        "intNa": sdDiff(np.array([1, _NA, 4, 9, 16, 25], dtype=np.int32), na_rm=True),
        "wide0": rowMadDiffs(np.zeros((2, 0))),
        "emptyRow": rowSdDiffs(np.zeros((0, 4))),
    }
    for name, value in got.items():
        _assert_close(np.atleast_1d(np.asarray(value, dtype=float)), reference[name], name)


def _assert_close(got, expected, name):
    assert got.shape == expected.shape, name
    assert np.array_equal(np.isnan(got), np.isnan(expected)), name
    finite = np.isfinite(got) & np.isfinite(expected)
    if np.any(finite):
        diff = np.max(np.abs(got[finite] - expected[finite]))
        assert diff <= 1e-8, (name, diff)
    nonfinite = ~np.isnan(got) & ~finite
    if np.any(nonfinite):
        assert np.array_equal(got[nonfinite], expected[nonfinite]), name


def _r_battery(z, matrix):
    payload = np.concatenate(
        [
            np.ascontiguousarray(z, dtype="<f8"),
            np.asfortranarray(matrix, dtype="<f8").ravel(order="F"),
        ]
    )
    script = r"""
    library(matrixStats)
    input <- file("stdin", "rb")
    z <- readBin(input, "double", 80)
    m <- matrix(readBin(input, "double", 48), nrow = 6, ncol = 8)
    close(input)
    storage <- list(
      var = varDiff(z),
      sd = sdDiff(z),
      mad = madDiff(z),
      iqr = iqrDiff(z),
      var19 = varDiff(z, diff = 1.9),
      sd2 = sdDiff(z, diff = 2),
      mad2 = madDiff(z, diff = 2, constant = 1),
      iqr0 = iqrDiff(z, diff = 0),
      trim = varDiff(z, trim = 0.1),
      trimMad = madDiff(z, trim = 0.2),
      trimIqr = iqrDiff(z, trim = 0.15, type = 4),
      idxs = varDiff(z, idxs = c(1, 2, 4, 8, 15, 16, 40)),
      neg = sdDiff(z, idxs = c(-1.2, -5, 0)),
      oob = iqrDiff(z, idxs = c(1, 200, NA)),
      logical = varDiff(z, idxs = c(TRUE, FALSE, FALSE)),
      row = rowVarDiffs(m),
      col = colSdDiffs(m),
      rowMad = rowMadDiffs(m, na.rm = TRUE),
      colIqr = colIQRDiffs(m, na.rm = TRUE, type = 5),
      rowNa = rowIQRDiffs(m),
      sub = rowVarDiffs(m, rows = c(1, 1, 6), cols = c(8, 1, 2, 2)),
      drop = colMadDiffs(m, rows = -c(2, 5), cols = c(TRUE, FALSE)),
      low = madDiff(z, diff = 0, low = TRUE),
      high = madDiff(z, diff = 0, high = TRUE),
      center = madDiff(z, diff = 0, center = 0),
      intNa = sdDiff(c(1L, NA, 4L, 9L, 16L, 25L), na.rm = TRUE),
      wide0 = rowMadDiffs(matrix(numeric(0), 2, 0)),
      emptyRow = rowSdDiffs(matrix(numeric(0), 0, 4))
    )
    for (nm in names(storage)) {
      val <- storage[[nm]]
      cat(nm, " ", length(val), "\n", sep = "")
      if (!length(val)) {
        cat("\n")
      } else {
        shown <- ifelse(is.na(val), "NA", sprintf("%.17g", val))
        cat(paste(shown, collapse = " "), "\n", sep = "")
      }
    }
    """
    result = subprocess.run(
        ["Rscript", "-e", script],
        input=payload.tobytes(),
        check=False,
        capture_output=True,
    )
    if result.returncode != 0:
        raise AssertionError(result.stderr.decode())
    lines = result.stdout.decode().splitlines()
    parsed = {}
    index = 0
    while index < len(lines):
        name, count = lines[index].split()
        count = int(count)
        index += 1
        body = lines[index] if index < len(lines) else ""
        index += 1
        if count == 0:
            parsed[name] = np.array([], dtype=float)
            continue
        values = [np.nan if part == "NA" else float(part) for part in body.split()]
        parsed[name] = np.asarray(values, dtype=float)
    return parsed
