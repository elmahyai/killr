"""Checks for allocMatrix, allocVector, and allocArray against installed R."""

from __future__ import annotations

import shutil
import subprocess
import textwrap
import warnings

import numpy as np
import pytest

from matrixstats.alloc import allocArray, allocMatrix, allocVector

_NA = -2_147_483_648
_DTYPE = {
    "double": np.dtype(np.float64),
    "integer": np.dtype(np.int32),
    "logical": np.dtype(np.int32),
}


def test_default_matrix_is_double_and_shaped_by_row():
    matrix = allocMatrix(5, 3)
    assert matrix.shape == (5, 3)
    assert matrix.dtype == np.float64
    assert np.all(matrix == 0.0)
    assert not np.signbit(matrix[0, 0])


def test_python_int_is_integer_storage_and_float_is_double():
    # R's bare 0 is double. Python's bare 0 is an int, so it follows 0L.
    assert allocMatrix(2, 2, 0).dtype == np.int32
    assert np.all(allocMatrix(2, 2, 0) == 0)
    assert allocMatrix(2, 2, 0.0).dtype == np.float64
    assert allocVector(4, 7).dtype == np.int32
    assert allocVector(4, 7).tolist() == [7, 7, 7, 7]
    assert allocVector(4).dtype == np.float64


def test_logical_storage_and_missing_values():
    truth = allocMatrix(2, 2, True)
    assert truth.dtype == np.int32
    assert truth.tolist() == [[1, 1], [1, 1]]
    assert allocMatrix(2, 2, False).tolist() == [[0, 0], [0, 0]]
    missing = allocArray((2, 2, 2), None)
    assert missing.shape == (2, 2, 2)
    assert missing.dtype == np.int32
    assert np.all(missing == _NA)
    integer_na = allocVector(3, _NA)
    assert integer_na.dtype == np.int32
    assert integer_na.tolist() == [_NA, _NA, _NA]
    double_na = allocMatrix(2, 3, np.nan)
    assert double_na.shape == (2, 3)
    assert np.all(np.isnan(double_na))


def test_negative_zero_is_positive_zero():
    matrix = allocMatrix(1, 2, -0.0)
    assert matrix.dtype == np.float64
    assert np.all(matrix == 0.0)
    assert not np.any(np.signbit(matrix))


def test_dim_alias_and_ignored_extra_arguments():
    via_dim = allocArray(dim=(2, 3), value=True)
    via_alias = allocArray(dim_=(2, 3), value=True)
    assert via_dim.shape == via_alias.shape == (2, 3)
    assert via_dim.tolist() == via_alias.tolist() == [[1, 1, 1], [1, 1, 1]]
    assert allocMatrix(2, 2, 1.5, 9, extra=4).tolist() == [[1.5, 1.5], [1.5, 1.5]]
    with pytest.raises(TypeError, match="dim"):
        allocArray(value=1.0)


def test_empty_shapes_and_truncation():
    assert allocMatrix(0, 3, 1.0).shape == (0, 3)
    assert allocMatrix(3, 0, 1).shape == (3, 0)
    assert allocMatrix(3, 0, 1).dtype == np.int32
    assert allocVector(5.9, 1.0).shape == (5,)
    assert allocVector(-0.1, 1.0).shape == (0,)
    assert allocArray([2.9, 3.2], 4).shape == (2, 3)
    assert allocArray([2.9, 3.2], 4).dtype == np.int32
    assert allocArray(5, True).shape == (5,)
    assert allocArray([2, 0, 3], 1.0).shape == (2, 0, 3)


