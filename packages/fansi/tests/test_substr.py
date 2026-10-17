"""substr_ctl and strsplit_ctl checked against installed fansi 1.0.7."""

import pytest

from fansi._args import FansiError
from fansi.strsplit_ctl import strsplit_ctl, strsplit_sgr
from fansi.substr_ctl import (
    substr2_ctl,
    substr2_ctl_replace,
    substr2_sgr,
    substr_ctl,
    substr_ctl_replace,
    substr_sgr,
)

HELLO = "\033[42mhello\033[m world"
WIDE = "\uFF37n\uFF37"
MARK = "\uFF37e\u0301\uFF37"


def test_substr_ctl_manual():
    assert substr_ctl(HELLO, 1, 9, warn=False) == ["\033[42mhello\033[m wor"]
    assert substr_ctl(HELLO, 3, 9, warn=False) == ["\033[42mllo\033[m wor"]


def test_substr2_width_and_mark():
    assert substr2_ctl(WIDE, 2, 4, type="width", round="start", warn=False) == ["\uFF37n"]
    assert substr2_ctl(WIDE, 2, 4, type="width", round="stop", warn=False) == ["n\uFF37"]
    assert substr2_ctl(WIDE, 2, 4, type="width", round="neither", warn=False) == ["n"]
    assert substr2_ctl(WIDE, 2, 4, type="width", round="both", warn=False) == [WIDE]
    assert substr2_ctl(MARK, 2, 4, type="width", round="start", warn=False) == ["\uFF37e\u0301"]
    assert substr2_ctl(MARK, 2, 4, type="width", round="stop", warn=False) == ["e\u0301\uFF37"]
    assert substr2_ctl(MARK, 2, 4, type="width", round="neither", warn=False) == ["e\u0301"]
    assert substr2_ctl(MARK, 2, 4, type="width", round="both", warn=False) == [MARK]
    assert substr2_ctl(MARK, 1, 2, type="graphemes", warn=False) == ["\uFF37e\u0301"]
    assert substr2_ctl(MARK, 1, 2, type="chars", warn=False) == ["\uFF37e"]
    assert substr2_ctl(WIDE, 2, 4, type="wi", round="ne", warn=False) == ["n"]


def test_carry_terminate_and_controls():
    pair = ["\033[33mhello", "world"]
    assert substr_ctl(pair, 1, 3, warn=False) == ["\033[33mhel\033[0m", "wor"]
    assert substr_ctl(pair, 1, 3, carry=True, warn=False) == [
        "\033[33mhel\033[0m",
        "\033[33mwor\033[0m",
    ]
    assert substr_ctl(pair, 1, 3, carry="\033[44m", warn=False) == [
        "\033[33;44mhel\033[0m",
        "\033[33;44mwor\033[0m",
    ]
    assert substr_ctl("ABC\033[42m", 1, 3, terminate=False, warn=False) == ["ABC"]
    assert substr_ctl("ABC\033[42m", 1, 4, terminate=False, warn=False) == ["ABC\033[42m"]
    assert substr_ctl("hello", 0, -1, warn=False) == [""]
    assert substr_ctl("hello", 4, 1, warn=False) == [""]
    assert substr_ctl(["AB", None, "CD"], 1, 2, carry=True, warn=False) == ["AB", None, None]
    assert substr_ctl(["hello", "world", "xyz"], [1, 2], [2, 3], warn=False) == [
        "he",
        "or",
        "xy",
    ]


def test_sgr_variants_and_state():
    assert substr_sgr("\033[31mhello\nworld", 1, 8, warn=False) == [
        "\033[31mhello\nwo\033[0m"
    ]
    assert substr2_sgr(MARK, 2, 4, type="width", round="start", warn=False) == [
        "\uFF37e\u0301"
    ]
    assert substr_ctl("\033[31;42mhello", 2, 4, normalize=True, warn=False) == [
        "\033[31m\033[42mell\033[39m\033[49m"
    ]
    assert substr_ctl("\033]8;;http://x\033\\hello\033]8;;\033\\", 2, 4, warn=False) == [
        "\033]8;;http://x\033\\ell\033]8;;\033\\"
    ]
    assert substr_ctl("\033[11mhello\033[m", 2, 4, warn=False) == ["\033[11mell\033[0m"]
    assert substr2_ctl("yo\tworld", 1, 8, tabs_as_spaces=True, warn=False) == ["yo      "]


