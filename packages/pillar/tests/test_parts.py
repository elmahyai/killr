"""Titles, types, and components against pillar 1.11.1."""

import math

import pytest

from cli._options import options as cli_options
from pillar._options import options as pillar_options
from pillar._vec import NULL, DataFrame, Factor
from pillar.parts import (
    new_pillar_component,
    new_pillar_title,
    new_pillar_type,
    pillar_component,
)

CHR = "\x1b[3m\x1b[90m<chr>\x1b[39m\x1b[23m"
FCT = "\x1b[3m\x1b[90m<fct>\x1b[39m\x1b[23m"
DOTS_NAMED = "`...` must be empty.\n\u2716 Problematic argument:\n\u2022 extra = 1"
DOTS_UNNAMED = (
    "`...` must be empty.\n"
    "\u2716 Problematic argument:\n"
    "\u2022 ..1 = 1\n"
    "\u2139 Did you forget to name an argument?"
)


@pytest.fixture(autouse=True)
def _defaults():
    cli_options(**{"cli.num_colors": 8, "cli.unicode": True})
    pillar_options(
        **{
            "pillar.bold": False,
            "pillar.subtle": True,
            "pillar.min_title_chars": 20,
        }
    )
    yield
    cli_options(**{"cli.num_colors": 8, "cli.unicode": True})
    pillar_options(
        **{
            "pillar.bold": False,
            "pillar.subtle": True,
            "pillar.min_title_chars": 20,
        }
    )


def test_trees_titles_pad_girth_and_stay_plain():
    titles = new_pillar_title(["Girth", "Height", "Volume"])
    assert titles.width == 6
    assert titles.min_width == 6
    assert titles.format() == ["Girth ", "Height", "Volume"]
    assert "\x1b" not in "".join(titles.format())


def test_null_and_blank_titles_have_width_zero():
    for value in (None, NULL, "", [None], ["", None], []):
        title = new_pillar_title(value)
        assert title.x is None
        assert title.width == 0
        assert title.min_width == 0
        assert title.format() == []


def test_mixed_missing_title_pastes_na():
    title = new_pillar_title(["a", None, "bb"])
    assert title.format() == ["a ", "NA", "bb"]


def test_letters_title_width_is_seven():
    title = new_pillar_title("letters")
    assert title.width == 7
    assert title.min_width == 7
    assert title.format() == "letters"
    assert isinstance(title.format(), str)


def test_min_title_chars_shrinks_only_past_the_option():
    pillar_options(**{"pillar.min_title_chars": 4})
    short = new_pillar_title("letters")
    assert short.width == 7
    assert short.min_width == 6

    pillar_options(**{"pillar.min_title_chars": float("inf")})
    assert new_pillar_title("letters").min_width == 7

    pillar_options(**{"pillar.min_title_chars": 0})
    assert new_pillar_title("letters").min_width == 2

    pillar_options(**{"pillar.min_title_chars": 15.5})
    wide = new_pillar_title("a" * 30)
    assert wide.width == 30
    assert wide.min_width == 17


def test_min_title_chars_rejects_a_bad_option():
    pillar_options(**{"pillar.min_title_chars": -1})
    with pytest.raises(ValueError, match="nonnegative number"):
        new_pillar_title("a")

    pillar_options(**{"pillar.min_title_chars": "x"})
    with pytest.raises(ValueError, match="nonnegative number"):
        new_pillar_title("a")

    pillar_options(**{"pillar.min_title_chars": [1, 2]})
    with pytest.raises(ValueError, match="nonnegative number"):
        new_pillar_title("a")

    pillar_options(**{"pillar.min_title_chars": float("nan")})
    with pytest.raises(ValueError, match="missing value where TRUE/FALSE needed"):
        new_pillar_title("a")


def test_format_truncates_one_wide_title_by_graphemes():
    assert new_pillar_title(["hello", "hi"]).format(width=4) == ["hel\u2026", "hi  "]
    assert new_pillar_title("hello").format(width=1) == "\u2026"
    assert new_pillar_title("hello").format(width=2) == "h\u2026"
    assert new_pillar_title(["ab", "c"]).format(width=10) == ["ab", "c "]
    assert new_pillar_title("`abcd`").format(width=4) == "abc\u2026"
    assert new_pillar_title("`ab`").format() == "`ab`"
    assert new_pillar_title("\u904b\u6c23\u597d").format(width=4) == "\u904b\u6c23\u597d\u2026"


def test_two_wide_titles_are_rejected():
    with pytest.raises(ValueError, match=r"length\(x\) == 1 is not TRUE"):
        new_pillar_title(["hello", "world"]).format(width=4)


