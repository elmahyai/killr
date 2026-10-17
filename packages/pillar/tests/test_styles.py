"""pillar styles against the installed 1.11.1 behaviour at 8 colors."""

import math

import pytest

from cli._options import options as cli_options
from pillar._options import options as pillar_options
from pillar.styles import (
    AsIs,
    format_type_sum,
    style_bold,
    style_na,
    style_neg,
    style_subtle,
    style_subtle_num,
)

GREY_OPEN = "\x1b[90m"
GREY_CLOSE = "\x1b[39m"
RED_OPEN = "\x1b[31m"
RED_CLOSE = "\x1b[39m"
BOLD_OPEN = "\x1b[1m"
BOLD_CLOSE = "\x1b[22m"
ITALIC_OPEN = "\x1b[3m"
ITALIC_CLOSE = "\x1b[23m"


def _grey(text: str) -> str:
    return GREY_OPEN + text + GREY_CLOSE


def _red(text: str) -> str:
    return RED_OPEN + text + RED_CLOSE


def _bold(text: str) -> str:
    return BOLD_OPEN + text + BOLD_CLOSE


def _type_label(text: str) -> str:
    return ITALIC_OPEN + _grey(text) + ITALIC_CLOSE


@pytest.fixture(autouse=True)
def _defaults():
    cli_options(**{"cli.num_colors": 8})
    pillar_options(
        **{
            "pillar.subtle": True,
            "pillar.subtle_num": False,
            "pillar.bold": False,
            "pillar.neg": True,
        }
    )
    yield
    cli_options(**{"cli.num_colors": 8})
    pillar_options(
        **{
            "pillar.subtle": True,
            "pillar.subtle_num": False,
            "pillar.bold": False,
            "pillar.neg": True,
        }
    )


def test_style_subtle_greys_text_and_keeps_blanks():
    assert style_subtle("text") == _grey("text")
    assert style_subtle(["a", "", None]) == [_grey("a"), "", _grey("NA")]
    assert isinstance(style_subtle("text"), str)
    assert isinstance(style_subtle(["a"]), list)
    assert style_subtle([]) == []


def test_style_subtle_off_is_plain_and_keeps_missing():
    pillar_options(**{"pillar.subtle": False})
    assert style_subtle("text") == "text"
    assert style_subtle(["a", "", None]) == ["a", "", None]
    assert style_subtle([0.01, None, 1]) == ["0.01", None, "1"]
    assert style_subtle(None) is None


def test_option_must_be_true():
    pillar_options(**{"pillar.subtle": 1})
    assert style_subtle("text") == "text"
    pillar_options(**{"pillar.bold": "TRUE"})
    assert style_bold("A") == "A"


def test_style_bold_follows_the_option():
    assert style_bold("Petal.Width") == "Petal.Width"
    pillar_options(**{"pillar.bold": True})
    assert style_bold("Petal.Width") == _bold("Petal.Width")
    assert style_bold(["a", "", None]) == [_bold("a"), "", _bold("NA")]
    assert isinstance(style_bold("Petal.Width"), str)


def test_style_neg_follows_the_option():
    assert style_neg("-1") == _red("-1")
    assert style_neg("123") == _red("123")
    assert style_neg(["-1", "", None, "0"]) == [_red("-1"), "", _red("NA"), _red("0")]
    pillar_options(**{"pillar.neg": False})
    assert style_neg("-1") == "-1"
    assert style_neg([0.01, None]) == ["0.01", None]


def test_style_na_always_red_and_keeps_empty():
    assert style_na("NA") == _red("NA")
    assert style_na("") == _red("")
    assert style_na(None) == _red("NA")
    assert style_na(["NA", "", None, "x"]) == [
        _red("NA"),
        _red(""),
        _red("NA"),
        _red("x"),
    ]
    assert style_na([1, None]) == [_red("1"), _red("NA")]
    assert isinstance(style_na("NA"), str)
    assert isinstance(style_na(["NA"]), list)


def test_style_subtle_num_default_example():
    values = [0.01 * i for i in (1, 2, 3)]
    assert style_subtle_num(values, [True, False, True]) == [
        _red("0.01"),
        "0.02",
        _red("0.03"),
    ]
    assert style_subtle_num(0.01, True) == _red("0.01")
    assert style_subtle_num(0.02, False) == 0.02


def test_style_subtle_num_on_greys_every_element():
    pillar_options(**{"pillar.subtle_num": True})
    assert style_subtle_num(["1", "2"], [True, False]) == [_grey("1"), _grey("2")]
    values = [0.01 * i for i in (1, 2, 3)]
    assert style_subtle_num(values, [True, False, True]) == [
        _grey("0.01"),
        _grey("0.02"),
        _grey("0.03"),
    ]


def test_style_subtle_num_neg_off_still_coerces_when_any_flag_is_true():
    pillar_options(**{"pillar.neg": False})
    values = [0.01 * i for i in (1, 2, 3)]
    assert style_subtle_num(values, [True, False, True]) == ["0.01", "0.02", "0.03"]
    assert style_subtle_num([0.01, 0.02], False) == 0.01
    assert style_subtle_num([0.01, 0.02], [False, False]) == [0.01, 0.02]


def test_style_subtle_num_recycles_to_the_length_of_negative():
    assert style_subtle_num(["a", "b", "c", "d"], True) == _red("a")
    assert style_subtle_num(["a", "b", "c", "d"], [True, False]) == [_red("a"), "b"]
    assert style_subtle_num(["a", "b"], [True, False, True]) == [
        _red("a"),
        "b",
        _red("a"),
    ]
    assert style_subtle_num(["a", "b", "c", "d"], [True, False, True]) == [
        _red("a"),
        "b",
        _red("c"),
    ]
    assert style_subtle_num(["a", "b"], [True, False, True, False]) == [
        _red("a"),
        "b",
        _red("a"),
        "b",
    ]


