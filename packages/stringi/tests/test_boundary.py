"""Checks for stringi boundary, word, and line-split functions."""

from __future__ import annotations

import warnings

import pytest

from stringi._na import NA, is_na
from stringi.boundary import (
    stri_count_boundaries,
    stri_count_words,
    stri_extract_all_boundaries,
    stri_extract_all_words,
    stri_extract_first_boundaries,
    stri_extract_first_words,
    stri_extract_last_boundaries,
    stri_extract_last_words,
    stri_locate_all_boundaries,
    stri_locate_all_words,
    stri_locate_first_boundaries,
    stri_locate_first_words,
    stri_locate_last_boundaries,
    stri_locate_last_words,
    stri_split_boundaries,
    stri_split_lines,
    stri_split_lines1,
)
from stringi.opts import stri_opts_brkiter


def test_word_skips_drop_the_segment_that_ends_on_that_status():
    text = "123 456 abc."
    assert stri_extract_all_boundaries(text, type="word", skip_word_none=True) == [
        ["123", "456", "abc"]
    ]
    assert stri_extract_all_boundaries(text, type="word", skip_word_number=True) == [
        [" ", " ", "abc", "."]
    ]
    assert stri_extract_all_boundaries(text, type="word", skip_word_letter=True) == [
        ["123", " ", "456", " ", "."]
    ]
    assert stri_count_boundaries("a b", type="word", skip_word_none=False) == [3]
    assert stri_count_words("a b") == [2]
    assert stri_count_words(["a b", NA, "", "NA"]) == [2, NA, 0, 1]
    assert stri_count_words("NA") == [1]
    assert stri_count_words(NA) == [NA]


def test_character_breaks_are_graphemes_and_positions_are_code_points():
    assert stri_count_boundaries("A\u0301", type="character") == [1]
    assert stri_count_boundaries(["abc", NA, "", "a\U0001f600b"], type="character") == [
        3,
        NA,
        0,
        3,
    ]
    assert stri_locate_all_boundaries("a\U0001f600b", type="character") == [
        [[1, 1], [2, 2], [3, 3]]
    ]
    assert stri_locate_all_boundaries(
        "A\u0301\U0001f468\u200d\U0001f469", type="character"
    ) == [[[1, 2], [3, 5]]]
    assert stri_extract_first_boundaries("ab cd", type="character") == ["a"]
    assert stri_extract_last_boundaries("ab cd", type="character") == ["d"]


def test_line_and_sentence_skips_and_locale_keywords():
    assert stri_split_boundaries("hello world\nnext", type="line", skip_line_soft=True) == [
        ["world\n"]
    ]
    assert stri_split_boundaries("hello world\nnext", type="line", skip_line_hard=True) == [
        ["hello ", "next"]
    ]
    assert stri_locate_all_boundaries("hello world\nnext", type="line") == [
        [[1, 6], [7, 12], [13, 16]]
    ]
    assert stri_extract_all_boundaries(
        "Hello. World\nNext", type="sentence", locale="en_US", skip_sentence_sep=True
    ) == [["Hello. "]]
    assert stri_extract_all_boundaries(
        "Hello. World\nNext", type="sentence", locale="en_US", skip_sentence_term=True
    ) == [["World\n", "Next"]]
    text = "Mr. Jones and Mrs. Brown are very happy. So am I, Prof. Smith."
    assert stri_split_boundaries(text, type="sentence", locale="en_US@ss=standard") == [
        ["Mr. Jones and Mrs. Brown are very happy. ", "So am I, Prof. Smith."]
    ]
    assert stri_count_boundaries("ab cd", type="w") == [3]
    assert stri_count_boundaries("ab", type="c") == [2]
    assert stri_count_boundaries("hello world") == [2]


