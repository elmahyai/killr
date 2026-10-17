"""Checks for stri_pad and the left, right, and both wrappers."""

from __future__ import annotations

import pytest

from stringi._na import NA
from stringi.pad import stri_pad, stri_pad_both, stri_pad_left, stri_pad_right


def test_pad_sides_and_odd_both():
    assert stri_pad_left("stringi", 10, pad="#") == "###stringi"
    assert stri_pad_right("ab", 5, pad="*") == "ab***"
    assert stri_pad("ab", 5) == "   ab"
    assert stri_pad("ab", 5, "r") == "ab   "
    assert stri_pad("ab", 5, "b") == " ab  "
    assert stri_pad_both("ab", 5, pad="*") == "*ab**"
    assert stri_pad_both("ab", 6, pad="*") == "**ab**"
    assert stri_pad_both("ab", 3, pad="*") == "ab*"
    assert stri_pad_both("stringi", list(range(8, 13)), pad="*") == [
        "stringi*",
        "*stringi*",
        "*stringi**",
        "**stringi**",
        "**stringi***",
    ]


def test_pad_width_is_display_width():
    assert stri_pad_left("\u1100", 4) == "  \u1100"
    assert stri_pad_left("\u1100", 4, use_length=True) == "   \u1100"
    hangul = "\ud6c8\ubbfc\uc815\uc74c"
    assert stri_pad_both([hangul, "abcd"], width=10) == [
        " " + hangul + " ",
        "   abcd   ",
    ]
    assert stri_pad_left("x", 3, pad="a\u0301") == "a\u0301a\u0301x"
    with pytest.raises(ValueError, match="total width 1"):
        stri_pad_left("x", 3, pad="\u1100")
    with pytest.raises(ValueError, match="exactly 1 code points"):
        stri_pad_left("x", 3, pad="ab", use_length=True)
    with pytest.raises(ValueError, match="total width 1"):
        stri_pad_left("x", 3, pad="")


def test_pad_na_short_negative_and_recycling():
    padded = stri_pad(["a", NA], [3, 4], pad=["*", NA])
    assert padded == ["**a", NA]
    assert padded[1] is NA
    assert stri_pad_left("NA", 4, pad=".") == "..NA"
    assert stri_pad_left("", 3, pad="*") == "***"
    assert stri_pad_left("abcd", 2, pad="*") == "abcd"
    assert stri_pad_left("a", 0, pad="*") == "a"
    assert stri_pad_left("a", -3, pad="*") == "a"
    assert stri_pad_left("a", NA) is NA
    assert stri_pad_left("a", 3.9, pad="*") == "**a"
    assert stri_pad_left(["a", "bb"], [4, 2], pad="x") == ["xxxa", "bb"]
    with pytest.warns(UserWarning, match="not a multiple"):
        assert stri_pad_left(["a", "b", "c"], [3, 4], pad="*") == ["**a", "***b", "**c"]
    assert stri_pad(None, 4) == []
    assert stri_pad_left("x") == (" " * 71) + "x"


def test_pad_side_match_arg():
    assert stri_pad("a", 3, ["left", "right", "both"]) == "  a"
    with pytest.raises(ValueError, match="left"):
        stri_pad("a", 3, "middle")
    with pytest.raises(ValueError, match="left"):
        stri_pad("a", 3, "")
