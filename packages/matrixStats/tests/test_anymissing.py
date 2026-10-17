"""Checks for anyMissing, including a comparison with matrixStats 1.5.0."""

from __future__ import annotations

import shutil
import subprocess

import numpy as np
import pytest

from matrixstats.anymissing import NA_INTEGER, anyMissing


def test_vector_without_and_with_missing_values():
    assert anyMissing(np.array([1.0, 2.0, 3.0, 4.0])) is False
    assert anyMissing(np.array([1.0, np.nan, 3.0])) is True
    assert anyMissing(np.array([1.0, np.inf, -np.inf])) is False


def test_idxs_subset_skips_the_missing_value():
    values = np.array([1.0, np.nan, 3.0, 4.0])
    assert anyMissing(values, idxs=[1, 3, 4]) is False
    assert anyMissing(values, idxs=2) is True
    assert anyMissing(values, idxs=-2) is False


def test_list_and_data_frame():
    assert anyMissing([np.array([1.0, 2.0]), np.array([4.0, np.nan])]) is True
    assert anyMissing([np.array([1.0, 2.0]), np.array([4.0, 5.0])]) is False
    frame = {"a": np.array([1.0, np.nan]), "b": np.array([3.0, 4.0])}
    assert anyMissing(frame) is True
    assert anyMissing(frame, idxs=1) is False
    assert anyMissing(frame, idxs=2) is True
    assert anyMissing([[np.nan]]) is False


def test_integer_sentinel_and_none():
    values = np.array([1, NA_INTEGER, 3], dtype=np.int32)
    assert anyMissing(values) is True
    assert anyMissing(np.array([1, 2, 3], dtype=np.int64)) is False
    assert anyMissing([1, None, 3]) is True
    assert anyMissing([1.0, 2.0, 3.0]) is False


def test_empty_input_is_false_before_subscript_checks():
    assert anyMissing(np.array([])) is False
    assert anyMissing(np.array([], dtype=np.int32), idxs=[1, -1]) is False
    assert anyMissing([]) is False
    assert anyMissing({}) is False


def test_out_of_bounds_and_na_indexes_count_as_missing():
    assert anyMissing(np.array([1.0, 2.0, 3.0]), idxs=5) is True
    assert anyMissing(np.array([1.0, 2.0, 3.0]), idxs=None) is False
    assert anyMissing(np.array([1.0, 2.0, 3.0]), idxs=[]) is False
    assert anyMissing(np.array([10.0, np.nan, 30.0]), idxs=2.9) is True
    assert anyMissing(np.array([1.0, 2.0, 3.0]), idxs=3.2) is True
    assert anyMissing(np.array([1.0, 2.0, 3.0]), idxs=2.9) is False


def test_logical_subscripts():
    values = np.array([1.0, np.nan, 3.0, 4.0])
    assert anyMissing(values, idxs=[True, False]) is False
    assert anyMissing(np.array([1.0, 2.0]), idxs=[False, False, True]) is True
    assert anyMissing(np.array([1.0, 2.0]), idxs=[False, False, False]) is False
    assert anyMissing(values, idxs=True) is True
    assert anyMissing(values, idxs=False) is False


def test_matrix_uses_column_major_positions():
    matrix = np.array([[1.0, 3.0], [np.nan, 4.0]])
    assert anyMissing(matrix, idxs=1) is False
    assert anyMissing(matrix, idxs=2) is True


def test_complex_raw_and_character():
    assert anyMissing(np.array([1 + 0j, np.nan + 1j])) is True
    assert anyMissing(np.array([1 + 0j, 2 + 3j])) is False
    assert anyMissing(np.array([1, 2], dtype=np.uint8)) is False
    assert anyMissing(np.array(["a", None], dtype=object)) is True
    assert anyMissing(np.array(["a", "b"])) is False


def test_mixed_signs_are_rejected():
    with pytest.raises(ValueError, match="only 0's may be mixed with negative subscripts"):
        anyMissing(np.array([1.0, 2.0, 3.0]), idxs=[1, -1])


