"""Checks for the stringi utility, escape, and reverse exports."""

from __future__ import annotations

import pytest

from stringi._na import NA
from stringi.escape import stri_escape_unicode, stri_unescape_unicode
from stringi.reverse import stri_reverse
from stringi.utils import (
    stri_list2matrix,
    stri_na2empty,
    stri_omit_empty,
    stri_omit_empty_na,
    stri_omit_na,
    stri_remove_empty,
    stri_remove_empty_na,
    stri_remove_na,
    stri_replace_na,
)


def test_empty_string_is_empty_and_na_is_not():
    assert stri_remove_empty([""]) == []
    assert stri_remove_empty([NA]) == [NA]
    assert stri_remove_empty(["", NA, "a"]) == [NA, "a"]
    assert stri_remove_empty([" ", ""]) == [" "]
    assert stri_remove_empty(["", NA, "a"], na_empty=True) == ["a"]
    assert stri_remove_empty(["", NA, "a"], na_empty=1) == [NA, "a"]
    assert stri_remove_empty(["", NA, "a"], na_empty=False) == [NA, "a"]


def test_na_helpers_on_the_manual_vector():
    text = ["a", NA, "", "b"]
    assert stri_na2empty(text) == ["a", "", "", "b"]
    assert stri_remove_empty(stri_na2empty(text)) == ["a", "b"]
    assert stri_remove_empty(text) == ["a", NA, "b"]
    assert stri_remove_empty(text, True) == ["a", "b"]
    assert stri_omit_empty(text) == ["a", NA, "b"]
    assert stri_remove_empty_na(text) == ["a", "b"]
    assert stri_omit_empty_na(text) == ["a", "b"]
    assert stri_remove_na(text) == ["a", "", "b"]
    assert stri_omit_na(text) == ["a", "", "b"]
    assert stri_remove_na([NA, NA]) == []
    assert stri_remove_empty(["", ""]) == []
    assert stri_remove_empty([NA, NA], True) == []
    assert stri_na2empty([1, NA]) == ["1", ""]


def test_replace_na():
    assert stri_replace_na(["test", NA]) == ["test", "NA"]
    assert stri_replace_na(["test", NA, ""], "xx") == ["test", "xx", ""]
    assert stri_replace_na(["test", NA], "") == ["test", ""]
    assert stri_replace_na(["a", NA], NA) == ["a", NA]
    with pytest.warns(UserWarning, match="single character string"):
        assert stri_replace_na(["a", NA], ["x", "y"]) == ["a", "x"]


def test_list2matrix_examples():
    even = [["a", "b"], ["c", "d"], ["e", "f"]]
    assert stri_list2matrix(even) == [["a", "c", "e"], ["b", "d", "f"]]
    assert stri_list2matrix(even, byrow=True) == [
        ["a", "b"],
        ["c", "d"],
        ["e", "f"],
    ]
    assert stri_list2matrix(["a", ["b", "c"]]) == [["a", "b"], [NA, "c"]]
    assert stri_list2matrix(["a", ["b", "c"]], fill="") == [["a", "b"], ["", "c"]]
    assert stri_list2matrix(["a", ["b", "c"]], fill="", n_min=5) == [
        ["a", "b"],
        ["", "c"],
        ["", ""],
        ["", ""],
        ["", ""],
    ]
    assert stri_list2matrix(["a", ["b", "c"]], byrow=True, fill="", n_min=5) == [
        ["a", "", "", "", ""],
        ["b", "c", "", "", ""],
    ]
    assert stri_list2matrix([["a", "b"], ["c", "d"]], byrow=False, by_row=True) == [
        ["a", "b"],
        ["c", "d"],
    ]
    assert stri_list2matrix([["a", "b"], ["c", "d"]], byrow=True, by_row=False) == [
        ["a", "c"],
        ["b", "d"],
    ]
    assert stri_list2matrix([[1, 2], [True, False]]) == [
        ["1", "TRUE"],
        ["2", "FALSE"],
    ]
    assert stri_list2matrix([["a", "b"], "c"], n_min=4, fill="*") == [
        ["a", "c"],
        ["b", "*"],
        ["*", "*"],
        ["*", "*"],
    ]


