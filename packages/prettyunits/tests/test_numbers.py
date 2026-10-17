"""Behavioral cases from prettyunits tests/testthat/test-numbers.r."""

import math

import pytest

from prettyunits.numbers import compute_num, pretty_num


def test_pretty_num_rejects_non_numeric():
    for bad in ("", "1", True, False, ["x"], [True]):
        with pytest.raises(ValueError, match=r"is\.numeric\(number\) is not TRUE"):
            pretty_num(bad)
        with pytest.raises(ValueError, match=r"is\.numeric\(number\) is not TRUE"):
            compute_num(bad)


def test_pretty_num_converts_scalars():
    assert pretty_num(1e-24) == "1 y"
    assert pretty_num(-1e-4) == "-100.00 u"
    assert pretty_num(-0.01) == "-10 m"
    assert pretty_num(0) == "0 "
    assert pretty_num(10) == "10 "
    assert pretty_num(999) == "999 "
    assert pretty_num(1001) == "1.00 k"
    assert pretty_num(1000 * 1000 - 1) == "1.00 M"
    assert pretty_num(1e16) == "10 P"
    assert pretty_num(1e30) == "1000000 Y"
    assert isinstance(pretty_num(0), str)


def test_pretty_num_handles_na_and_nan():
    assert pretty_num(None) == "NA "
    assert pretty_num(float("nan")) == "NaN "


def test_pretty_num_handles_vectors():
    assert pretty_num(list(range(1, 11))) == [f"{n:2d} " for n in range(1, 11)]
    values = [None, -1e-7, 1, 1e4, 1e6, float("nan"), 1e5]
    assert pretty_num(values) == [
        "      NA ",
        "-100.00 n",
        "       1 ",
        "     10 k",
        "      1 M",
        "     NaN ",
        "    100 k",
    ]
    assert pretty_num([]) == []
    assert pretty_num([1]) == ["1 "]


def test_pretty_num_nopad_style():
    values = [None, 1, 1e4, 1e6, float("nan"), 1e5]
    assert pretty_num(values, style="nopad") == [
        "NA ",
        "1 ",
        "10 k",
        "1 M",
        "NaN ",
        "100 k",
    ]
    assert pretty_num([], style="nopad") == []


def test_pretty_num_handles_negative_values():
    values = [None, -1, 1e4, 1e6, float("nan"), -1e5]
    assert pretty_num(values) == [
        "   NA ",
        "   -1 ",
        "  10 k",
        "   1 M",
        "  NaN ",
        "-100 k",
    ]


def test_always_two_fraction_digits():
    assert pretty_num([5.6 * 1000 * 1000, 5 * 1000 * 1000, None]) == [
        "5.60 M",
        "   5 M",
        "   NA ",
    ]


def test_six_width_style():
    cases = [
        (" -10 k", -1e4),
        ("-111  ", -111.33333),
        ("-100  ", -100),
        (" -10  ", -10.33333),
        (" -10  ", -9.99999),
        ("-9.0  ", -9),
        ("-1.0  ", -1),
        ("0.00  ", 0),
        ("1.00  ", 1),
        ("9.00  ", 9),
        ("10.0  ", 9.99999),
        ("10.3  ", 10.33333),
        (" 100  ", 100),
        (" 111  ", 111.33333),
        ("1.00 k", 1e3),
        ("1.05 k", 1049),
        ("1.05 k", 1051),
        ("1.10 k", 1100),
        ("10.0 k", 1e4),
        (" 100 k", 1e5),
        ("1.00 M", 1e6),
        (" NaN  ", float("nan")),
        ("  NA  ", None),
    ]
    assert pretty_num([value for _, value in cases], style="6") == [
        name for name, _ in cases
    ]


def test_no_fractional_bytes():
    cases = [
        ("    -1 ", -1),
        ("     1 ", 1),
        ("    16 ", 16),
        ("   128 ", 128),
        (" 1.02 k", 1024),
        ("16.38 k", 16384),
        (" 1.05 M", 1048576),
        ("-1.05 M", -1048576),
        ("    NA ", None),
    ]
    assert pretty_num([value for _, value in cases]) == [name for name, _ in cases]


def test_compute_num_smallest_prefix():
    got = compute_num(1e-24, smallest_prefix="m")
    assert got.prefix == ["m"]
    assert got.negative == [False]
    assert abs(got.amount[0] - 1e-21) < 1e-8

    got = compute_num(-1e-4, smallest_prefix="m")
    assert got.prefix == ["m"]
    assert got.negative == [True]
    assert abs(got.amount[0] - 0.1) < 1e-8

    got = compute_num(-0.01, smallest_prefix="m")
    assert got.amount == [10]
    assert got.prefix == ["m"]
    assert got.negative == [True]

    got = compute_num(0, smallest_prefix="m")
    assert got.amount == [0]
    assert got.prefix == [""]
    assert got.negative == [False]
    assert isinstance(got.amount, list)
    assert isinstance(got.prefix, list)
    assert isinstance(got.negative, list)


def test_compute_num_check_vector():
    got = compute_num([1e-24, -1e-4, -0.01, 0, None, float("nan")])
    assert got.prefix == ["y", "u", "m", "", "", ""]
    assert got.negative == [False, True, True, False, False, False]
    assert got.amount[0] == 1
    assert got.amount[1] == 100.00000000000001
    assert got.amount[2] == 10
    assert got.amount[3] == 0
    assert got.amount[4] is None
    assert math.isnan(got.amount[5])
