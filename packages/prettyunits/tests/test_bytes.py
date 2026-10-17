"""Expectations from prettyunits tests/testthat/test-bytes.r."""

import math

import pytest

from prettyunits.bytes import compute_bytes, pretty_bytes


def test_pretty_bytes_gives_errors_on_invalid_input():
    with pytest.raises(ValueError, match=r"is\.numeric.*is not TRUE"):
        pretty_bytes("")
    with pytest.raises(ValueError, match=r"is\.numeric.*is not TRUE"):
        pretty_bytes("1")
    with pytest.raises(ValueError, match=r"is\.numeric.*is not TRUE"):
        pretty_bytes(True)
    # R's list(1, 2, 3) is not an atomic vector. A Python list is that vector.
    with pytest.raises(ValueError, match=r"is\.numeric.*is not TRUE"):
        pretty_bytes([[1, 2, 3]])


def test_pretty_bytes_converts_properly():
    assert pretty_bytes(0) == "0 B"
    assert pretty_bytes(10) == "10 B"
    assert pretty_bytes(999) == "999 B"
    assert pretty_bytes(1001) == "1.00 kB"
    assert pretty_bytes(1000 * 1000 - 1) == "1.00 MB"
    assert pretty_bytes(1e16) == "10 PB"
    assert pretty_bytes(1e30) == "1000000 YB"
    assert isinstance(pretty_bytes(0), str)


def test_pretty_bytes_handles_na_and_nan():
    assert pretty_bytes(None) == "NA B"
    assert pretty_bytes(float("nan")) == "NaN B"
    with pytest.raises(ValueError, match=r"is\.numeric.*is not TRUE"):
        pretty_bytes("NA")
    with pytest.raises(ValueError, match=r"is\.numeric.*is not TRUE"):
        pretty_bytes(False)


def test_pretty_bytes_handles_vectors():
    assert pretty_bytes(list(range(1, 11))) == [
        " 1 B",
        " 2 B",
        " 3 B",
        " 4 B",
        " 5 B",
        " 6 B",
        " 7 B",
        " 8 B",
        " 9 B",
        "10 B",
    ]
    values = [None, 1, 1e4, 1e6, float("nan"), 1e5]
    assert pretty_bytes(values) == [
        "  NA B",
        "   1 B",
        " 10 kB",
        "  1 MB",
        " NaN B",
        "100 kB",
    ]
    assert pretty_bytes([]) == []
    assert pretty_bytes([1, 2, 3]) == ["1 B", "2 B", "3 B"]


def test_pretty_bytes_nopad_style():
    values = [None, 1, 1e4, 1e6, float("nan"), 1e5]
    assert pretty_bytes(values, style="nopad") == [
        "NA B",
        "1 B",
        "10 kB",
        "1 MB",
        "NaN B",
        "100 kB",
    ]
    assert pretty_bytes(values, style="n") == pretty_bytes(values, style="nopad")
    assert pretty_bytes(10, style="d") == "10 B"
    assert pretty_bytes([], style="nopad") == []


def test_pretty_bytes_handles_negative_values():
    values = [None, -1, 1e4, 1e6, float("nan"), -1e5]
    assert pretty_bytes(values) == [
        "   NA B",
        "   -1 B",
        "  10 kB",
        "   1 MB",
        "  NaN B",
        "-100 kB",
    ]


def test_always_two_fraction_digits():
    assert pretty_bytes([5.6 * 1000 * 1000, 5 * 1000 * 1000, None]) == [
        "5.60 MB",
        "   5 MB",
        "   NA B",
    ]


def test_6_width_style():
    cases = [
        (-1e4, "< 0 kB"),
        (-100, "< 0 kB"),
        (-1, "< 0 kB"),
        (0, "0.0 kB"),
        (1, "0.0 kB"),
        (9, "0.0 kB"),
        (9.99999, "0.0 kB"),
        (10.33333, "0.0 kB"),
        (100, "0.1 kB"),
        (111.33333, "0.1 kB"),
        (1e3, "1.0 kB"),
        (1049, "1.0 kB"),
        (1051, "1.1 kB"),
        (1100, "1.1 kB"),
        (1e4, " 10 kB"),
        (1e5, "100 kB"),
        (1e6, "1.0 MB"),
        (float("nan"), "NaN kB"),
        (None, " NA kB"),
    ]
    assert pretty_bytes([value for value, _label in cases], style="6") == [
        label for _value, label in cases
    ]


def test_no_fractional_bytes():
    cases = [
        (-1, "    -1 B"),
        (1, "     1 B"),
        (16, "    16 B"),
        (128, "   128 B"),
        (1024, " 1.02 kB"),
        (16384, "16.38 kB"),
        (1048576, " 1.05 MB"),
        (-1048576, "-1.05 MB"),
        (None, "    NA B"),
    ]
    assert pretty_bytes([value for value, _label in cases]) == [
        label for _value, label in cases
    ]


def test_compute_bytes_check_vector_and_edges():
    values = [None, -1, 1e4, 1e6, float("nan"), -1e5]
    result = compute_bytes(values)
    assert result.amount[0] is None
    assert result.amount[1] == 1
    assert result.amount[2] == 10
    assert result.amount[3] == 1
    assert math.isnan(result.amount[4])
    assert result.amount[5] == 100
    assert result.unit == ["B", "B", "kB", "MB", "B", "kB"]
    assert result.negative == [False, True, False, False, False, True]

    empty = compute_bytes([])
    assert empty.amount == []
    assert empty.unit == []
    assert empty.negative == []

    zero = compute_bytes(0)
    assert zero.amount == [0]
    assert zero.unit == ["B"]
    assert zero.negative == [False]

    yotta = compute_bytes([0, 10, -10, None, float("nan"), 1e30], smallest_unit="YB")
    assert yotta.amount[0] == 0
    assert yotta.unit[0] == "YB"
    assert yotta.negative == [False, False, True, False, False, False]
    assert yotta.amount[1] is None and yotta.unit[1] is None
    assert yotta.amount[2] is None and yotta.unit[2] is None
    assert yotta.amount[3] is None and yotta.unit[3] == "YB"
    assert math.isnan(yotta.amount[4]) and yotta.unit[4] == "YB"
    assert yotta.amount[5] is None and yotta.unit[5] is None