def test_locale_sensitive_words_warn_when_the_bundle_is_root():
    with pytest.warns(UserWarning, match="root or the default locale"):
        assert stri_extract_all_words("ฉันกินข้าว", locale="th") == [["ฉัน", "กิน", "ข้าว"]]
    assert stri_extract_all_words("私は日本語を話します", locale="ja") == [
        ["私", "は", "日本語", "を", "話", "し", "ます"]
    ]
    assert stri_extract_all_boundaries(
        "カタカナと漢字", type="word", locale="ja", skip_word_ideo=True
    ) == [[NA]]
    assert stri_extract_all_boundaries(
        "カタカナと漢字", type="word", locale="ja", skip_word_kana=True
    ) == [["カタカナ", "と", "漢字"]]
    with pytest.warns(UserWarning, match="root or the default locale"):
        assert stri_count_words("Ala ma kota", locale="pl") == [3]
    assert stri_count_words("hello world", locale="root") == [2]
    assert stri_count_words("hello world", locale="C") == [2]
    assert stri_count_words("a b", locale="") == [2]
    with pytest.warns(UserWarning, match="root or the default locale"):
        assert stri_count_words("hello", locale="zzz") == [1]
    with pytest.raises(ValueError, match="U_ILLEGAL_ARGUMENT_ERROR"):
        stri_count_words("a b", locale="not a locale !!!")


def test_extract_and_locate_word_edges():
    assert stri_extract_all_words("stringi: THE string processing package 123.48...") == [
        ["stringi", "THE", "string", "processing", "package", "123.48"]
    ]
    assert stri_extract_all_words("above-mentioned") == [["above", "mentioned"]]
    assert stri_extract_first_words(["hello world", "", NA, "  x"]) == ["hello", NA, NA, "x"]
    assert stri_extract_last_words(["hello world", "", NA, "  x", "hello "]) == [
        "world",
        NA,
        NA,
        "x",
        "hello",
    ]
    assert stri_locate_all_words("a\U0001f600bc def", get_length=True) == [
        [[1, 1], [3, 2], [6, 3]]
    ]
    assert stri_locate_first_words("a\U0001f600bc def", get_length=True) == [[1, 1]]
    assert stri_locate_last_words("a\U0001f600bc def", get_length=True) == [[6, 3]]
    assert stri_locate_last_words(["hello ", "hello world", "..."]) == [
        [1, 5],
        [7, 11],
        [NA, NA],
    ]
    assert stri_locate_all_words("...", get_length=True) == [[[-1, -1]]]
    assert stri_locate_all_words("...", omit_no_match=True, get_length=True) == [[]]
    assert stri_locate_first_boundaries("", get_length=True) == [[-1, -1]]
    assert stri_locate_first_boundaries(NA, get_length=True, type="character") == [[NA, NA]]
    assert stri_locate_all_boundaries("", omit_no_match=True) == [[]]
    assert stri_extract_all_words(["...", NA], omit_no_match=True) == [[], [NA]]
    assert stri_extract_all_words(["a b", "c"], simplify=True) == [["a", "b"], ["c", ""]]
    assert stri_extract_all_words(["a b", "c"], simplify=NA) == [["a", "b"], ["c", NA]]


def test_split_boundaries_keeps_the_remainder_unless_tokens_only():
    assert stri_split_boundaries(
        "hello world foo", type="word", skip_word_none=True, n=2
    ) == [["hello", "world foo"]]
    assert stri_split_boundaries(
        "hello world foo", type="word", skip_word_none=True, n=2, tokens_only=True
    ) == [["hello", "world"]]
    assert stri_split_boundaries(
        "one two three four", type="word", skip_word_none=True, n=3
    ) == [["one", "two", "three four"]]
    assert stri_split_boundaries("abcd", n=1, type="character") == [["abcd"]]
    assert stri_split_boundaries("abcd", n=1, tokens_only=True, type="character") == [["a"]]
    assert stri_split_boundaries("abcd", n=2.9, type="character") == [["a", "bcd"]]
    assert stri_split_boundaries("abcd", n=0.2, type="character") == [[]]
    assert stri_split_boundaries("") == [[]]
    assert stri_split_boundaries("abc", n=0, type="character") == [[]]
    assert stri_split_boundaries(["ab", "cd"], n=[1, NA], type="character") == [["ab"], [NA]]
    assert stri_split_boundaries(["ab", "c"], n=3, type="character", simplify=True) == [
        ["a", "b", ""],
        ["c", "", ""],
    ]
    assert stri_split_boundaries(["ab", "c"], n=3, type="character", simplify=NA) == [
        ["a", "b", NA],
        ["c", NA, NA],
    ]
    with pytest.warns(UserWarning, match="not a multiple"):
        assert stri_split_boundaries(["ab", "cd", "ef"], n=[1, 2], type="character") == [
            ["ab"],
            ["c", "d"],
            ["ef"],
        ]
    with pytest.raises(ValueError, match="value too large"):
        stri_split_boundaries("a", n=2147483646, type="character")
    assert stri_split_boundaries("hello world") == [["hello ", "world"]]
    assert stri_count_boundaries(
        "a b", opts_brkiter=stri_opts_brkiter(type="word", skip_word_none=True)
    ) == [2]