def test_footnote_replaces_the_trailing_mark():
    assert new_pillar_title("hello").format(width=4, footnote_idx=2) == "he\u2026\u00b2"
    assert new_pillar_title("hi").format(width=4, footnote_idx=2) == "hi"
    assert new_pillar_title("a" * 20).format(width=6, footnote_idx=12) == "aaaa\u2026\u02df"
    assert new_pillar_title("abcdefghij").format(width=5, footnote_idx=1) == "abc\u2026\u00b9"


def test_bold_wraps_the_padded_title():
    pillar_options(**{"pillar.bold": True})
    assert new_pillar_title(["Girth", "Height"]).format() == [
        "\x1b[1mGirth \x1b[22m",
        "\x1b[1mHeight\x1b[22m",
    ]


def test_extra_title_argument_uses_the_dots_message():
    with pytest.raises(ValueError) as caught:
        new_pillar_title("a", extra=1)
    assert str(caught.value) == DOTS_NAMED


def test_character_and_factor_types():
    character = new_pillar_type("a")
    assert character.x == "chr"
    assert character.width == 5
    assert character.min_width == 5
    assert character.format() == CHR

    factor = new_pillar_type(Factor(["a"]))
    assert factor.x == "fct"
    assert factor.format() == FCT

    letters = new_pillar_type(list("abcdefghijklmnopqrstuvwxyz"))
    assert letters.x == "chr"
    assert letters.width == 5
    assert letters.min_width == 5


def test_type_width_trims_and_focus_underlines():
    character = new_pillar_type("a")
    assert character.format(width=4) == "\x1b[3m\x1b[90m<ch>\x1b[39m\x1b[23m"
    assert character.format(width=3) == "\x1b[3m\x1b[90m<c>\x1b[39m\x1b[23m"
    assert character.format(width=5) == CHR
    assert character.format(is_focus=True) == "\x1b[4m" + CHR + "\x1b[24m"

    pillar_options(**{"pillar.subtle": False})
    assert new_pillar_type("a").format() == "\x1b[3m<chr>\x1b[23m"


def test_long_type_keeps_minimum_five():
    frame = new_pillar_type(DataFrame({"a": [1]}))
    assert frame.x == "df[,1]"
    assert frame.width == 8
    assert frame.min_width == 5


def test_extra_type_argument_uses_the_dots_message():
    with pytest.raises(ValueError) as caught:
        new_pillar_type("a", extra=1)
    assert str(caught.value) == DOTS_NAMED


def test_component_stores_letters_and_integer_widths():
    component = new_pillar_component([["a", "b", "c"]], width=1)
    assert component.x == [["a", "b", "c"]]
    assert component.width == 1
    assert component.min_width == 1
    assert type(component.width) is int
    assert type(component.min_width) is int

    wider = new_pillar_component([["a", "b", "c"]], width=1.0, min_width=2.0)
    assert wider.width == 1
    assert wider.min_width == 2
    assert type(wider.width) is int

    negative = new_pillar_component([["a"]], width=-1)
    assert negative.width == -1
    assert negative.min_width == -1


def test_component_rejects_a_bad_list_or_width():
    with pytest.raises(ValueError, match=r"is_bare_list\(x\) is not TRUE"):
        new_pillar_component("a", width=1)
    with pytest.raises(ValueError, match=r"length\(x\) == 1 is not TRUE"):
        new_pillar_component(["a", "b"], width=1)
    with pytest.raises(ValueError, match=r"is_integerish\(width\) is not TRUE"):
        new_pillar_component(["a"], width=1.5)
    with pytest.raises(ValueError, match=r"is_integerish\(width\) is not TRUE"):
        new_pillar_component(["a"], width=True)
    with pytest.raises(TypeError, match="argument \"width\" is missing, with no default"):
        new_pillar_component(["a"])
    with pytest.raises(ValueError) as caught:
        new_pillar_component(["a"], 1)
    assert str(caught.value) == DOTS_UNNAMED


def test_non_finite_width_is_missing():
    with pytest.warns(RuntimeWarning, match="NAs introduced by coercion to integer range"):
        component = new_pillar_component(["a"], width=float("inf"))
    assert component.width is None
    assert component.min_width is None

    quiet = new_pillar_component(["a"], width=float("nan"))
    assert quiet.width is None
    assert quiet.min_width is None


def test_pillar_component_copies_title_and_type_widths():
    title = pillar_component(new_pillar_title("letters"))
    assert title.width == 7
    assert title.min_width == 7
    assert title.x[0].x == "letters"

    kind = pillar_component(new_pillar_type(list("abcdefghijklmnopqrstuvwxyz")))
    assert kind.width == 5
    assert kind.min_width == 5
    assert kind.x[0].x == "chr"

    pillar_options(**{"pillar.min_title_chars": 3})
    shrunk = pillar_component(new_pillar_title("letters"))
    assert shrunk.width == 7
    assert shrunk.min_width == 5