def test_matches_r_matrixstats():
    if shutil.which("Rscript") is None:
        pytest.skip("Rscript is unavailable")
    script = r"""
library(matrixStats)
show <- function(name, value) cat(name, if (isTRUE(value)) "true" else "false", "\n", sep = " ")
show("no_na", anyMissing(c(1, 2, 3, 4)))
show("has_na", anyMissing(c(1, NA, 3)))
show("nan", anyMissing(c(1, NaN)))
show("inf", anyMissing(c(1, Inf, -Inf)))
show("idxs", anyMissing(c(1, NA, 3, 4), idxs = c(1, 3, 4)))
show("idx2", anyMissing(c(1, NA, 3), idxs = 2))
show("neg", anyMissing(c(1, NA, 3), idxs = -2))
show("oob", anyMissing(c(1, 2, 3), idxs = 5))
show("frac", anyMissing(c(10, NA, 30), idxs = 2.9))
show("frac_oob", anyMissing(c(1, 2, 3), idxs = 3.2))
show("half", anyMissing(c(1, NA, 3), idxs = 0.5))
show("lgl", anyMissing(c(1, NA, 3, 4), idxs = c(TRUE, FALSE)))
show("lgl_long", anyMissing(c(1, 2), idxs = c(FALSE, FALSE, TRUE)))
show("lgl_long_f", anyMissing(c(1, 2), idxs = c(FALSE, FALSE, FALSE)))
show("listed", anyMissing(list(c(1, 2), c(4, NA))))
show("list_ok", anyMissing(list(1:3, 4:6)))
show("nested", anyMissing(list(list(NA))))
show("frame", anyMissing(data.frame(a = c(1, NA), b = c(3, 4))))
show("frame_idx", anyMissing(data.frame(a = c(1, NA), b = c(3, 4)), idxs = 1))
show("empty", anyMissing(numeric(0)))
show("empty_idx", anyMissing(numeric(0), idxs = c(1, -1)))
show("int_na", anyMissing(c(1L, NA_integer_, 3L)))
show("mat", anyMissing(matrix(c(1, NA, 3, 4), nrow = 2), idxs = 2))
show("mat1", anyMissing(matrix(c(1, NA, 3, 4), nrow = 2), idxs = 1))
show("chr", anyMissing(c("a", NA, "b")))
show("raw", anyMissing(as.raw(c(1, 2))))
show("cplx", anyMissing(c(1+1i, NA)))
"""
    completed = subprocess.run(
        ["Rscript", "-e", script],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        pytest.skip("matrixStats is unavailable")
    reference = {}
    for line in completed.stdout.splitlines():
        name, value = line.split()
        reference[name] = value == "true"
    matrix = np.array([[1.0, 3.0], [np.nan, 4.0]])
    translated = {
        "no_na": anyMissing(np.array([1.0, 2.0, 3.0, 4.0])),
        "has_na": anyMissing(np.array([1.0, np.nan, 3.0])),
        "nan": anyMissing(np.array([1.0, np.nan])),
        "inf": anyMissing(np.array([1.0, np.inf, -np.inf])),
        "idxs": anyMissing(np.array([1.0, np.nan, 3.0, 4.0]), idxs=[1, 3, 4]),
        "idx2": anyMissing(np.array([1.0, np.nan, 3.0]), idxs=2),
        "neg": anyMissing(np.array([1.0, np.nan, 3.0]), idxs=-2),
        "oob": anyMissing(np.array([1.0, 2.0, 3.0]), idxs=5),
        "frac": anyMissing(np.array([10.0, np.nan, 30.0]), idxs=2.9),
        "frac_oob": anyMissing(np.array([1.0, 2.0, 3.0]), idxs=3.2),
        "half": anyMissing(np.array([1.0, np.nan, 3.0]), idxs=0.5),
        "lgl": anyMissing(np.array([1.0, np.nan, 3.0, 4.0]), idxs=[True, False]),
        "lgl_long": anyMissing(np.array([1.0, 2.0]), idxs=[False, False, True]),
        "lgl_long_f": anyMissing(np.array([1.0, 2.0]), idxs=[False, False, False]),
        "listed": anyMissing([np.array([1.0, 2.0]), np.array([4.0, np.nan])]),
        "list_ok": anyMissing([np.array([1, 2, 3]), np.array([4, 5, 6])]),
        "nested": anyMissing([[np.nan]]),
        "frame": anyMissing({"a": np.array([1.0, np.nan]), "b": np.array([3.0, 4.0])}),
        "frame_idx": anyMissing(
            {"a": np.array([1.0, np.nan]), "b": np.array([3.0, 4.0])}, idxs=1
        ),
        "empty": anyMissing(np.array([])),
        "empty_idx": anyMissing(np.array([]), idxs=[1, -1]),
        "int_na": anyMissing(np.array([1, NA_INTEGER, 3], dtype=np.int32)),
        "mat": anyMissing(matrix, idxs=2),
        "mat1": anyMissing(matrix, idxs=1),
        "chr": anyMissing(np.array(["a", None, "b"], dtype=object)),
        "raw": anyMissing(np.array([1, 2], dtype=np.uint8)),
        "cplx": anyMissing(np.array([1 + 1j, np.nan + 0j])),
    }
    assert translated == reference