def test_dimension_errors_do_not_allocate_a_huge_product():
    with pytest.raises(ValueError, match="negative extents to matrix"):
        allocMatrix(2, -3, "a")
    with pytest.raises(ValueError, match="nrow' is negative"):
        allocMatrix(-2, -3, "a")
    with pytest.raises(ValueError, match="must be a scalar"):
        allocMatrix(2, -3, [1.0, 2.0])
    with pytest.raises(ValueError, match="negative length vectors are not allowed"):
        allocArray(-1, "a")
    with pytest.raises(ValueError, match="must be a scalar"):
        allocArray(-1, [1.0, 2.0])
    with pytest.raises(ValueError, match="integer, numeric or logical"):
        allocArray([-2, -3], "a")
    with pytest.raises(ValueError, match="negative values"):
        allocArray([-1, -1, -1, -1], 1.0)
    with pytest.raises(ValueError, match="missing values"):
        allocArray([None, -1], 1.0)
    with pytest.raises(ValueError, match="missing values"):
        allocArray([0, None], 1.0)
    with pytest.raises(ValueError, match="vector is too large"):
        allocMatrix(2_147_483_647, 2_147_483_647, "a")
    with pytest.raises(ValueError, match="vector is too large"):
        allocArray([None, None], 1.0)
    with pytest.raises(ValueError, match="length' is negative"):
        allocVector(-1, "a")
    with pytest.raises(ValueError, match="vector is too large"):
        allocVector(2**53, "a")
    with pytest.raises(ValueError, match="must be a scalar"):
        allocVector(2**53, [1.0, 2.0])


def test_coercion_warnings():
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        assert allocMatrix(1.9, 2.9, 1.0).shape == (1, 2)
    with pytest.warns(UserWarning, match="coercion to integer range"):
        with pytest.raises(ValueError, match="nrow' is negative"):
            allocMatrix(np.inf, 2, 1.0)
    with pytest.warns(UserWarning, match=r"^NAs introduced by coercion$"):
        with pytest.raises(ValueError, match="nrow' is negative"):
            allocMatrix("a", 2, 1.0)