def test_style_subtle_num_missing_flags_and_values():
    assert style_subtle_num(["a", "b"], None) is None
    assert style_subtle_num(["a", "b", "c"], [True, None, False]) == [_red("a"), None, "c"]
    assert style_subtle_num([0.01, None, 0.03], [False, False, True]) == [
        "0.01",
        None,
        _red("0.03"),
    ]
    assert style_subtle_num([1.0, None], [False, False]) == [1.0, None]
    assert style_subtle_num([float("nan"), 1.0], [False, True]) == ["NaN", _red("1")]
    assert style_subtle_num([float("nan"), 1.0], [True, False]) == [_red("NaN"), "1"]
    assert style_subtle_num([float("inf"), float("-inf")], [False, True]) == [
        "Inf",
        _red("-Inf"),
    ]
    assert style_subtle_num(["", "a", ""], [True, False, True]) == ["", "a", ""]
    assert style_subtle_num(1e5, True) == _red("1e+05")
    assert style_subtle_num(1e-4, True) == _red("1e-04")
    assert style_subtle_num(-0.0, True) == _red("0")


def test_style_subtle_num_empty():
    assert style_subtle_num([], []) == []
    assert style_subtle_num([], True) is None
    assert style_subtle_num([], False) is None
    assert style_subtle_num([], [True, False]) == [None, None]


def test_one_color_pastes_the_text():
    cli_options(**{"cli.num_colors": 1})
    assert style_subtle("text") == "text"
    assert style_subtle(None) == "NA"
    assert style_na("NA") == "NA"
    assert style_na("") == ""
    assert style_neg("-1") == "-1"
    assert format_type_sum("dbl") == "<dbl>"


def test_format_type_sum_default_width():
    assert format_type_sum("dbl", None) == _type_label("<dbl>")
    assert format_type_sum("dbl") == _type_label("<dbl>")
    assert format_type_sum("dbl", 4) == _type_label("<db>")
    assert format_type_sum("dbl", 5) == _type_label("<dbl>")
    assert format_type_sum("dbl", 3) == _type_label("<d>")
    assert format_type_sum("dbl", 2) == _type_label("<>")
    assert format_type_sum("dbl", 0) == _type_label("<>")
    assert format_type_sum("dbl", -1) == _type_label("<>")
    assert format_type_sum("dbl", 4.9) == _type_label("<db>")
    assert format_type_sum("dbl", 5.1) == _type_label("<dbl>")
    assert format_type_sum(None) == _type_label("<NA>")
    assert format_type_sum("") == _type_label("<>")
    assert isinstance(format_type_sum("dbl"), str)


def test_format_type_sum_vector_and_empty():
    assert format_type_sum(["dbl", "int"]) == [
        _type_label("<dbl>"),
        _type_label("<int>"),
    ]
    assert format_type_sum([]) == _type_label("<>")
    with pytest.raises(ValueError, match="length = 2"):
        format_type_sum(["dbl", "int"], 4)
    with pytest.raises(ValueError, match="missing value where TRUE/FALSE needed"):
        format_type_sum([], 4)
    with pytest.raises(TypeError, match="non-numeric argument"):
        format_type_sum("dbl", "4")
    with pytest.raises(ValueError, match="missing value where TRUE/FALSE needed"):
        format_type_sum("dbl", float("nan"))


def test_format_type_sum_asis_has_no_brackets():
    assert format_type_sum(AsIs("kg m/s^2")) == _type_label("kg m/s^2")
    assert format_type_sum(AsIs("kg m/s^2"), 4) == _type_label("kg m")
    assert format_type_sum(AsIs("kg m/s^2"), 8) == _type_label("kg m/s^2")
    assert format_type_sum(AsIs("dbl"), 3) == _type_label("dbl")
    assert format_type_sum(AsIs("dbl"), 0) == ITALIC_OPEN + ITALIC_CLOSE
    assert isinstance(format_type_sum(AsIs("dbl")), str)


def test_format_type_sum_unicode_uses_display_width_and_code_points():
    assert format_type_sum("運氣", 4) == _type_label("<運氣>")
    assert format_type_sum("運氣", 3) == _type_label("<運>")
    assert format_type_sum("運氣", 2) == _type_label("<>")
    assert format_type_sum("運氣", 6) == _type_label("<運氣>")


def test_format_type_sum_subtle_off_is_italic_only():
    pillar_options(**{"pillar.subtle": False})
    assert format_type_sum("dbl") == ITALIC_OPEN + "<dbl>" + ITALIC_CLOSE
    assert format_type_sum(AsIs("")) == ITALIC_OPEN + ITALIC_CLOSE


def test_infinity_width_does_not_truncate():
    assert format_type_sum("dbl", math.inf) == _type_label("<dbl>")


def test_256_colors_use_the_grey_ramp():
    cli_options(**{"cli.num_colors": 256})
    assert style_subtle("text") == "\x1b[38;5;246mtext\x1b[39m"
    assert style_na("NA") == "\x1b[31mNA\x1b[39m"
    assert format_type_sum("dbl") == "\x1b[3m\x1b[38;5;246m<dbl>\x1b[39m\x1b[23m"
    pillar_options(**{"pillar.bold": True})
    assert style_bold("Petal.Width") == "\x1b[1mPetal.Width\x1b[22m"
