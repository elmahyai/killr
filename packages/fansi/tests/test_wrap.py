"""Wrap, trim, and tab checks against the values installed fansi 1.0.7 returned."""

import pytest

from fansi._args import FansiError
from fansi.strtrim_ctl import strtrim2_ctl, strtrim_ctl, strtrim_sgr
from fansi.strwrap_ctl import strwrap2_ctl, strwrap_ctl, strwrap_sgr
from fansi.tabs_as_spaces import tabs_as_spaces
from fansi.trimws_ctl import trimws_ctl

RED = "hello \033[41mred\033[49m world"


def test_tabs_as_spaces_stops():
    assert tabs_as_spaces("1\t12\t123\t1234\t12345678", warn=False) == [
        "1       12      123     1234    12345678"
    ]
    assert tabs_as_spaces("a\tb\tc", tab_stops=[3, 5], warn=False) == ["a  b    c"]
    assert tabs_as_spaces("a\tb\na\tb", warn=False) == ["a       b\na       b"]
    assert tabs_as_spaces("ab\033[31m\tcd", warn=False) == ["ab\033[31m      cd"]
    assert tabs_as_spaces(["a\tb", None], warn=False) == ["a       b", None]
    # ctl does not turn conversion off; it only changes which bytes have width
    assert tabs_as_spaces("a\tb\tc", ctl=[], warn=False) == ["a       b      c"]


def test_strwrap_ctl_width_and_styles():
    assert strwrap_ctl(RED, 12, warn=False) == ["hello \033[41mred\033[0m", "world"]
    assert strwrap_ctl(["hello world", "a b c"], 8, warn=False) == [
        "hello",
        "world",
        "a b c",
    ]
    assert strwrap_ctl(["hello world", "a b"], 8, simplify=False, warn=False) == [
        ["hello", "world"],
        ["a b"],
    ]
    assert strwrap_ctl([None, "ab cd"], 8, warn=False) == ["NA", "ab cd"]
    assert strwrap_ctl("", 10, indent=3, warn=False) == [""]
    assert strwrap_ctl([], 10, warn=False) == []
    # An omitted width is 72, 0.9 times the usual 80-column option.
    words = " ".join(["word"] * 30)
    assert strwrap_ctl(words, warn=False) == strwrap_ctl(words, 72, warn=False)


def test_strwrap2_features():
    assert strwrap2_ctl("abcdefghijklmnop", 12, wrap_always=True, warn=False) == [
        "abcdefghijk",
        "lmnop",
    ]
    assert strwrap2_ctl("你好世界朋友", 5, wrap_always=True, warn=False) == [
        "你好",
        "世界",
        "朋友",
    ]
    assert strwrap2_ctl("hi there friend", 10, pad_end=".", warn=False) == [
        "hi there.",
        "friend...",
    ]
    assert strwrap2_ctl("hello world today", 8, strip_spaces=False, warn=False) == [
        "hello ",
        "world ",
        "today",
    ]
    assert strwrap2_ctl("hello\tred\tworld", 12, tabs_as_spaces=True, warn=False) == [
        "hello   red",
        "     world",
    ]
    assert strwrap_ctl("hello\n\nworld  today", 20, warn=False) == [
        "hello",
        "",
        "world today",
    ]
    assert strwrap_ctl("Hi.  There you go now", 12, warn=False) == [
        "Hi.  There",
        "you go now",
    ]
    with pytest.raises(FansiError, match="narrower than character width"):
        strwrap2_ctl("你好", 2, wrap_always=True, warn=False)
    with pytest.raises(FansiError, match="at least 2"):
        strwrap2_ctl("abcd", 1, wrap_always=True, warn=False)
    with pytest.raises(FansiError, match="should not both be TRUE"):
        strwrap2_ctl("a\tb", 10, tabs_as_spaces=True, strip_spaces=True, warn=False)


def test_carry_and_sgr_alias():
    assert strwrap_ctl(
        ["\033[31mhello world", "again"], 8, carry=True, terminate=True, warn=False
    ) == [
        "\033[31mhello\033[0m",
        "\033[31mworld\033[0m",
        "\033[31magain\033[0m",
    ]
    assert strwrap_sgr("hello \033[31mred\033[39m world", 12, warn=False) == [
        "hello \033[31mred\033[0m",
        "world",
    ]
    assert strwrap2_ctl("\033[31mabcdefghij\033[0m", 6, wrap_always=True, warn=False) == [
        "\033[31mabcde\033[0m",
        "\033[31mfghij\033[0m",
    ]


def test_strtrim_counts_c0_as_zero():
    assert strtrim_ctl("\033[42mHello world\033[m", 6, warn=False) == [
        "\033[42mHello \033[0m"
    ]
    assert strtrim_ctl(["hello world", "ab", None], 6, warn=False) == [
        "hello ",
        "ab",
        None,
    ]
    assert strtrim_ctl("ab\ncd", 3, warn=False) == ["ab\nc"]
    assert strtrim_ctl("ab\ncd", 3, ctl="sgr", warn=False) == ["ab\n"]
    assert strtrim2_ctl("a\tbcd", 4, tabs_as_spaces=True, warn=False) == ["a   "]
    assert strtrim_ctl(
        ["\033[31mhelloxxx", None, "world"], 4, carry=True, warn=False
    ) == ["\033[31mhell\033[0m", None, None]
    assert strtrim_sgr("\033[42mHello world\033[m", 6, warn=False) == [
        "\033[42mHello \033[0m"
    ]
    with pytest.raises(FansiError, match="width - 1"):
        strtrim_ctl("hello", 0, warn=False)


def test_trimws_partial_which():
    assert trimws_ctl(" \033[31m\thello world\t\033[39m  ", warn=False) == [
        "\033[31mhello world\033[0m"
    ]
    assert trimws_ctl("  hi  ", "l", warn=False) == ["hi  "]
    assert trimws_ctl("  hi  ", "right", warn=False) == ["  hi"]
    assert trimws_ctl(" a ", "bo", warn=False) == ["a"]
    assert trimws_ctl(["  a", None, "b  "], warn=False) == ["a", None, "b"]
    assert trimws_ctl("   ", warn=False) == [""]
    with pytest.raises(FansiError, match="whitespace"):
        trimws_ctl(" a ", whitespace=" ")
    with pytest.raises(FansiError, match="partial match"):
        trimws_ctl(" a ", "leftright")
