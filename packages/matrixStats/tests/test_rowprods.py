"""Checks for rowProds and colProds against the installed R package."""

from __future__ import annotations

import math
import subprocess
from pathlib import Path

import numpy as np
import pytest

from matrixstats.rowprods import colProds, rowProds

_CASE_DIR = Path("/tmp/rowprods-cases")


def test_column_major_matrix_matches_the_printed_products():
    x = np.array([[1.0, 3.0, 5.0], [2.0, 4.0, 6.0]])
    assert _equal(rowProds(x), [15.0, 48.0])
    assert _equal(colProds(x), [2.0, 12.0, 30.0])
    assert _equal(rowProds(x, method="expSumLog"), [15.0, 48.0])
    assert _equal(colProds(x, method="expSumLog"), [2.0, 12.0, 30.0])


def test_storage_order_does_not_change_the_logical_matrix():
    x = np.array([[1.0, 3.0, 5.0], [2.0, 4.0, 6.0]])
    fortran = np.asfortranarray(x)
    assert _equal(rowProds(x), rowProds(fortran))
    assert _equal(colProds(x), colProds(fortran))
    filled = np.reshape(np.arange(1, 7, dtype=float), (2, 3), order="F")
    assert _equal(rowProds(filled, dim=(2, 3)), rowProds(x))
    assert _equal(
        rowProds(np.arange(1, 7, dtype=float), dim=(2, 3)),
        rowProds(x),
    )
    assert _equal(
        colProds(np.arange(1, 7, dtype=float), dim=(2, 3)),
        colProds(x),
    )


def test_negative_zero_and_a_short_row_with_na():
    real = np.array([[-1.0, 0.0]])
    direct = rowProds(real)
    logged = rowProds(real, method="expSumLog")
    assert direct[0] == 0.0 and math.copysign(1.0, direct[0]) == -1.0
    assert logged[0] == 0.0 and math.copysign(1.0, logged[0]) == -1.0

    integer = np.array([[-1, 0]], dtype=np.int32)
    direct_i = rowProds(integer)
    logged_i = rowProds(integer, method="expSumLog")
    assert direct_i[0] == 0.0 and math.copysign(1.0, direct_i[0]) == -1.0
    assert logged_i[0] == 0.0 and math.copysign(1.0, logged_i[0]) == 1.0

    short = np.array([[0.0, -2.0, np.nan]])
    assert np.isnan(rowProds(short)[0])
    assert np.isnan(rowProds(short, method="expSumLog")[0])
    kept = rowProds(short, na_rm=True)
    kept_log = rowProds(short, na_rm=True, method="expSumLog")
    assert kept[0] == 0.0 and math.copysign(1.0, kept[0]) == -1.0
    assert kept_log[0] == 0.0 and math.copysign(1.0, kept_log[0]) == -1.0
    assert np.isnan(colProds(short)[2])
    assert colProds(short, na_rm=True)[0] == 0.0


def test_empty_product_is_one_and_an_empty_margin_skips_method():
    assert _equal(rowProds(np.zeros((3, 0))), [1.0, 1.0, 1.0])
    assert _equal(rowProds(np.zeros((3, 0)), method="expSumLog"), [1.0, 1.0, 1.0])
    assert _equal(colProds(np.zeros((0, 4))), [1.0, 1.0, 1.0, 1.0])
    assert rowProds(np.zeros((0, 3))).size == 0
    assert colProds(np.zeros((2, 0))).size == 0
    assert rowProds(np.zeros((0, 3)), method="nope").size == 0
    assert rowProds(np.zeros((0, 2)), na_rm="nope", use_names="nope").size == 0
    with pytest.raises(ValueError, match="Unknown value of argument 'method': nope"):
        colProds(np.zeros((0, 3)), method="nope")