def test_replacement():
    source = ["\033[42mABC", "\033[34mDEF"]
    assert substr_ctl_replace(source, 2, 2, "_", warn=False) == [
        "\033[42mA\033[0m_\033[42mC",
        "\033[34mD\033[0m_\033[34mF",
    ]
    assert substr_ctl_replace(source, 2, 2, "\033[45m_", warn=False) == [
        "\033[42mA\033[0m\033[45m_\033[0m\033[42mC",
        "\033[34mD\033[0m\033[45m_\033[0m\033[34mF",
    ]
    assert substr_ctl_replace("ABCD", 2, 3, "#?-", warn=False) == ["A#?D"]
    assert substr_ctl_replace(["AB", "CDE", "EFGH"], 2, 3, ["_", "_."], warn=False) == [
        "A_",
        "C_.",
        "E_GH",
    ]
    assert substr2_ctl_replace(
        MARK, 2, 4, "n", type="width", round="start", warn=False
    ) == ["n\uFF37"]
    assert substr2_ctl_replace(
        "A123456789B", 2, 9, "\t", tabs_as_spaces=True, warn=False
    ) == ["A        9B"]
    styled = "\033[32mAB\033[45m"
    assert substr_ctl_replace(styled, 1, 3, "", warn=False) == [styled]
    assert substr_ctl_replace(["AB", None, "BC"], 1, 1, "#", warn=False) == [
        "#B",
        None,
        "#C",
    ]


def test_strsplit_manual():
    assert strsplit_ctl("\033[31mhello\033[42m world!", " ", warn=False) == [
        ["\033[31mhello\033[0m", "\033[31;42mworld!\033[0m"]
    ]
    assert strsplit_ctl("\033[31mhello\033[42m\nworld!", "\n", warn=False) == [
        ["\033[31mhello\033[42m\nworld!"]
    ]
    assert strsplit_ctl(
        "\033[31mhello\033[42m\nworld!", "\n", ctl=["all", "nl"], warn=False
    ) == [["\033[31mhello\033[0m", "\033[31;42mworld!\033[0m"]]
    assert strsplit_sgr("\033[31mhello\033[42m\nworld!", "\n", warn=False) == [
        ["\033[31mhello\033[0m", "\033[31;42mworld!\033[0m"]
    ]
    assert strsplit_ctl("\uFF37n\uFF37", "n", warn=False) == [["\uFF37", "\uFF37"]]
    assert strsplit_ctl("", " ", warn=False) == [[]]
    assert strsplit_ctl(["ab", None, "a b", ""], " ", warn=False) == [
        ["ab"],
        [None],
        ["a", "b"],
        [],
    ]
    assert strsplit_ctl("a.b", ".", warn=False) == [["", "", ""]]
    assert strsplit_ctl("a.b", ".", fixed=True, warn=False) == [["a", "b"]]


def test_errors():
    with pytest.raises(FansiError, match="partial match"):
        substr2_ctl("a", 1, 1, type="bananas")
    with pytest.raises(FansiError, match="tab.stops"):
        substr2_ctl("a", 1, 1, tab_stops=0)
    with pytest.raises(FansiError, match="replacement mode"):
        substr_ctl_replace("a", 1, 1, "b", carry="\033[41m")
    with pytest.raises(FansiError, match="may not contain NAs"):
        strsplit_ctl("a", None)
    with pytest.raises(FansiError, match="fixed"):
        strsplit_ctl("a", "b", fixed=None)
