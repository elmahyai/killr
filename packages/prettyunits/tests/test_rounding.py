import math

import pytest

from prettyunits.rounding import pretty_round, pretty_signif


def test_round_rejects_a_digits_vector_of_the_wrong_length():
    with pytest.raises(
        ValueError,
        match="digits must either be a scalar or the same length as x",
    ):
        pretty_round(1, [2, 3])


def test_round_scalars_and_specials():
    assert pretty_round(11) == "11"
    assert pretty_round(5) == "5"
    assert pretty_round(0.05) == "0"
    assert pretty_round(None) == "NA"
    assert pretty_round(float("nan")) == "NaN"
    assert pretty_round(float("inf")) == "Inf"
    assert pretty_round(float("-inf")) == "-Inf"


def test_round_keeps_trailing_zeros():
    assert pretty_round(0.05, 3) == "0.050"
    assert pretty_round(123.05, 3) == "123.050"
    assert pretty_round([100, 0.1], 3) == ["100.000", "0.100"]
    assert pretty_round([100, 0.1], [0, 3]) == ["100", "0.100"]
    assert pretty_round([100, 0.1], [3]) == ["100.000", "0.100"]


def test_round_mixed_missing_and_nonfinite():
    assert pretty_round([0.1, None], digits=3) == ["0.100", "NA"]
    assert pretty_round(
        [0.1, None, float("nan"), float("inf"), float("-inf")], digits=3
    ) == ["0.100", "NA", "NaN", "Inf", "-Inf"]


def test_round_zeros_negative_digits_and_scientific():
    assert pretty_round(0, digits=3) == "0.000"
    assert pretty_round([0, None], digits=3) == ["0.000", "NA"]
    assert pretty_round(-0.0004, digits=3) == "-0.000"
    assert pretty_round(123, digits=-1) == "120"
    assert pretty_round(1234567, digits=3, sci_range=5) == "1.234567000e6"
    assert (
        pretty_round(1234567, digits=3, sci_range=5, sci_sep="x10^")
        == "1.234567000x10^6"
    )
    assert pretty_round([1e7, 1e10], digits=[-3, -9], sci_range=5) == [
        "1.0000e7",
        "1.0e10",
    ]
    assert pretty_round(1e5, digits=0, sci_range=5) == "1.00000e5"
    assert pretty_round(99999, digits=0, sci_range=5) == "99999"
    assert pretty_round(5, digits=2, sci_range=0) == "5.00e0"
    assert pretty_round(0.001, digits=4, sci_range=2) == "1.0e-3"
    assert pretty_round(1234567, digits=3, sci_range=math.inf) == "1234567.000"
    assert pretty_round(0, digits=3, sci_range=0) == "0.000"


def test_round_shape_and_bool():
    assert pretty_round([]) == []
    assert pretty_round([], []) == []
    assert isinstance(pretty_round(1), str)
    assert isinstance(pretty_round([1]), list)
    with pytest.raises(ValueError, match="bool is not numeric"):
        pretty_round(True)
    with pytest.raises(ValueError, match="bool is not numeric"):
        pretty_round([1.0, False])
    with pytest.raises(ValueError, match="bool is not numeric"):
        pretty_round(1, digits=True)


def test_round_recorded_case():
    assert pretty_round(
        [123.05, 1234567, None, float("nan"), float("inf"), float("-inf")],
        digits=3,
        sci_range=5,
    ) == ["123.050", "1.234567000e6", "NA", "NaN", "Inf", "-Inf"]


def test_signif_scalars_and_specials():
    assert pretty_signif(11) == "11.0000"
    assert pretty_signif(5) == "5.00000"
    assert pretty_signif(0.05) == "0.0500000"
    assert pretty_signif(None) == "NA"
    assert pretty_signif(float("nan")) == "NaN"
    assert pretty_signif(float("inf")) == "Inf"
    assert pretty_signif(float("-inf")) == "-Inf"


def test_signif_digits_and_scientific_edges():
    assert pretty_signif(0.05, 3) == "0.0500"
    assert pretty_signif(123.05, 3) == "123"
    assert pretty_signif(123456.05, 3) == "123000"
    assert pretty_signif(123456.05, 3, sci_range=6) == "123000"
    assert pretty_signif(123456.05, 3, sci_range=5) == "1.23e5"
    assert pretty_signif(-123000.05, 3, sci_range=5) == "-1.23e5"
    assert pretty_signif(999999, 3, sci_range=6) == "1.00e6"
    assert pretty_signif(999999, 7, sci_range=6) == "999999.0"
    assert pretty_signif(-0.05, 3) == "-0.0500"
    assert pretty_signif(0.01, 3) == "0.0100"
    assert pretty_signif(1, 3) == "1.00"
    assert pretty_signif(100, 3) == "100"
    assert pretty_signif(0.9999, 2) == "1.0"
    assert pretty_signif(-0.0, digits=3) == "-0.000"


def test_signif_vectors_zeros_and_separator():
    assert pretty_signif([100, 0.1], 3) == ["100", "0.100"]
    assert pretty_signif(0.9999999, 3) == "1.00"
    assert pretty_signif([0.1, None], digits=3) == ["0.100", "NA"]
    assert pretty_signif(
        [0.1, None, float("nan"), float("inf"), float("-inf")], digits=3
    ) == ["0.100", "NA", "NaN", "Inf", "-Inf"]
    assert pretty_signif(0, digits=3) == "0.000"
    assert pretty_signif([0, None], digits=3) == ["0.000", "NA"]
    assert (
        pretty_signif(1234567, digits=3, sci_range=5, sci_sep="x10^")
        == "1.23x10^6"
    )
    assert pretty_signif([1e7, 1e10], digits=3) == ["1.00e7", "1.00e10"]
    assert pretty_signif(
        [0.001, 0.01, 0.1, 1, 10, 100, 1000], digits=3
    ) == ["0.00100", "0.0100", "0.100", "1.00", "10.0", "100", "1000"]


def test_signif_shape_bool_and_recorded_case():
    assert pretty_signif([]) == []
    assert isinstance(pretty_signif(1), str)
    assert isinstance(pretty_signif([1]), list)
    with pytest.raises(ValueError, match="bool is not numeric"):
        pretty_signif(True)
    with pytest.raises(ValueError, match="bool is not numeric"):
        pretty_signif(1, digits=True)
    assert pretty_signif(
        [0.9999999, 999999, -123000.05, None, float("nan"), float("inf")],
        digits=3,
        sci_range=5,
    ) == ["1.00", "1.00e6", "-1.23e5", "NA", "NaN", "Inf"]