def test_list2matrix_empty_shapes():
    assert stri_list2matrix([]) == []
    assert stri_list2matrix([], n_min=2) == [[], []]
    assert stri_list2matrix([], n_min=2, byrow=True) == []
    assert stri_list2matrix([[], []]) == []
    with pytest.raises(ValueError, match="nonnegative"):
        stri_list2matrix([["a"]], n_min=-1)
    with pytest.raises(ValueError, match="missing values"):
        stri_list2matrix([["a"]], byrow=NA)


def test_escape_matches_probed_rules():
    assert stri_escape_unicode("aą!") == ["a\\u0105!"]
    assert stri_escape_unicode("é©ÿ") == ["\\u00e9\\u00a9\\u00ff"]
    assert stri_escape_unicode("É") == ["\\u00c9"]
    assert stri_escape_unicode("😀") == ["\\U0001f600"]
    assert stri_escape_unicode("\a") == ["\\a"]
    assert stri_escape_unicode("\x1b") == ["\\u001b"]
    assert stri_escape_unicode("\x7f") == ["\\u007f"]
    assert stri_escape_unicode(" ") == [" "]
    assert stri_escape_unicode("\\") == ["\\\\"]
    assert stri_escape_unicode('"') == ['\\"']
    assert stri_escape_unicode("'") == ["\\'"]
    assert stri_escape_unicode(["a", NA, ""]) == ["a", NA, ""]
    ascii_text = "".join(chr(code) for code in range(1, 128))
    escaped = stri_escape_unicode(ascii_text)[0]
    assert escaped.startswith("\\u0001")
    assert "\\a\\b\\t\\n\\v\\f\\r" in escaped
    assert "\\u001b" in escaped
    assert '\\"#$%&\\\'' in escaped
    assert escaped.endswith("\\u007f")
    assert "\\e" not in escaped


def test_unescape_icu_rules():
    assert stri_unescape_unicode("a\\u0105!\\u0032\\n") == ["aą!2\n"]
    assert stri_unescape_unicode("\\a\\b\\t\\n\\v\\f\\r") == ["\a\b\t\n\v\f\r"]
    assert stri_unescape_unicode("\\e\\?") == ["\x1b?"]
    assert stri_unescape_unicode("\\x41\\x4") == ["A\x04"]
    assert stri_unescape_unicode("\\101") == ["A"]
    assert stri_unescape_unicode("\\x{1F600}") == ["😀"]
    assert stri_unescape_unicode("\\U0001F600") == ["😀"]
    assert stri_unescape_unicode("\\q") == ["q"]
    assert stri_unescape_unicode("\\cA") == ["\x01"]
    assert stri_unescape_unicode("\\c") == ["c"]
    assert stri_unescape_unicode("\\uD800\\uDC00") == ["\U00010000"]
    assert stri_unescape_unicode("") == [""]
    assert stri_unescape_unicode(["a", NA, ""]) == ["a", NA, ""]
    assert stri_unescape_unicode("plain") == ["plain"]
    with pytest.warns(UserWarning, match="invalid escape"):
        assert stri_unescape_unicode("\\x{0001F600}") == [NA]
    with pytest.warns(UserWarning, match="invalid escape"):
        assert stri_unescape_unicode("\\") == [NA]
    with pytest.warns(UserWarning, match="invalid escape"):
        assert stri_unescape_unicode("hello\\u12") == [NA]
    with pytest.raises(ValueError, match="embedded nul"):
        stri_unescape_unicode("\\u0000")
    with pytest.raises(ValueError, match="embedded nul"):
        stri_unescape_unicode("\\c ")
    with pytest.raises(ValueError, match="U_INVALID_CHAR_FOUND"):
        stri_unescape_unicode("\\uD800")


def test_reverse_code_points():
    assert stri_reverse(["123", "abc d e f"]) == ["321", "f e d cba"]
    assert stri_reverse("ZXY (ąĄ123$^).") == [".)^$321Ąą( YXZ"]
    assert stri_reverse(["a", NA, "", "😀b"]) == ["a", NA, "", "b😀"]
    assert stri_reverse("e\u0301") == ["\u0301e"]
    assert stri_reverse("a\u0328") == ["\u0328a"]
    assert stri_reverse("a\u0328") != ["a\u0328"]
    assert stri_reverse(123) == ["321"]
