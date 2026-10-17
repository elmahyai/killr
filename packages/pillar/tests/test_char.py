"""char() and set_char_opts() against pillar 1.11.1."""

import pytest

from pillar.char import (
    char,
    format_pillar_char_attr,
    set_char_opts,
    vec_ptype_abbr,
    vec_ptype_full,
)


def test_char_keeps_data_and_formats_mid():
    out = char(["a", "bb"], min_chars=5, shorten="mid")
    assert out.data == ["a", "bb"]
    assert out.marked is True
    assert out.pillar.shorten == "mid"
    assert out.pillar.min_chars == 5
    assert format_pillar_char_attr(out.pillar) == "pillar_char(5)|"
    assert vec_ptype_full(out) == "pillar_char(5)|"
    assert vec_ptype_abbr(out) == "char"


def test_missing_string_stays_missing():
    out = char(["a", None])
    assert out.data == ["a", None]
    assert out.data[1] is None
    assert format_pillar_char_attr(out.pillar) == "pillar_char"
    assert vec_ptype_abbr(out) == "char"
    assert char(None).data is None


def test_abbreviate_adds_no_mark():
    out = char("hello", min_chars=3, shorten="abbreviate")
    assert out.data == "hello"
    assert out.pillar.shorten == "abbreviate"
    assert format_pillar_char_attr(out.pillar) == "pillar_char(3)"
    assert vec_ptype_abbr(out) == "char"


def test_shorten_marks():
    assert format_pillar_char_attr(char("ab", shorten="back").pillar) == "pillar_char>"
    assert format_pillar_char_attr(char("ab", shorten="front").pillar) == "pillar_char<"
    assert format_pillar_char_attr(char("ab", min_chars=2, shorten="front").pillar) == "pillar_char(2)<"
    assert format_pillar_char_attr(char("ab", min_chars=1, shorten="back").pillar) == "pillar_char(1)>"


def test_omitted_shorten_stays_none():
    out = char("a", shorten=None, min_chars=None)
    assert out.pillar.shorten is None
    assert out.pillar.min_chars is None
    assert format_pillar_char_attr(out.pillar) == "pillar_char"


def test_stored_abbr_and_never():
    out = char("a")
    out.pillar.shorten = "abbr"
    assert vec_ptype_abbr(out) == "abbr"
    assert format_pillar_char_attr(out.pillar) == "pillar_char&"
    out.pillar.shorten = "never"
    assert vec_ptype_abbr(out) == "char"
    assert format_pillar_char_attr(out.pillar) == "pillar_char="
    out.pillar.shorten = "abbreviate"
    assert vec_ptype_abbr(out) == "char"
    assert format_pillar_char_attr(out.pillar) == "pillar_char"


def test_prefix_is_rejected():
    with pytest.raises(ValueError, match="not \"b\""):
        char("a", shorten="b")
    with pytest.raises(ValueError, match="not \"ab\""):
        char("a", shorten="ab")
    with pytest.raises(ValueError):
        char("a", shorten="nope")


def test_number_is_not_character():
    with pytest.raises(ValueError, match="is.character"):
        char(1)
    with pytest.raises(ValueError, match="is.character"):
        char([1, "a"])
    with pytest.raises(ValueError, match="is.character"):
        char(True)


def test_dots_must_be_empty():
    with pytest.raises(ValueError, match="empty"):
        char("a", extra=1)
    with pytest.raises(ValueError, match="empty"):
        set_char_opts("a", "back")


def test_min_chars_uses_paste0():
    assert format_pillar_char_attr(char("a", min_chars=1e5).pillar) == "pillar_char(1e+05)"
    assert format_pillar_char_attr(char("a", min_chars=1e-4).pillar) == "pillar_char(1e-04)"
    assert format_pillar_char_attr(char("a", min_chars=5.5).pillar) == "pillar_char(5.5)"
    assert format_pillar_char_attr(char("a", min_chars=True).pillar) == "pillar_char(TRUE)"
    assert format_pillar_char_attr(char("a", min_chars="5").pillar) == "pillar_char(5)"
    assert format_pillar_char_attr(char("a", min_chars=[1, 2]).pillar) == [
        "pillar_char(1)",
        "pillar_char(2)",
    ]


def test_empty_vector_and_copy():
    assert char([]).data == []
    src = ["a", "bb"]
    out = char(src, min_chars=5, shorten="mid")
    src.append("c")
    assert out.data == ["a", "bb"]


def test_set_char_opts_keeps_data_and_stays_unmarked():
    out = set_char_opts(["a", "bb"], min_chars=5, shorten="mid")
    assert out.data == ["a", "bb"]
    assert out.marked is False
    assert out.classes == ()
    assert format_pillar_char_attr(out.pillar) == "pillar_char(5)|"
    assert vec_ptype_abbr(out) == "chr"
    plain = set_char_opts(["a", None])
    assert plain.data[1] is None
    assert format_pillar_char_attr(plain.pillar) == "pillar_char"
    number = set_char_opts(3, min_chars=2)
    assert number.data == 3
    assert format_pillar_char_attr(number.pillar) == "pillar_char(2)"


def test_set_char_opts_on_pillar_char_keeps_the_mark():
    base = char(["a", "bb"], shorten="mid")
    out = set_char_opts(base, min_chars=9, shorten="back")
    assert out.marked is True
    assert out.data == ["a", "bb"]
    assert format_pillar_char_attr(out.pillar) == "pillar_char(9)>"
    assert vec_ptype_abbr(out) == "char"
    assert format_pillar_char_attr(base.pillar) == "pillar_char|"
    again = char(base)
    assert again.marked is True
    assert again.data == ["a", "bb"]
    assert format_pillar_char_attr(again.pillar) == "pillar_char"
    assert vec_ptype_abbr(again) == "char"
