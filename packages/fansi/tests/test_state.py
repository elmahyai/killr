"""State writers checked against values installed fansi 1.0.7 returned."""

import warnings

import pytest

from fansi._args import FansiError
from fansi.has_ctl import has_ctl
from fansi.normalize_state import normalize_state
from fansi.state_at_end import close_state, state_at_end
from fansi.unhandled_ctl import unhandled_ctl

TC = ["bright", "256"]
WIDE = "A\033[33;44mB\033[1;2;3;4;5;6;7;8;9;11;21;26;51;52;53;60;61;62;63;64mC\033[m"


def test_normalize_decomposes_sgr():
    assert normalize_state("hello\033[42;33m world", warn=False, term_cap=TC) == [
        "hello\033[33m\033[42m world"
    ]
    assert normalize_state("hello\033[42;33m world\033[m", warn=False, term_cap=TC) == [
        "hello\033[33m\033[42m world\033[39m\033[49m"
    ]
    assert normalize_state("\033[31;32mhello\033[m", warn=False, term_cap=TC) == [
        "\033[32mhello\033[39m"
    ]
    assert normalize_state("\033[31mhe\033[49mllo\033[m", warn=False, term_cap=TC) == [
        "\033[31mhello\033[39m"
    ]
    assert normalize_state(WIDE, warn=False, term_cap=TC) == [
        "A\033[33m\033[44mB\033[1m\033[2m\033[3m\033[4m\033[5m\033[6m\033[7m"
        "\033[8m\033[9m\033[21m\033[26m\033[51m\033[52m\033[53m\033[60m\033[61m"
        "\033[62m\033[63m\033[64m\033[11mC\033[10m\033[22m\033[23m\033[24m"
        "\033[25m\033[27m\033[28m\033[29m\033[39m\033[49m\033[50m\033[54m"
        "\033[55m\033[65m"
    ]


def test_normalize_carry_and_urls():
    assert normalize_state("he\033[0mllo", carry="\033[41m", warn=False, term_cap=TC) == [
        "he\033[49mllo"
    ]
    assert normalize_state(
        ["A\033[31;42mB", "A\033[39;4mB"], carry=True, warn=False, term_cap=TC
    ) == ["A\033[31m\033[42mB", "A\033[39m\033[4mB"]
    assert normalize_state(
        ["AB\033[31;42m", None, "\033[0;4mAB"], carry=True, warn=False, term_cap=TC
    ) == ["AB\033[31m\033[42m", None, None]
    merged = "A\033]8;id=a;x.yz\033\\B\033]8;id=a;x.yz\033\\C\033]8;;\033\\D"
    assert normalize_state(merged, warn=False, term_cap=TC) == [
        "A\033]8;id=a;x.yz\033\\BC\033]8;;\033\\D"
    ]
    assert normalize_state("\033]8;;z\033\\\033[31mA", warn=False, term_cap=TC) == [
        "\033[31m\033]8;;z\033\\A"
    ]
    assert normalize_state("plain\033k", warn=False, term_cap=TC) == ["plain\033k"]
    assert normalize_state(None, warn=False, term_cap=TC) == [None]
    assert normalize_state("", warn=False, term_cap=TC) == [""]


def test_state_at_end_and_close():
    x = ["\033[44mhello", "\033[33mworld"]
    assert state_at_end(x, warn=False, term_cap=TC) == ["\033[44m", "\033[33m"]
    carried = state_at_end(x, carry=True, normalize=True, warn=False, term_cap=TC)
    assert carried == ["\033[44m", "\033[33m\033[44m"]
    assert close_state(carried, normalize=True, warn=False) == [
        "\033[49m",
        "\033[39m\033[49m",
    ]
    assert close_state(carried, normalize=False, warn=False) == ["\033[0m", "\033[0m"]
    assert close_state(["hello", "", None, "\033[31m"], warn=False) == [
        "",
        "",
        "",
        "\033[0m",
    ]
    assert close_state("\033[31m\033]8;;z\033\\", normalize=True, warn=False) == [
        "\033[39m\033]8;;\033\\"
    ]
    assert state_at_end("\033]8;id=a;http://x\033\\hi", warn=False, term_cap=TC) == [""]
    assert state_at_end(
        ["\033[42mA", None, "\033[31mA"], carry=True, warn=False, term_cap=TC
    ) == ["\033[42m", None, None]


def test_unhandled_codes():
    string = [
        "\033[41mhello world\033[m",
        "foo\033[22>m",
        "\033[999mbar",
        "baz \033[31#3m",
        "a\033[31k",
        "hello\033m world",
    ]
    found = unhandled_ctl(string, term_cap=TC)
    assert found["index"] == [2, 3, 4, 5, 6]
    assert found["start"] == [4, 1, 5, 2, 6]
    assert found["stop"] == [9, 6, 11, 6, 7]
    assert found["error"] == [
        "invalid-substr",
        "invalid-substr",
        "invalid-substr",
        "non-SGR/hyperlink",
        "non-CSI/OSC",
    ]
    assert found["translated"] == [False, False, False, False, False]
    assert found["esc"] == ["\033[22>m", "\033[999m", "\033[31#3m", "\033[31k", "\033m"]
    wide = unhandled_ctl("\u4e00\u4e01\033[999mX\a", term_cap=TC)
    assert wide["start"] == [5, 12]
    assert wide["stop"] == [10, 12]
    assert wide["error"] == ["invalid-substr", "C0"]
    assert unhandled_ctl("hello", term_cap=TC)["index"] == []


def test_errors_and_warning():
    with pytest.raises(FansiError, match="Argument `carry` may not be NA"):
        normalize_state("a", carry=None, warn=False, term_cap=TC)
    with pytest.raises(FansiError, match="exceeded color buffer"):
        normalize_state(
            "\033[48;2;255;255;255mX",
            warn=False,
            term_cap=["bright", "256", "truecolor"],
        )
    with pytest.raises(FansiError, match="Argument `norm` must be TRUE or FALSE"):
        state_at_end("a", normalize="yeah", warn=False, term_cap=TC)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        assert normalize_state("\033[999m", warn=True, term_cap=TC) == [""]
    assert len(caught) == 1
    assert "invalid substrings at index [1]" in str(caught[0].message)


def test_reader_still_sees_sgr():
    assert has_ctl("hello\033[31mworld\033[m", ctl="sgr") == [True]