def test_split_lines_and_lines1_trailing_empty_field():
    assert stri_split_lines("a\n") == [["a", ""]]
    assert stri_split_lines1("a\n") == ["a"]
    assert stri_split_lines("a\n\n") == [["a", "", ""]]
    assert stri_split_lines1("a\n\n") == ["a", ""]
    assert stri_split_lines("\r\n") == [["", ""]]
    assert stri_split_lines1("\r\n") == [""]
    assert stri_split_lines("") == [[""]]
    assert stri_split_lines1("") == [""]
    assert stri_split_lines(NA) == [[NA]]
    assert stri_split_lines1(NA) == [NA]
    assert is_na(stri_split_lines1(NA)[0])
    assert stri_split_lines1("a\rb\r") == ["a", "b"]
    assert stri_split_lines1("a\n\rb") == ["a", "", "b"]
    assert stri_split_lines1("\n") == [""]
    assert stri_split_lines("\n") == [["", ""]]
    assert stri_split_lines1("a\vb\fc\u0085d\u2028e\u2029f") == ["a", "b", "c", "d", "e", "f"]
    assert stri_split_lines("a\n\n", omit_empty=True) == [["a"]]
    assert stri_split_lines("a\n\n", omit_empty=NA) == [["a"]]
    assert stri_split_lines("\n", omit_empty=True) == [[]]
    assert stri_split_lines(["a\n\nb", "c\n", "\n", "a\n"], omit_empty=[True, False, NA, NA]) == [
        ["a", "b"],
        ["c", ""],
        [],
        ["a"],
    ]
    assert stri_split_boundaries("ab\ncd\r\nef", type="line") == [["ab\n", "cd\r\n", "ef"]]
    with pytest.raises(ValueError, match="non-empty vector"):
        stri_split_lines1(None)
    with pytest.raises(ValueError, match="non-empty vector"):
        stri_split_lines1([])
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        assert stri_split_lines1(["a\n", "b\n"]) == ["a"]
    assert any("only the first element is used" in str(item.message) for item in caught)


def test_option_errors_match_the_installed_function():
    with pytest.raises(ValueError, match="U_BRK_RULE_SYNTAX"):
        stri_count_boundaries("ab", type="nope")
    with pytest.raises(TypeError, match='formal argument "type" matched by multiple'):
        stri_count_boundaries("a", opts_brkiter={"type": "word"}, type="sentence")
    with pytest.raises(ValueError, match="skip_word_none"):
        stri_count_boundaries("a", type="word", skip_word_none=NA)
    with pytest.raises(ValueError, match="get_length"):
        stri_locate_all_words("a", get_length=NA)
    with pytest.raises(ValueError, match="omit_no_match"):
        stri_extract_all_words("a", omit_no_match=NA)
    with pytest.raises(ValueError, match="incorrect option for `type`"):
        stri_count_boundaries("a", opts_brkiter={"type": NA})
    assert stri_count_boundaries("a", opts_brkiter={"type": ""}) == [1]
    assert stri_count_boundaries(None) == []
    assert stri_extract_all_boundaries("", omit_no_match=True) == [[]]
    assert stri_extract_all_boundaries("") == [[NA]]
