"""Behavior that the R package tests and the comparison cases rely on."""

import pytest

from backports._values import NA, BackportError
from backports import (
    Dots,
    Factor,
    Name,
    anyNA,
    as_character_rconcordance,
    as_rconcordance_default,
    asplit,
    capture_output,
    deparse1,
    dQuote,
    dots_elt,
    dots_length,
    dots_names,
    endsWith,
    get_backports,
    hasName,
    import_,
    isFALSE,
    isTRUE,
    lengths,
    list2DF,
    matchConcordance,
    message,
    null_coalesce,
    paste,
    paste0,
    sQuote,
    startsWith,
    stopifnot,
    str2expression,
    str2lang,
    strrep,
    trimws,
    URLencode,
    valid_factor,
    Array,
)


def test_predicates_and_names():
    assert isTRUE(True) is True
    assert isTRUE([True, True]) is False
    assert isTRUE(1) is False
    assert isFALSE(False) is True
    assert isFALSE(NA) is False
    assert hasName({"a": 1, "b": 2}, ["a", "b", "c"]) == [True, True, False]
    assert anyNA(["a", "b"]) is False
    assert anyNA([1, NA]) is True
    assert anyNA([[[NA]]], recursive=True) is True
    assert lengths([[1, 2, 3], 2]) == [3, 1]
    assert lengths({"a": [1, 2, 3], "b": 2}, use_names=False) == [3, 1]


def test_strings():
    assert trimws(["  a  ", "b  ", "  c"]) == ["a", "b", "c"]
    assert trimws(["  a  ", "b  ", "  c"], which="left") == ["a  ", "b  ", "c"]
    assert startsWith(["aabb", "bbcc"], "bb") == [False, True]
    assert endsWith(["aabb", "bbcc"], "bb") == [True, False]
    assert strrep("-", 10) == "----------"
    assert strrep(["a", NA], [2, 3]) == ["aa", NA]
    assert null_coalesce(None, False) is False
    assert null_coalesce(False, None) is False
    assert URLencode("a b") == "a%20b"
    assert URLencode("ab%20cd") == "ab%20cd"
    assert URLencode("ab%20cd", repeated=True) == "ab%2520cd"
    assert dQuote("foo") == "\u201cfoo\u201d"
    assert dQuote("foo", q="TeX") == "``foo''"
    assert sQuote("foo", q="TeX") == "`foo'"
    assert valid_factor(Factor(["a", "b", "c"])) is True


def test_version_table():
    assert get_backports("4.5.0") == []
    assert get_backports("3.5.0")[:4] == ["%||%", "as.Rconcordance", "matchConcordance", "...names"]
    assert import_("backports") is True


def test_paste_and_stop():
    assert paste(["a", "b", "c"], [], collapse=None, recycle0=True) == []
    assert paste(["a", "b", "c"], [], collapse="_", recycle0=True) == ""
    assert paste(["a", "b", "c"], [1, 2, 3], sep="-") == ["a-1", "b-2", "c-3"]
    assert paste(["a", NA], "b", collapse="|") == "a b|NA b"
    assert paste0(["a", "b", "c"], [], recycle0=True) == []
    with pytest.raises(BackportError, match="Test"):
        stopifnot(**{"Test": False})
    assert stopifnot(**{"Test": True}) is None


def test_language_and_concordance():
    assert deparse1(Name("foo bar")) == "foo bar"
    assert deparse1(str2lang("x[3] <- 1+4")) == "x[3] <- 1 + 4"
    assert deparse1(str2lang("log(y)")) == "log(y)"
    assert deparse1(str2expression("abc")) == "expression(abc)"
    sample = "<!-- concordance::Sample.Rmd:1 9 1 1 6 14 1 -->"
    obj = as_rconcordance_default(sample)
    assert as_character_rconcordance(obj, targetfile="out.tex") == (
        "concordance:out.tex:Sample.Rmd:1 9 1 1 6 14 1"
    )
    assert matchConcordance(20, obj) == ("Sample.Rmd", "25")


def test_dots_and_capture_and_split():
    def named():
        _dots = Dots(("a", 1), ("b", 2), ("", 3))
        return dots_names(), dots_length(), dots_elt(2)

    assert named() == (["a", "b", ""], 3, 2)
    assert capture_output(lambda: message("hi"), type="message") == ["hi"]
    frame = list2DF({"x": [1, 2, 3], "y": [2, 3, 4]})
    assert frame.columns == {"x": [1, 2, 3], "y": [2, 3, 4]}
    parts = asplit(Array([1, 2, 3, 4, 5, 6], [2, 3]), 1)
    assert [part.data for part in parts] == [[1, 3, 5], [2, 4, 6]]