def test_missing_values_zero_inf_and_logical():
    na = np.array([[1.0, 2.0], [np.nan, 3.0]])
    assert np.isnan(rowProds(na)[1])
    assert _equal(rowProds(na, na_rm=True), [2.0, 3.0])
    assert np.isnan(rowProds(na, method="expSumLog")[1])
    assert rowProds(np.array([[np.nan, np.nan]]), na_rm=True)[0] == 1.0
    assert rowProds(np.array([[np.nan, np.nan]]), na_rm=True, method="expSumLog")[0] == 1.0

    assert np.isnan(rowProds(np.array([[0.0, np.inf]]))[0])
    assert np.isnan(rowProds(np.array([[0.0, np.inf]]), method="expSumLog")[0])
    assert np.isnan(rowProds(np.array([[0.0, -np.inf]]))[0])
    assert math.isinf(rowProds(np.array([[1e200, 1e200]]))[0])

    logical = np.array([[True, True], [False, True]])
    assert _equal(rowProds(logical), [1.0, 0.0])
    assert _equal(colProds(logical), [0.0, 1.0])
    with pytest.raises(ValueError, match="Argument 'x' cannot be logical"):
        rowProds(logical, method="expSumLog")
    with pytest.raises(ValueError, match="Argument 'x' cannot be logical"):
        rowProds(np.zeros((2, 0), dtype=bool), method="expSumLog")
    assert rowProds(np.zeros((0, 2), dtype=bool), method="expSumLog").size == 0


def test_subscripts_follow_r_matrix_indexing():
    x = np.array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]])
    assert _equal(rowProds(x, rows=[2, 2]), [120.0, 120.0])
    assert _equal(rowProds(x, rows=[0, 2, 0]), [120.0])
    assert _equal(rowProds(x, rows=[-1]), [120.0])
    assert _equal(rowProds(x, rows=[False, True]), [120.0])
    assert rowProds(x, rows=False).size == 0
    assert rowProds(x, rows=np.array([], dtype=np.int64)).size == 0
    assert _equal(rowProds(x, rows=[1.9, 2.1]), [6.0, 120.0])
    assert rowProds(x, rows=0.5).size == 0
    assert _equal(rowProds(x, rows=[0.5, 2]), [120.0])
    assert _equal(rowProds(x, rows=-1.2), [120.0])
    assert _equal(rowProds(x, rows=[-1.9, -0.2]), [120.0])
    assert _equal(colProds(x, cols=[0, 2]), [10.0])
    assert colProds(x, cols=np.array([], dtype=np.int64)).size == 0
    assert _equal(rowProds(x, cols=np.array([], dtype=np.int64)), [1.0, 1.0])
    assert _equal(rowProds(x, rows=2, cols=[1, 3]), [24.0])
    assert _equal(colProds(x, cols=[1, 0, 1]), [4.0, 4.0])
    assert _equal(rowProds(x, rows=True), [6.0, 120.0])
    assert _equal(colProds(x, cols=[True, False]), [4.0, 18.0])

    missing = rowProds(x, rows=[np.nan, 2])
    assert np.isnan(missing[0]) and missing[1] == 120.0
    assert _equal(rowProds(x, rows=[np.nan, 2], na_rm=True), [1.0, 120.0])
    logged = rowProds(x, rows=[np.nan, 2], method="expSumLog", na_rm=True)
    assert _equal(logged, [1.0, 120.0])
    na_col = colProds(x, cols=[np.nan, 1])
    assert np.isnan(na_col[0]) and na_col[1] == 4.0

    with pytest.raises(ValueError, match="subscript out of bounds"):
        rowProds(x, rows=[1, 9])
    with pytest.raises(ValueError, match="only 0's may be mixed with negative subscripts"):
        rowProds(x, rows=[1, -2])
    with pytest.raises(ValueError, match="logical subscript too long"):
        rowProds(x, rows=[True, False, True])
    with pytest.raises(ValueError, match="idxs can only be integer, numeric, or logical"):
        rowProds(x, rows=["a"])


