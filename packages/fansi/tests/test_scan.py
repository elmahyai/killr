"""Scanner checks against the values installed fansi 1.0.7 returned."""

import warnings

import pytest

from fansi._args import FansiError
from fansi.has_ctl import has_ctl, has_sgr
from fansi.nchar_ctl import nchar_ctl, nchar_sgr, nzchar_ctl, nzchar_sgr
from fansi.strip_ctl import strip_ctl, strip_sgr

MOON = "hello\033k\033[45p world\n\033[31mgoodbye\a moon"
CJK = "\033[31m\u4e00\u4e01\u4e03\a\r"
COMBO = "hello\u0300\u035c world"
ZWJ = "\U0001f468\u200d\U0001f469\u200d\U0001f467"
FLAG = "\U0001f1fa\U0001f1f8"


def test_has_ctl_suggested():
    assert has_ctl("hello world") == [False]
    assert has_ctl("hello\nworld") == [True]
    assert has_ctl("hello\033[31mworld\033[m", ctl="sgr") == [True]
    assert has_ctl("\n") == [True]
    assert has_ctl("\n", ctl=[]) == [False]
    assert has_ctl(None, ctl=[]) == [False]
    assert has_ctl(None) == [None]


def test_has_sgr():
    assert has_sgr("hello\nworld") == [False]
    assert has_sgr("hello\033[31mworld\033[m") == [True]


def test_strip_ctl_suggested():
    assert strip_ctl(MOON) == ["hello worldgoodbye moon"]
    assert strip_ctl(MOON, ctl="sgr") == [
        "hello\033k\033[45p world\ngoodbye\a moon"
    ]
    assert strip_ctl(MOON, ctl=["all", "nl", "c0"]) == [
        "hello world\ngoodbye\a moon"
    ]
    assert strip_ctl(MOON, ctl=[]) == [MOON]
    assert strip_ctl(None) == [None]


def test_strip_sgr():
    assert strip_sgr("hello\033[31mworld") == ["helloworld"]
    assert strip_sgr(MOON) == strip_ctl(MOON, ctl=["sgr", "url"])


def test_nchar_ctl_suggested():
    assert nchar_ctl("\033[31m123\a\r") == [3]
    assert nchar_ctl(CJK) == [3]
    assert nchar_ctl(CJK, type="width") == [6]
    assert nchar_ctl(CJK, type="bytes") == [9]
    assert nchar_ctl("\t\n\r", ctl="all") == [0]
    assert nchar_ctl("\t\n\r", ctl="c0") == [1]
    assert nchar_ctl("\t\n\r", ctl=["c0", "nl"]) == [0]


def test_width_and_graphemes():
    assert nchar_ctl(COMBO, type="width") == [11]
    assert nchar_ctl(COMBO, type="graphemes") == [11]
    assert nchar_ctl(COMBO, type="chars") == [13]
    assert nchar_ctl("A\u030a", type="width") == [1]
    assert nchar_ctl("A\u030a", type="graphemes") == [1]
    assert nchar_ctl(ZWJ, type="width") == [2]
    assert nchar_ctl(ZWJ, type="graphemes") == [1]
    assert nchar_ctl(ZWJ, type="chars") == [5]
    assert nchar_ctl(FLAG, type="width") == [2]
    assert nchar_ctl(FLAG, type="graphemes") == [1]
    assert nchar_ctl("\U0001f1fa" * 3, type="width") == [4]
    assert nchar_ctl("\U0001f1fa" * 3, type="graphemes") == [2]
    assert nchar_ctl("\u4e00\u0300", type="width") == [2]
    assert nchar_ctl("\u4e00\u0300", type="graphemes") == [1]
    broken = "\U0001f468\u200d\033[31m\U0001f469"
    assert nchar_ctl(broken, type="width") == [4]
    assert nchar_ctl(broken, type="graphemes") == [2]


def test_nchar_missing_and_types():
    assert nchar_ctl(None) == [None]
    assert nchar_ctl(None, keepNA=False) == [2]
    assert nchar_ctl(None, type="width") == [2]
    assert nchar_ctl(None, type="graphemes") == [2]
    assert nchar_ctl(None, type="bytes") == [None]
    assert nchar_ctl("abcd", type="g") == [4]
    assert nchar_ctl(["a", None, "\033[31mb"]) == [1, None, 1]


def test_nchar_sgr_and_nzchar():
    assert nchar_sgr("\033[31m123") == [3]
    assert nchar_sgr("\t\n\n123") == [6]
    assert nzchar_ctl("\n\033[42;31m\033[123P\a") == [False]
    assert nzchar_ctl(None) == [True]
    assert nzchar_ctl(None, keepNA=True) == [None]
    assert nzchar_sgr(None) == [True]
    assert nzchar_sgr("\033[31m") == [False]


def test_bad_utf8_and_warnings():
    bad = "\udcf0"
    with pytest.raises(FansiError, match="malformed UTF-8 sequence"):
        nchar_ctl(bad)
    assert nchar_ctl(bad, allowNA=True) == [None]
    with pytest.raises(FansiError, match="malformed UTF-8 sequence"):
        nchar_ctl(bad, warn=False)
    assert nzchar_ctl(bad) == [True]
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        assert nchar_ctl("hello\033") == [5]
    assert "malformed escape sequence at index [1]" in str(caught[0].message)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        assert nchar_ctl("\033[31m123\a\r") == [3]
    assert caught == []


def test_deprecation_and_argument_errors(capsys):
    assert nchar_ctl("abc", strip="sgr") == [3]
    assert has_ctl("\033[31mx", which="sgr") == [True]
    err = capsys.readouterr().err
    assert "Parameter `strip` has been deprecated; use `ctl` instead." in err
    assert "Parameter `which` has been deprecated; use `ctl` instead." in err
    with pytest.raises(FansiError, match="must be TRUE or FALSE"):
        has_ctl("a", warn=None)
    with pytest.raises(FansiError, match="scalar logical"):
        nchar_ctl("a", keepNA=[True, False])