def test_matches_installed_r():
    if shutil.which("Rscript") is None:
        pytest.skip("Rscript is unavailable")
    script = textwrap.dedent(
        r"""
        options(warn = -1)
        library(matrixStats)
        token <- function(x) {
          if (is.double(x)) {
            if (is.na(x)) return("NaN")
            if (is.infinite(x)) return(if (x > 0) "Inf" else "-Inf")
            if (x == 0 && sign(1/x) < 0) return("-0")
            return(sprintf("%.17g", x))
          }
          if (is.logical(x)) {
            if (is.na(x)) return("NA")
            return(if (isTRUE(x)) "1" else "0")
          }
          if (is.integer(x)) {
            if (is.na(x)) return("NA")
            return(sprintf("%d", x))
          }
          "OTHER"
        }
        report <- function(name, expr) {
          value <- tryCatch(
            withCallingHandlers(expr, warning = function(w) invokeRestart("muffleWarning")),
            error = function(e) structure(conditionMessage(e), class = "err")
          )
          if (inherits(value, "err")) {
            cat(paste(name, "error", value, sep = "\t"), "\n", sep = "")
            return(invisible())
          }
          dims <- if (is.null(dim(value))) {
            paste0("v", length(value))
          } else {
            paste(dim(value), collapse = "x")
          }
          flat <- as.vector(value)
          encoded <- if (length(flat) == 0) "" else paste(vapply(flat, token, ""), collapse = " ")
          cat(paste(name, "ok", typeof(value), dims, encoded, sep = "\t"), "\n", sep = "")
        }
        report("m_default", allocMatrix(5, 3))
        report("m_double", allocMatrix(2, 3, 1.5))
        report("m_int", allocMatrix(2, 3, 7L))
        report("m_zero_int", allocMatrix(2, 2, 0L))
        report("m_zero_double", allocMatrix(2, 2, 0))
        report("m_true", allocMatrix(2, 2, TRUE))
        report("m_false", allocMatrix(2, 2, FALSE))
        report("m_na", allocMatrix(2, 2, NA))
        report("m_na_int", allocMatrix(2, 2, NA_integer_))
        report("m_na_real", allocMatrix(2, 2, NA_real_))
        report("m_nan", allocMatrix(2, 2, NaN))
        report("m_inf", allocMatrix(1, 2, Inf))
        report("m_ninf", allocMatrix(1, 2, -Inf))
        report("m_neg_zero", allocMatrix(1, 2, -0))
        report("m_empty_rows", allocMatrix(0, 3, 1))
        report("m_empty_cols", allocMatrix(3, 0, 1L))
        report("m_empty_both", allocMatrix(0, 0, TRUE))
        report("m_frac", allocMatrix(1.9, 2.9, 1))
        report("m_bool_dim", allocMatrix(TRUE, FALSE, 1L))
        report("m_extra", allocMatrix(2, 2, 1, foo = 3))
        report("m_char_dim", allocMatrix("2", "3", 1L))
        report("m_scalar_matrix", allocMatrix(2, 2, matrix(7L)))
        report("m_neg_nrow", allocMatrix(-1, 3, 1))
        report("m_neg_ncol", allocMatrix(2, -3, 1))
        report("m_both_neg", allocMatrix(-2, -3, 1))
        report("m_na_nrow", allocMatrix(NA, 3, 1))
        report("m_na_ncol", allocMatrix(2, NA, 1))
        report("m_vec_nrow", allocMatrix(c(2, 3), 1, 1))
        report("m_vec_value", allocMatrix(2, 2, c(1, 2)))
        report("m_char_value", allocMatrix(2, 2, "a"))
        report("m_null_value", allocMatrix(2, 2, NULL))
        report("m_complex", allocMatrix(2, 2, 1+0i))
        report("m_empty_value", allocMatrix(2, 2, numeric(0)))
        report("m_neg_ncol_char", allocMatrix(2, -1, "a"))
        report("m_neg_ncol_vec", allocMatrix(2, -1, c(1, 2)))
        report("m_huge", allocMatrix(2147483647, 2147483647, 0))
        report("v_default", allocVector(5))
        report("v_int", allocVector(4, 3L))
        report("v_false", allocVector(3, FALSE))
        report("v_na", allocVector(3, NA))
        report("v_na_int", allocVector(3, NA_integer_))
        report("v_na_real", allocVector(3, NA_real_))
        report("v_frac", allocVector(5.9, 1))
        report("v_neg_frac", allocVector(-0.1, 1))
        report("v_zero", allocVector(0, 1L))
        report("v_neg", allocVector(-3, 1))
        report("v_na_len", allocVector(NA, 1))
        report("v_inf", allocVector(Inf, 1))
        report("v_two", allocVector(c(2, 3), 1))
        report("v_true_len", allocVector(TRUE, 8L))
        report("v_char_len", allocVector("4", 1L))
        report("v_bad_char", allocVector("a", 1))
        report("v_null", allocVector(NULL, 1))
        report("v_neg_zero", allocVector(2, -0))
        report("v_char_value", allocVector(2, "a"))
        report("v_neg_char", allocVector(-1, "a"))
        report("v_too_big", allocVector(2^53, 0))
        report("v_1e20", allocVector(1e20, 0))
        report("a_2d", allocArray(c(2, 3), 1.5))
        report("a_3d", allocArray(c(2, 3, 4), 9L))
        report("a_1d", allocArray(5, TRUE))
        report("a_zero", allocArray(c(2, 0, 3), 1))
        report("a_neg", allocArray(c(2, -3), 1))
        report("a_two_neg", allocArray(c(-2, -3), 1))
        report("a_na", allocArray(c(2, NA), 1))
        report("a_empty", allocArray(integer(0), 1))
        report("a_null", allocArray(NULL, 1))
        report("a_frac", allocArray(c(2.9, 3.2), 4L))
        report("a_na_value", allocArray(c(2, 2, 2), NA))
        report("a_scalar", allocArray(4, 0))
        report("a_four_neg", allocArray(c(-1, -1, -1, -1), 1))
        report("a_one_neg", allocArray(-5, 1))
        report("a_zero_one", allocArray(0, 1L))
        report("a_char_dim", allocArray(c("2", "3"), 1))
        report("a_bool_dim", allocArray(c(TRUE, FALSE, TRUE), 1L))
        report("a_char_value", allocArray(c(2, 2), "a"))
        report("a_neg_char", allocArray(-1, "a"))
        report("a_two_neg_char", allocArray(c(-2, -3), "a"))
        report("a_neg_vec", allocArray(-1, c(1, 2)))
        report("a_na_zero", allocArray(c(0, NA), 1))
        report("a_two_na", allocArray(c(NA, NA), 1))
        report("a_huge", allocArray(c(2147483647, 2147483647), 0))
        report("a_neg_zero_dim", allocArray(c(2, -0), 1))
        """
    )
    completed = subprocess.run(
        ["Rscript", "--vanilla", "-"],
        input=script,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    expected = {}
    for line in completed.stdout.splitlines():
        name, status, payload = line.split("\t", 2)
        expected[name] = (status, payload)

    calls = {name: fn for name, fn in _PYTHON_CASES}
    assert set(calls) == set(expected)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        for name, fn in _PYTHON_CASES:
            status, payload = expected[name]
            if status == "error":
                with pytest.raises(ValueError, match=_message_pattern(payload)) as caught:
                    fn()
                assert str(caught.value) == payload
                continue
            mode, dims, encoded = payload.split("\t", 2)
            array = fn()
            assert array.dtype == _DTYPE[mode], name
            assert _dims(array, name) == dims, name
            assert _tokens(array) == encoded, name


def _dims(array: np.ndarray, name: str) -> str:
    if name.startswith("v_"):
        return f"v{array.size}"
    if array.ndim == 1 and name.startswith("a_") and "x" not in _shape_text(array):
        return _shape_text(array)
    return _shape_text(array)


def _shape_text(array: np.ndarray) -> str:
    return "x".join(str(extent) for extent in array.shape)


def _tokens(array: np.ndarray) -> str:
    flat = np.ravel(array)
    if flat.size == 0:
        return ""
    if array.dtype == np.float64:
        return " ".join(_token_float(value) for value in flat)
    return " ".join("NA" if int(value) == _NA else str(int(value)) for value in flat)


def _token_float(value: float) -> str:
    number = float(value)
    if math_isnan(number):
        return "NaN"
    if math_isinf(number):
        return "Inf" if number > 0 else "-Inf"
    if number == 0.0 and np.signbit(number):
        return "-0"
    text = format(number, ".17g")
    return text


def math_isnan(value: float) -> bool:
    return value != value


def math_isinf(value: float) -> bool:
    return value == float("inf") or value == float("-inf")


def _message_pattern(message: str) -> str:
    return "^" + __import__("re").escape(message) + "$"


_PYTHON_CASES = [
    ("m_default", lambda: allocMatrix(5, 3)),
    ("m_double", lambda: allocMatrix(2, 3, 1.5)),
    ("m_int", lambda: allocMatrix(2, 3, 7)),
    ("m_zero_int", lambda: allocMatrix(2, 2, 0)),
    ("m_zero_double", lambda: allocMatrix(2, 2, 0.0)),
    ("m_true", lambda: allocMatrix(2, 2, True)),
    ("m_false", lambda: allocMatrix(2, 2, False)),
    ("m_na", lambda: allocMatrix(2, 2, None)),
    ("m_na_int", lambda: allocMatrix(2, 2, _NA)),
    ("m_na_real", lambda: allocMatrix(2, 2, np.nan)),
    ("m_nan", lambda: allocMatrix(2, 2, np.nan)),
    ("m_inf", lambda: allocMatrix(1, 2, np.inf)),
    ("m_ninf", lambda: allocMatrix(1, 2, -np.inf)),
    ("m_neg_zero", lambda: allocMatrix(1, 2, -0.0)),
    ("m_empty_rows", lambda: allocMatrix(0, 3, 1.0)),
    ("m_empty_cols", lambda: allocMatrix(3, 0, 1)),
    ("m_empty_both", lambda: allocMatrix(0, 0, True)),
    ("m_frac", lambda: allocMatrix(1.9, 2.9, 1.0)),
    ("m_bool_dim", lambda: allocMatrix(True, False, 1)),
    ("m_extra", lambda: allocMatrix(2, 2, 1.0, foo=3)),
    ("m_char_dim", lambda: allocMatrix("2", "3", 1)),
    ("m_scalar_matrix", lambda: allocMatrix(2, 2, np.array([[7]], dtype=np.int32))),
    ("m_neg_nrow", lambda: allocMatrix(-1, 3, 1.0)),
    ("m_neg_ncol", lambda: allocMatrix(2, -3, 1.0)),
    ("m_both_neg", lambda: allocMatrix(-2, -3, 1.0)),
    ("m_na_nrow", lambda: allocMatrix(_NA, 3, 1.0)),
    ("m_na_ncol", lambda: allocMatrix(2, _NA, 1.0)),
    ("m_vec_nrow", lambda: allocMatrix([2, 3], 1, 1.0)),
    ("m_vec_value", lambda: allocMatrix(2, 2, [1.0, 2.0])),
    ("m_char_value", lambda: allocMatrix(2, 2, "a")),
    ("m_null_value", lambda: allocMatrix(2, 2, [])),
    ("m_complex", lambda: allocMatrix(2, 2, 1j)),
    ("m_empty_value", lambda: allocMatrix(2, 2, np.array([], dtype=np.float64))),
    ("m_neg_ncol_char", lambda: allocMatrix(2, -1, "a")),
    ("m_neg_ncol_vec", lambda: allocMatrix(2, -1, [1.0, 2.0])),
    ("m_huge", lambda: allocMatrix(2_147_483_647, 2_147_483_647, 0.0)),
    ("v_default", lambda: allocVector(5)),
    ("v_int", lambda: allocVector(4, 3)),
    ("v_false", lambda: allocVector(3, False)),
    ("v_na", lambda: allocVector(3, None)),
    ("v_na_int", lambda: allocVector(3, _NA)),
    ("v_na_real", lambda: allocVector(3, np.nan)),
    ("v_frac", lambda: allocVector(5.9, 1.0)),
    ("v_neg_frac", lambda: allocVector(-0.1, 1.0)),
    ("v_zero", lambda: allocVector(0, 1)),
    ("v_neg", lambda: allocVector(-3, 1.0)),
    ("v_na_len", lambda: allocVector(np.nan, 1.0)),
    ("v_inf", lambda: allocVector(np.inf, 1.0)),
    ("v_two", lambda: allocVector([2, 3], 1.0)),
    ("v_true_len", lambda: allocVector(True, 8)),
    ("v_char_len", lambda: allocVector("4", 1)),
    ("v_bad_char", lambda: allocVector("a", 1.0)),
    ("v_null", lambda: allocVector(None, 1.0)),
    ("v_neg_zero", lambda: allocVector(2, -0.0)),
    ("v_char_value", lambda: allocVector(2, "a")),
    ("v_neg_char", lambda: allocVector(-1, "a")),
    ("v_too_big", lambda: allocVector(2**53, 0.0)),
    ("v_1e20", lambda: allocVector(1e20, 0.0)),
    ("a_2d", lambda: allocArray([2, 3], 1.5)),
    ("a_3d", lambda: allocArray([2, 3, 4], 9)),
    ("a_1d", lambda: allocArray(5, True)),
    ("a_zero", lambda: allocArray([2, 0, 3], 1.0)),
    ("a_neg", lambda: allocArray([2, -3], 1.0)),
    ("a_two_neg", lambda: allocArray([-2, -3], 1.0)),
    ("a_na", lambda: allocArray([2, None], 1.0)),
    ("a_empty", lambda: allocArray([], 1.0)),
    ("a_null", lambda: allocArray(None, 1.0)),
    ("a_frac", lambda: allocArray([2.9, 3.2], 4)),
    ("a_na_value", lambda: allocArray([2, 2, 2], None)),
    ("a_scalar", lambda: allocArray(4, 0.0)),
    ("a_four_neg", lambda: allocArray([-1, -1, -1, -1], 1.0)),
    ("a_one_neg", lambda: allocArray(-5, 1.0)),
    ("a_zero_one", lambda: allocArray(0, 1)),
    ("a_char_dim", lambda: allocArray(["2", "3"], 1.0)),
    ("a_bool_dim", lambda: allocArray([True, False, True], 1)),
    ("a_char_value", lambda: allocArray([2, 2], "a")),
    ("a_neg_char", lambda: allocArray(-1, "a")),
    ("a_two_neg_char", lambda: allocArray([-2, -3], "a")),
    ("a_neg_vec", lambda: allocArray(-1, [1.0, 2.0])),
    ("a_na_zero", lambda: allocArray([0, None], 1.0)),
    ("a_two_na", lambda: allocArray([None, None], 1.0)),
    ("a_huge", lambda: allocArray([2_147_483_647, 2_147_483_647], 0.0)),
    ("a_neg_zero_dim", lambda: allocArray([2, -0.0], 1.0)),
]