def test_method_must_match_the_whole_first_string():
    x = np.array([[1.0, 2.0], [3.0, 4.0]])
    with pytest.raises(ValueError, match="Unknown value of argument 'method': d"):
        rowProds(x, method="d")
    with pytest.raises(ValueError, match="Unknown value of argument 'method': exp"):
        rowProds(x, method="exp")
    with pytest.raises(ValueError, match="argument is of length zero"):
        rowProds(x, method=None)
    with pytest.raises(ValueError, match="missing value where TRUE/FALSE needed"):
        rowProds(x, method=[])
    with pytest.raises(ValueError, match="missing value where TRUE/FALSE needed"):
        rowProds(x, method=float("nan"))
    assert _equal(rowProds(x, method=["expSumLog", "direct"]), rowProds(x, method="expSumLog"))
    with pytest.raises(TypeError, match="na_rm"):
        rowProds(x, na_rm=1)
    with pytest.raises(TypeError, match="use_names"):
        rowProds(x, use_names="yes")
    with pytest.raises(ValueError, match="Argument 'x' must be a matrix or a vector"):
        rowProds(np.arange(8, dtype=float).reshape(2, 2, 2))
    with pytest.raises(ValueError, match="Argument 'dim' must be an integer vector of length two"):
        rowProds(np.array([1.0, 2.0, 3.0]))
    with pytest.raises(ValueError, match="does not match length"):
        rowProds(np.array([1.0, 2.0, 3.0]), dim=(2, 2))


def test_long_uniform_product_underflows_to_zero():
    sample = np.random.default_rng(1).uniform(0.5, 1.5, 20_000)
    direct = rowProds(sample.reshape(1, -1))
    assert direct[0] == 0.0


