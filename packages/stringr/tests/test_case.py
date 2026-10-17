"""Checks for the stringr case, trim, pad, wrap, trunc, and word wrappers."""

from __future__ import annotations

import pytest
from rlang import Named
from stringi._na import NA

from stringr._size import RecycleError
from stringr.case import (
    str_to_camel,
    str_to_kebab,
    str_to_lower,
    str_to_sentence,
    str_to_snake,
    str_to_title,
    str_to_upper,
)
from stringr.pad import str_pad
from stringr.pattern import boundary, coll, fixed
from stringr.trim import str_squish, str_trim
from stringr.trunc import str_trunc
from stringr.word import word
from stringr.wrap import str_wrap


def test_case_defaults_are_english_and_return_lists():
    assert str_to_upper("The quick brown dog") == ["THE QUICK BROWN DOG"]
    assert str_to_lower("The quick brown dog") == ["the quick brown dog"]
    assert str_to_title("The quick brown dog") == ["The Quick Brown Dog"]
    assert str_to_sentence("the quick brown dog") == ["The quick brown dog"]
    assert str_to_upper("i") == ["I"]
    assert str_to_upper("i", "tr") == ["İ"]
    assert str_to_lower("I", "tr") == ["ı"]
    assert str_to_upper(["A", NA, "", "ß"]) == ["A", NA, "", "SS"]
    assert str_to_sentence("a Test. a second.") == ["A test. a second."]
    assert str_to_title("istanbul", "tr") == ["İstanbul"]
    assert str_to_upper([]) == []


def test_programming_case_follows_the_word_breaks():
    assert str_to_camel("my_variable") == ["myVariable"]
    assert str_to_camel("my$variable") == ["myVariable"]
    assert str_to_camel(" my    variable  ") == ["myVariable"]
    assert str_to_camel("my-variable", first_upper=True) == ["MyVariable"]
    assert str_to_kebab(
        ["myVariable", "MyVariable", "1MyVariable1", "testABCTest", "IlÉtaitUneFois"]
    ) == ["my-variable", "my-variable", "1-my-variable-1", "test-abc-test", "il-était-une-fois"]
    assert str_to_snake("HTML") == ["html"]
    assert str_to_snake("a123b") == ["a_123_b"]
    assert str_to_camel([NA, ""]) == [NA, ""]
    assert str_to_snake([]) == []
    named = Named(["MyVar"], ["A"])
    assert str_to_snake(named) == ["my_var"]
    assert str_to_snake(named).names == ["A"]


def test_case_rejects_a_bad_locale_and_a_non_character_camel_input():
    with pytest.raises(ValueError):
        str_to_upper("i", None)
    with pytest.raises(ValueError):
        str_to_camel(1)


def test_trim_and_squish():
    assert str_trim("  String with trailing and leading white space\t") == [
        "String with trailing and leading white space"
    ]
    assert str_trim("\n\nString with trailing and leading white space\n\n") == [
        "String with trailing and leading white space"
    ]
    assert str_trim(" abc ", "left") == ["abc "]
    assert str_trim(" abc ", "right") == [" abc"]
    assert str_trim("\u00a0ab\u00a0") == ["ab"]
    assert str_trim(["abc", NA]) == ["abc", NA]
    assert str_squish("ab\t\tc\t") == ["ab c"]
    assert str_squish("  String with trailing,  middle, and leading white space\t") == [
        "String with trailing, middle, and leading white space"
    ]
    assert str_trim([]) == []
    with pytest.raises(ValueError):
        str_trim(" abc ", "l")


def test_pad_recycles_with_the_common_size_and_uses_width():
    assert str_pad("had", 10, "left") == ["       had"]
    assert str_pad("had", 10, "right") == ["had       "]
    assert str_pad("had", 10, "both") == ["   had    "]
    assert str_pad(["a", "abc", "abcdef"], 10) == ["         a", "       abc", "    abcdef"]
    assert str_pad("a", [5, 10, 20]) == ["    a", "         a", "                   a"]
    assert str_pad("hadley", 3) == ["hadley"]
    assert str_pad("\u4e2d", 6, "both") == ["  \u4e2d  "]
    assert str_pad("\u4e2d", 5, "both", use_width=False) == ["  \u4e2d  "]
    assert str_pad(["a", NA], [3, NA]) == ["  a", NA]
    assert str_pad([], 10) == []
    named = Named(["3", "2"], ["C", "B"])
    assert str_pad(named, 2).names == ["C", "B"]
    assert getattr(str_pad(Named(["a"], ["A"]), [3, 4]), "names", None) is None
    with pytest.raises(RecycleError):
        str_pad(["a", "b"], [1, 2, 3])
    with pytest.raises(ValueError):
        str_pad("a", 3, "b")