def test_matches_r():
    manifest = _r_cases()
    x = np.array([[1.0, 3.0, 5.0], [2.0, 4.0, 6.0]])
    byrow = np.array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]])
    neg = np.array([[1.0, 2.0], [-4.0, 3.0]])
    zero = np.array([[-1.0, 0.0], [2.0, 3.0]])
    na = np.array([[1.0, 2.0], [np.nan, 3.0]])
    nan = na.copy()
    short = np.array([[0.0, -2.0, np.nan]])
    logical = np.array([[True, True], [False, True]])
    integer = np.array([[10, 30], [20, 40]], dtype=np.int32)
    int_zero = np.array([[-1, 0]], dtype=np.int32)
    int_na = np.array([[1, 2], [np.iinfo(np.int32).min, 3]], dtype=np.int32)
    big = np.array([[1e200, 1e200], [2.0, 3.0]])
    inf = np.array([[0.0, np.inf], [1.0, 2.0]])

    expect = {
        "basic-row": rowProds(x),
        "basic-col": colProds(x),
        "basic-row-exp": rowProds(x, method="expSumLog"),
        "basic-col-exp": colProds(x, method="expSumLog"),
        "neg-row": rowProds(neg),
        "neg-row-exp": rowProds(neg, method="expSumLog"),
        "neg-col": colProds(neg),
        "neg-col-exp": colProds(neg, method="expSumLog"),
        "zero-row": rowProds(zero),
        "zero-row-exp": rowProds(zero, method="expSumLog"),
        "zero-col": colProds(zero),
        "zero-col-exp": colProds(zero, method="expSumLog"),
        "na-row": rowProds(na),
        "na-row-rm": rowProds(na, na_rm=True),
        "na-row-exp": rowProds(na, method="expSumLog"),
        "na-row-exp-rm": rowProds(na, na_rm=True, method="expSumLog"),
        "na-col": colProds(na),
        "na-col-rm": colProds(na, na_rm=True),
        "nan-row": rowProds(nan),
        "nan-row-exp": rowProds(nan, method="expSumLog"),
        "short": rowProds(short),
        "short-exp": rowProds(short, method="expSumLog"),
        "short-rm": rowProds(short, na_rm=True),
        "short-exp-rm": rowProds(short, na_rm=True, method="expSumLog"),
        "short-col": colProds(short),
        "empty-row": rowProds(np.zeros((0, 3))),
        "empty-row-col": colProds(np.zeros((0, 3))),
        "empty-col-row": rowProds(np.zeros((3, 0))),
        "empty-col": colProds(np.zeros((3, 0))),
        "allna-rm": rowProds(np.full((2, 2), np.nan), na_rm=True),
        "allna-exp-rm": rowProds(np.full((2, 2), np.nan), na_rm=True, method="expSumLog"),
        "inf-row": rowProds(inf),
        "inf-row-exp": rowProds(inf, method="expSumLog"),
        "overflow-row": rowProds(big),
        "overflow-row-exp": rowProds(big, method="expSumLog"),
        "rows-dup": rowProds(byrow, rows=[2, 2]),
        "rows-zero": rowProds(byrow, rows=[0, 2, 0]),
        "rows-neg": rowProds(byrow, rows=[-1]),
        "rows-logical": rowProds(byrow, rows=[False, True]),
        "rows-false": rowProds(byrow, rows=False),
        "rows-empty": rowProds(byrow, rows=np.array([], dtype=np.int64)),
        "rows-na": rowProds(byrow, rows=[np.nan, 2]),
        "rows-na-rm": rowProds(byrow, rows=[np.nan, 2], na_rm=True),
        "rows-na-exp": rowProds(byrow, rows=[np.nan, 2], method="expSumLog"),
        "rows-na-exp-rm": rowProds(byrow, rows=[np.nan, 2], method="expSumLog", na_rm=True),
        "rows-frac": rowProds(byrow, rows=[1.9, 2.1]),
        "rows-half": rowProds(byrow, rows=0.5),
        "rows-half-two": rowProds(byrow, rows=[0.5, 2]),
        "rows-neg-frac": rowProds(byrow, rows=-1.2),
        "cols-zero": colProds(byrow, cols=[0, 2]),
        "cols-empty": colProds(byrow, cols=np.array([], dtype=np.int64)),
        "row-empty-cols": rowProds(byrow, cols=np.array([], dtype=np.int64)),
        "both": rowProds(byrow, rows=2, cols=[1, 3]),
        "cols-na": colProds(byrow, cols=[np.nan, 1]),
        "cols-na-rm": colProds(byrow, cols=[np.nan, 1], na_rm=True),
        "cols-dup": colProds(byrow, cols=[1, 0, 1]),
        "rows-true": rowProds(byrow, rows=True),
        "cols-logical": colProds(byrow, cols=[True, False]),
        "rows-na-int": rowProds(byrow, rows=np.array([INT_MIN], dtype=np.int64)),
        "logical-row": rowProds(logical),
        "logical-col": colProds(logical),
        "int-row": rowProds(integer),
        "int-row-exp": rowProds(integer, method="expSumLog"),
        "int-zero": rowProds(int_zero),
        "int-zero-exp": rowProds(int_zero, method="expSumLog"),
        "int-na": rowProds(int_na),
        "int-na-exp": rowProds(int_na, method="expSumLog"),
        "int-na-rm": rowProds(int_na, na_rm=True),
        "int-na-exp-rm": rowProds(int_na, na_rm=True, method="expSumLog"),
        "method-swap": rowProds(byrow, method=["expSumLog", "direct"]),
        "dim-row": rowProds(np.arange(1, 7, dtype=float), dim=(2, 3)),
        "dim-col": colProds(np.arange(1, 7, dtype=float), dim=(2, 3)),
        "bad-method-empty": rowProds(np.zeros((0, 3)), method="nope"),
    }
    missing = set(manifest) - set(expect) - {"modest-x", "long-x", "modest-row", "modest-col", "modest-row-exp", "modest-col-exp", "long-direct", "long-exp"}
    assert not missing
    for name, got in expect.items():
        _close(got, _load(name), name)

    modest = np.reshape(_load("modest-x"), (80, 40), order="F")
    _close(rowProds(modest), _load("modest-row"), "modest-row")
    _close(colProds(modest), _load("modest-col"), "modest-col")
    _close(rowProds(modest, method="expSumLog"), _load("modest-row-exp"), "modest-row-exp")
    _close(colProds(modest, method="expSumLog"), _load("modest-col-exp"), "modest-col-exp")

    long = _load("long-x").reshape(1, -1)
    direct = rowProds(long)
    logged = rowProds(long, method="expSumLog")
    _close(direct, _load("long-direct"), "long-direct")
    _close(logged, _load("long-exp"), "long-exp")
    assert direct[0] == 0.0
    assert _load("long-direct")[0] == 0.0


INT_MIN = -2_147_483_648


def _equal(got, reference):
    _close(got, reference, "unit")
    return True


def _close(got, reference, name):
    got = np.asarray(got, dtype=np.float64)
    reference = np.asarray(reference, dtype=np.float64)
    assert got.shape == reference.shape, name
    assert np.array_equal(np.isnan(got), np.isnan(reference)), name
    finite = np.isfinite(got) & np.isfinite(reference)
    if np.any(finite):
        diff = np.max(np.abs(got[finite] - reference[finite]))
        assert diff <= 1e-8, (name, diff)
    other = ~np.isnan(got) & ~finite
    if np.any(other):
        assert np.array_equal(got[other], reference[other]), name
    zeros = finite & (got == 0.0) & (reference == 0.0)
    if np.any(zeros):
        assert np.array_equal(np.signbit(got[zeros]), np.signbit(reference[zeros])), name