def test_wrap_joins_lines_and_treats_a_non_positive_width_as_one():
    assert str_wrap("") == [""]
    assert str_wrap(" ") == [""]
    assert str_wrap("  a  ") == ["a"]
    assert str_wrap("a b c d e", 0) == ["a\nb\nc\nd\ne"]
    assert str_wrap("a/b", width=0, whitespace_only=True) == ["a/b"]
    assert str_wrap("a/b", width=0, whitespace_only=False) == ["a/\nb"]
    assert str_wrap(["hello world there", NA], width=8) == ["hello\nworld\nthere", NA]
    assert str_wrap("one two three four", width=10, indent=2, exdent=1) == [
        "  one two\n three\n four"
    ]
    assert str_wrap([]) == []
    named = Named(["hello world", "x"], ["A", "B"])
    assert str_wrap(named, 5).names == ["A", "B"]


def test_trunc_sides_and_short_ellipsis():
    text = "This string is moderately long"
    assert str_trunc(text, 20, "right") == ["This string is mo..."]
    assert str_trunc(text, 20, "left") == ["...s moderately long"]
    assert str_trunc(text, 20, "center") == ["This stri...ely long"]
    assert str_trunc(text, 3, "center") == ["..."]
    assert str_trunc(text, 4, "center") == ["T..."]
    assert str_trunc(text, 5, "center") == ["T...g"]
    assert str_trunc(["foobar", NA], 5) == ["fo...", NA]
    assert str_trunc(["abcd", "abcde", "abcdef"], 5) == ["abcd", "abcde", "ab..."]
    assert str_trunc(["", "a", "aa", "aaa", "aaaa", "aaaaaaa"], 4, "center", "..") == [
        "",
        "a",
        "aa",
        "aaa",
        "aaaa",
        "a..a",
    ]
    assert str_trunc(["", "a", "aa", "aaa", "aaaa", "aaaaaaa"], 3, "left", "..") == [
        "",
        "a",
        "aa",
        "aaa",
        "..a",
        "..a",
    ]
    assert str_trunc("a\U0001f600bcdef", 5) == ["a\U0001f600..."]
    assert str_trunc([], 4) == []
    with pytest.raises(ValueError):
        str_trunc("foobar", 2)
    with pytest.raises(ValueError):
        str_trunc("abcdef", 4.2)


def test_word_ranges_and_separators():
    sentences = ["Jane saw a cat", "Jane sat down"]
    assert word(sentences, 1) == ["Jane", "Jane"]
    assert word(sentences, 2) == ["saw", "sat"]
    assert word(sentences, -1) == ["cat", "down"]
    assert word(sentences, 2, -1) == ["saw a cat", "sat down"]
    assert word(sentences[0], [1, 2, 3], -1) == ["Jane saw a cat", "saw a cat", "a cat"]
    assert word(sentences[0], 1, [1, 2, 3, 4]) == ["Jane", "Jane saw", "Jane saw a", "Jane saw a cat"]
    assert word("abc.def..123.4568.999", 1, sep=fixed("..")) == ["abc.def"]
    assert word("abc.def..123.4568.999", 2, sep=fixed("..")) == ["123.4568.999"]
    assert word("a b c", 4) == [NA]
    assert word("walk the moon", -5, -1) == ["walk the moon"]
    assert word("a  b", [1, 2, 3]) == ["a", "", "b"]
    assert word("a b", 0) == [NA]
    assert word("", 1) == [""]
    assert word(["a b", NA], 1) == ["a", NA]
    assert word("a b c", NA) == [NA]
    assert word("a-b-c", 2, sep="-") == ["b"]
    assert word("a b c", 2, sep=coll(" ")) == ["b"]
    assert word("Jane saw a cat.", 1, sep=boundary("word")) == [""]
    assert word([]) == []
    named = Named(["hello world"], ["A"])
    assert word(named, [1, 2]).names == ["A", "A"]
    from vctrs import RecycleError as VctrsRecycleError

    with pytest.raises(VctrsRecycleError):
        word(["a b", "c d"], [1, 2, 3])