def _load(name):
    path = _CASE_DIR / f"{name}.bin"
    data = np.fromfile(path, dtype="<f8")
    return data.copy()


def _r_cases():
    _CASE_DIR.mkdir(parents=True, exist_ok=True)
    script = r"""
    library(matrixStats)
    dir <- "/tmp/rowprods-cases"
    dump <- function(name, expr) {
      val <- as.numeric(expr)
      writeBin(val, file.path(dir, paste0(name, ".bin")))
      cat("OK ", name, " ", length(val), "\n", sep = "")
    }
    x <- matrix(c(1, 2, 3, 4, 5, 6), nrow = 2)
    dump("basic-row", rowProds(x))
    dump("basic-col", colProds(x))
    dump("basic-row-exp", rowProds(x, method = "expSumLog"))
    dump("basic-col-exp", colProds(x, method = "expSumLog"))
    neg <- matrix(c(1, -4, 2, 3), nrow = 2)
    dump("neg-row", rowProds(neg))
    dump("neg-row-exp", rowProds(neg, method = "expSumLog"))
    dump("neg-col", colProds(neg))
    dump("neg-col-exp", colProds(neg, method = "expSumLog"))
    zero <- matrix(c(-1, 2, 0, 3), nrow = 2)
    dump("zero-row", rowProds(zero))
    dump("zero-row-exp", rowProds(zero, method = "expSumLog"))
    dump("zero-col", colProds(zero))
    dump("zero-col-exp", colProds(zero, method = "expSumLog"))
    na <- matrix(c(1, NA, 2, 3), nrow = 2)
    dump("na-row", rowProds(na))
    dump("na-row-rm", rowProds(na, na.rm = TRUE))
    dump("na-row-exp", rowProds(na, method = "expSumLog"))
    dump("na-row-exp-rm", rowProds(na, method = "expSumLog", na.rm = TRUE))
    dump("na-col", colProds(na))
    dump("na-col-rm", colProds(na, na.rm = TRUE))
    nan <- matrix(c(1, NaN, 2, 3), nrow = 2)
    dump("nan-row", rowProds(nan))
    dump("nan-row-exp", rowProds(nan, method = "expSumLog"))
    short <- matrix(c(0, -2, NA), nrow = 1)
    dump("short", rowProds(short))
    dump("short-exp", rowProds(short, method = "expSumLog"))
    dump("short-rm", rowProds(short, na.rm = TRUE))
    dump("short-exp-rm", rowProds(short, method = "expSumLog", na.rm = TRUE))
    dump("short-col", colProds(short))
    dump("empty-row", rowProds(matrix(numeric(), nrow = 0, ncol = 3)))
    dump("empty-row-col", colProds(matrix(numeric(), nrow = 0, ncol = 3)))
    dump("empty-col-row", rowProds(matrix(numeric(), nrow = 3, ncol = 0)))
    dump("empty-col", colProds(matrix(numeric(), nrow = 3, ncol = 0)))
    allna <- matrix(NA_real_, nrow = 2, ncol = 2)
    dump("allna-rm", rowProds(allna, na.rm = TRUE))
    dump("allna-exp-rm", rowProds(allna, na.rm = TRUE, method = "expSumLog"))
    inf <- matrix(c(0, 1, Inf, 2), nrow = 2)
    dump("inf-row", rowProds(inf))
    dump("inf-row-exp", rowProds(inf, method = "expSumLog"))
    big <- matrix(c(1e200, 2, 1e200, 3), nrow = 2)
    dump("overflow-row", rowProds(big))
    dump("overflow-row-exp", rowProds(big, method = "expSumLog"))
    m <- matrix(1:6, nrow = 2, byrow = TRUE)
    dump("rows-dup", rowProds(m, rows = c(2, 2)))
    dump("rows-zero", rowProds(m, rows = c(0, 2, 0)))
    dump("rows-neg", rowProds(m, rows = -1))
    dump("rows-logical", rowProds(m, rows = c(FALSE, TRUE)))
    dump("rows-false", rowProds(m, rows = FALSE))
    dump("rows-empty", rowProds(m, rows = integer(0)))
    dump("rows-na", rowProds(m, rows = c(NA, 2)))
    dump("rows-na-rm", rowProds(m, rows = c(NA, 2), na.rm = TRUE))
    dump("rows-na-exp", rowProds(m, rows = c(NA, 2), method = "expSumLog"))
    dump("rows-na-exp-rm", rowProds(m, rows = c(NA, 2), method = "expSumLog", na.rm = TRUE))
    dump("rows-frac", rowProds(m, rows = c(1.9, 2.1)))
    dump("rows-half", rowProds(m, rows = 0.5))
    dump("rows-half-two", rowProds(m, rows = c(0.5, 2)))
    dump("rows-neg-frac", rowProds(m, rows = -1.2))
    dump("cols-zero", colProds(m, cols = c(0, 2)))
    dump("cols-empty", colProds(m, cols = integer(0)))
    dump("row-empty-cols", rowProds(m, cols = integer(0)))
    dump("both", rowProds(m, rows = 2, cols = c(1, 3)))
    dump("cols-na", colProds(m, cols = c(NA, 1)))
    dump("cols-na-rm", colProds(m, cols = c(NA, 1), na.rm = TRUE))
    dump("cols-dup", colProds(m, cols = c(1, 0, 1)))
    dump("rows-true", rowProds(m, rows = TRUE))
    dump("cols-logical", colProds(m, cols = c(TRUE, FALSE)))
    dump("rows-na-int", rowProds(m, rows = NA_integer_))
    logical <- matrix(c(TRUE, FALSE, TRUE, TRUE), nrow = 2)
    dump("logical-row", rowProds(logical))
    dump("logical-col", colProds(logical))
    ix <- matrix(c(10L, 20L, 30L, 40L), nrow = 2)
    dump("int-row", rowProds(ix))
    dump("int-row-exp", rowProds(ix, method = "expSumLog"))
    dump("int-zero", rowProds(matrix(c(-1L, 0L), nrow = 1)))
    dump("int-zero-exp", rowProds(matrix(c(-1L, 0L), nrow = 1), method = "expSumLog"))
    ina <- matrix(c(1L, NA_integer_, 2L, 3L), nrow = 2)
    dump("int-na", rowProds(ina))
    dump("int-na-exp", rowProds(ina, method = "expSumLog"))
    dump("int-na-rm", rowProds(ina, na.rm = TRUE))
    dump("int-na-exp-rm", rowProds(ina, method = "expSumLog", na.rm = TRUE))
    dump("method-swap", rowProds(m, method = c("expSumLog", "direct")))
    dump("dim-row", rowProds(matrix(c(1, 2, 3, 4, 5, 6), nrow = 2)))
    dump("dim-col", colProds(matrix(c(1, 2, 3, 4, 5, 6), nrow = 2)))
    dump("bad-method-empty", rowProds(matrix(numeric(), nrow = 0, ncol = 3), method = "nope"))
    set.seed(1)
    xm <- matrix(runif(80 * 40, 0.5, 1.5), nrow = 80, ncol = 40)
    writeBin(as.numeric(xm), file.path(dir, "modest-x.bin"))
    dump("modest-row", rowProds(xm))
    dump("modest-col", colProds(xm))
    dump("modest-row-exp", rowProds(xm, method = "expSumLog"))
    dump("modest-col-exp", colProds(xm, method = "expSumLog"))
    set.seed(1)
    long <- matrix(runif(20000, 0.5, 1.5), nrow = 1)
    writeBin(as.numeric(long), file.path(dir, "long-x.bin"))
    dump("long-direct", rowProds(long))
    dump("long-exp", rowProds(long, method = "expSumLog"))
    """
    completed = subprocess.run(
        ["Rscript", "-e", script],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise AssertionError(completed.stderr)
    names = []
    for line in completed.stdout.splitlines():
        parts = line.split()
        if parts and parts[0] == "OK":
            names.append(parts[1])
    names.extend(["modest-x", "long-x"])
    return set(names)
