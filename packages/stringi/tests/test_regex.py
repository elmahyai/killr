"""Regex search checked against stringi 1.8.9."""

import json
import re
import warnings

import pytest

from stringi._na import NA
from stringi.regex import (
    stri_count_regex,
    stri_detect_regex,
    stri_extract_all_regex,
    stri_extract_first_regex,
    stri_extract_last_regex,
    stri_locate_all_regex,
    stri_locate_first_regex,
    stri_locate_last_regex,
    stri_match,
    stri_match_all,
    stri_match_all_regex,
    stri_match_first,
    stri_match_first_regex,
    stri_match_last,
    stri_match_last_regex,
    stri_replace_all_regex,
    stri_replace_first_regex,
    stri_replace_last_regex,
    stri_replace_rstr,
    stri_split_regex,
    stri_subset_regex,
)

s = "Lorem ipsum dolor sit amet, consectetur adipisicing elit."


def enc(value):
    if value is NA:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, list):
        return "[" + ",".join(enc(item) for item in value) + "]"
    raise TypeError(type(value))


CASES = {
    'count1': (stri_count_regex(s, "(s|el)it"), '[2]'),
    'count2': (stri_count_regex("bab baab baaab", ["b.*?b", "b.b"]), '[3,2]'),
    'count3': (stri_count_regex(["", NA, "Éé", "aaaa"], [".*", "a", "é", "aa"]), '[1,null,1,2]'),
    'count4': (stri_count_regex("aAaA", "aa", case_insensitive=True), '[2]'),
    'count5': (stri_count_regex("ß", "SS", case_insensitive=True), '[1]'),
    'count6': (stri_count_regex("", [".*", "a", "^$"]), '[1,0,1]'),
    'count7': (stri_count_regex("a.b", ".", literal=True), '[1]'),
    'count8': (stri_count_regex("a\nb\nc", "^.", multiline=True), '[3]'),
    'count9': (stri_count_regex(["a\rb", "a\nb"], "^b", multiline=True, unix_lines=True), '[0,1]'),
    'count10': (stri_count_regex("ab", "a #x\n b", comments=True), '[1]'),
    'detect1': (stri_detect_regex(["stringi R", "R STRINGI", "123"], "R."), '[false,true,false]'),
    'detect2': (stri_detect_regex("stringi", "STRING.", case_insensitive=True), '[true]'),
    'detect3': (stri_detect_regex(["abc", "def", "123", "ghi", "456", "789", "jkl"], "^[0-9]+$", max_count=2), '[false,false,true,false,true,null,null]'),
    'detect4': (stri_detect_regex(["abc", "def", "123", "ghi", "456", "789", "jkl"], "^[0-9]+$", negate=True, max_count=3), '[true,true,false,true,null,null,null]'),
    'detect5': (stri_detect_regex(["a", "1", "b", "2", "c", "3"], ["[0-9]", "x"], max_count=1), '[false,false,false,false,false,false]'),
    'detect6': (stri_detect_regex(["", "a"], [".*", "a"], negate=True), '[false,false]'),
    'detect7': (stri_detect_regex("a\nb", "a.b", dotall=True), '[true]'),
    'exf': (stri_extract_first_regex("XaaaaX", ["\\p{Ll}", "\\p{Ll}+", "\\p{Ll}{2,3}", "\\p{Ll}{2,3}?"]), '["a","aaaa","aaa","aa"]'),
    'exl': (stri_extract_last_regex(["agAGA", "ababa"], ["aga", "aba"], case_insensitive=True), '["agA","aba"]'),
    'exa': (stri_extract_all_regex("XaaaaX", ["\\p{Ll}", "\\p{Ll}+"]), '[["a","a","a","a"],["aaaa"]]'),
    'exa2': (stri_extract_all_regex(["abc", "zzz", NA, ""], "a+", omit_no_match=True), '[["a"],[],[null],[]]'),
    'exa3': (stri_extract_all_regex("XaaaaX", ["\\p{Ll}", "\\p{Ll}+"], simplify=True), '[["a","a","a","a"],["aaaa","","",""]]'),
    'exa4': (stri_extract_all_regex("XaaaaX", ["\\p{Ll}", "\\p{Ll}+"], simplify=NA), '[["a","a","a","a"],["aaaa",null,null,null]]'),
    'loczw': (stri_locate_all_regex("ACAGAGACTTTAGATAGAGAAGA", "(?=AGA)"), '[[[3,2],[5,4],[12,11],[16,15],[18,17],[21,20]]]'),
    'locem': (stri_locate_all_regex("a😀b😀c", "😀"), '[[[2,2],[4,4]]]'),
    'loclen': (stri_locate_first_regex(["yes yes", "no", NA, ""], "yes", get_length=True), '[[1,3],[-1,-1],[null,null],[-1,-1]]'),
    'loclast': (stri_locate_last_regex("ababa", "aba"), '[[1,3]]'),
    'loccap': (stri_locate_all_regex(["breakfast=eggs;lunch=pizza", "no food"], "(?<when>\\w+)=(?<what>\\w+)", capture_groups=True), '[[[1,14],[16,26]],[[null,null]]]'),
    'locfcap': (stri_locate_first_regex(["a1b", "xx", NA], "(?<d>\\d)?x?", capture_groups=True, get_length=True), '[[1,0],[1,1],[null,null]]'),
    'mf': (stri_match_first_regex(["abcd", ":abcd", ":abcd:"], "^(:)?([^:]*)(:)?$"), '[["abcd",null,"abcd",null],[":abcd",":","abcd",null],[":abcd:",":","abcd",":"]]'),
    'mfcg': (stri_match_first_regex(["abcd", ":abcd", ":abcd:"], "^(:)?([^:]*)(:)?$", cg_missing=""), '[["abcd","","abcd",""],[":abcd",":","abcd",""],[":abcd:",":","abcd",":"]]'),
    'ma': (stri_match_all_regex(["breakfast=eggs;lunch=pizza", "no food"], "(?<when>\\w+)=(?<what>\\w+)"), '[[["breakfast=eggs","breakfast","eggs"],["lunch=pizza","lunch","pizza"]],[[null,null,null]]]'),
    'maom': (stri_match_all_regex(["breakfast=eggs", "no"], "(\\w+)=(\\w+)", omit_no_match=True), '[[["breakfast=eggs","breakfast","eggs"]],[]]'),
    'ml': (stri_match_last_regex(["breakfast=eggs;lunch=pizza", "no"], "(\\w+)=(\\w+)"), '[["lunch=pizza","lunch","pizza"],[null,null,null]]'),
    'mna': (stri_match_first_regex([NA, "ab"], "(a)", cg_missing=""), '[[null,null],["a","a"]]'),
    'mmix': (stri_match_first_regex(["ab", "no"], ["(a)", "(a)(b)(c)"], cg_missing=""), '[["a","a",null,null],["","","",""]]'),
    'mempty': (stri_match_first_regex([], ["(a)", "(b)(c)"]), '[]'),
    'rep1': (stri_replace_all_regex("123|456|789", "(\\p{N}).(\\p{N})", "$2-$1"), '["3-1|6-4|9-7"]'),
    'rep2': (stri_replace_all_regex("words 123 and numbers 456", "(?<numbers>[0-9]+)", "!${numbers}!"), '["words !123! and numbers !456!"]'),
    'rep3': (stri_replace_last_regex("agAGA", "aga", "*", case_insensitive=True), '["*GA"]'),
    'rep4': (stri_replace_all_regex(["abc", "def", "zzz"], "b|e", NA), '[null,null,"zzz"]'),
    'rep5': (stri_replace_all_regex("ab", "(a)", "\\1"), '["1b"]'),
    'rep6': (stri_replace_all_regex("a", "a", "\\$"), '["$"]'),
    'rep7': (stri_replace_all_regex("", ".*", "Z"), '["Z"]'),
    'rep8': (stri_replace_all_regex("The quicker brown fox jumped over the lazy dog.", ["\\b" + p + "\\b" for p in ["quick", "brown", "fox"]], ["slow", "black", "bear"], vectorize_all=False), '["The quicker black bear jumped over the lazy dog."]'),
    'rep9': (stri_replace_first_regex(["abc", "zzz"], "b", NA), '[null,"zzz"]'),
    'rep10': (stri_replace_all_regex("a" * 10, "(a)" * 10, "$10"), '["a"]'),
    'rep11': (stri_replace_all_regex("ab", "(a)(b)", "$10"), '["a0"]'),
    'rstr': (stri_replace_rstr(["$", "\\1", "\\12", "\\a", "a\\", "\\\\", "\\$", NA, "", "x$y\\1z", "\\0"]), '["\\\\$","$1","$1\\\\2","a","a","\\\\\\\\","\\\\$",null,"","x\\\\$y$1z","0"]'),
    'spl': (stri_split_regex(["ab,c", "d,ef  ,  g", ",  h", ""], "\\p{WHITE_SPACE}*,\\p{WHITE_SPACE}*", omit_empty=NA, simplify=True), '[["ab","c",""],["d","ef","g"],[null,"h",""],[null,"",""]]'),
    'spl2': (stri_split_regex("a,b,c,d", ",", n=2), '[["a","b,c,d"]]'),
    'spl3': (stri_split_regex("a,b,c,d", ",", n=2, tokens_only=True), '[["a","b"]]'),
    'spl4': (stri_split_regex(["a,b", "c"], ",", n=4, simplify=True), '[["a","b","",""],["c","","",""]]'),
    'sub': (stri_subset_regex(["stringi R", "123", "ID456", "", NA], "^[0-9]+$"), '["123",null]'),
    'sub2': (stri_subset_regex(["stringi R", "123", NA, ""], "^[0-9]+$", omit_na=True), '["123"]'),
    'sub3': (stri_subset_regex(["ab", "12", NA], "[0-9]", negate=True), '["ab",null]'),
    'sub4': (stri_subset_regex(["", "a"], ".*"), '["","a"]'),
    'alias': (stri_match_all("a1b2", "(\\d)"), '[[["1","1"],["2","2"]]]'),
    'mode': (stri_match("ab12", "(\\d+)", mode="last"), '[["12","12"]]'),
    'modep': (stri_match("ab12", "(\\d+)", mode="f"), '[["12","12"]]'),
    'uword': (stri_extract_all_regex("café xx", "\\b\\w+\\b", uword=True), '[["café","xx"]]'),
    'emptyrep': (lambda: stri_replace_all_regex(["a", "b"], ["a", ""], "Z", vectorize_all=False), '[null,null]'),
    'locempty': (stri_locate_all_regex("", "a*"), '[[[1,0]]]'),
    'exempty': (stri_extract_all_regex("", "a*"), '[[""]]'),
    'ciuni': (stri_count_regex("Éé", "é", case_insensitive=True), '[2]'),
    'look': (stri_locate_all_regex("abc", "(?<=a)b"), '[[[2,2]]]'),
    'overlap': (stri_match_all_regex("ACAGAGACTTTAGATAGAGAAGA", "(?=(([ACGT])[ACGT]\\2))"), '[[["","ACA","A"],["","AGA","A"],["","GAG","G"],["","AGA","A"],["","TTT","T"],["","AGA","A"],["","ATA","A"],["","AGA","A"],["","GAG","G"],["","AGA","A"],["","AGA","A"]]]'),
}


ERRORS = {
    "bad": (
        lambda: stri_count_regex("a", "("),
        "Incorrectly nested parentheses in regex pattern. (U_REGEX_MISMATCHED_PAREN, context=`(`)",
    ),
    "badesc": (
        lambda: stri_count_regex("a", "\\q", error_on_unknown_escapes=True),
        "Unrecognized backslash escape sequence in pattern. (U_REGEX_BAD_ESCAPE_SEQUENCE, context=`\\q`)",
    ),
    "dollar": (
        lambda: stri_replace_all_regex("a", "a", "$"),
        "Invalid capture group name. (U_REGEX_INVALID_CAPTURE_GROUP_NAME)",
    ),
    "time": (
        lambda: stri_count_regex("a" * 30, "(a+)+b", time_limit=1),
        "Maximum allowed match time exceeded. (U_REGEX_TIME_OUT)",
    ),
    "stack": (
        lambda: stri_count_regex("a" * 40, "(a+)+b", stack_limit=50),
        "Regular expression backtrack stack overflow. (U_REGEX_STACK_OVERFLOW)",
    ),
}


@pytest.mark.parametrize("name", list(CASES))
def test_against_r(name):
    value, payload = CASES[name]
    if callable(value):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            value = value()
    assert enc(value) == payload


@pytest.mark.parametrize("name", list(ERRORS))
def test_errors(name):
    call, message = ERRORS[name]
    with pytest.raises(ValueError, match=re.escape(message)):
        call()


def test_aliases_are_the_regex_functions():
    assert stri_match_all is stri_match_all_regex
    assert stri_match_first is stri_match_first_regex
    assert stri_match_last is stri_match_last_regex


def test_named_capture_positions_are_code_points():
    found = stri_locate_all_regex(
        ["breakfast=eggs;lunch=pizza", "no"],
        r"(?<when>\w+)=(?<what>\w+)",
        capture_groups=True,
    )
    assert list(found[0]) == [[1, 14], [16, 26]]
    assert found[0].capture_groups.names == ["when", "what"]
    assert list(found[0].capture_groups[0]) == [[1, 9], [16, 20]]
    assert list(found[0].capture_groups[1]) == [[11, 14], [22, 26]]
    first = stri_locate_first_regex(
        ["a1b", "xx", NA],
        r"(?<d>\d)?x?",
        capture_groups=True,
        get_length=True,
    )
    assert list(first) == [[1, 0], [1, 1], [NA, NA]]
    assert first.capture_groups.names == ["d"]
    assert list(first.capture_groups[0]) == [[-1, -1], [-1, -1], [NA, NA]]
    unnamed = stri_locate_first_regex(
        ["a1", "b2"],
        [r"(?<d>\d)", r"(?<e>\d)"],
        capture_groups=True,
    )
    assert unnamed.capture_groups.names is None


def test_match_colnames_and_empty_input():
    matched = stri_match_first_regex("breakfast=eggs", r"(?<when>\w+)=(?<what>\w+)")
    assert matched.colnames == ["", "when", "what"]
    assert matched.ncol == 3
    empty = stri_match_first_regex([], r"(?<a>x)(?<b>y)")
    assert list(empty) == []
    assert empty.colnames == ["", "a", "b"]
    assert empty.ncol == 3
    last = stri_match_last_regex([], r"(?<a>x)")
    assert last.colnames == ["", "a"]
    assert last.ncol == 2
    mixed = stri_match_first_regex([], ["(a)", "(b)(c)"])
    assert mixed.colnames is None
    missed = stri_match_all_regex("no", r"(?<a>z)", omit_no_match=True)
    assert list(missed[0]) == []
    assert missed[0].colnames == ["", "a"]
    assert missed[0].ncol == 2


def test_emoji_positions_are_code_points():
    assert stri_locate_all_regex("a😀b😀c", "😀") == [[[2, 2], [4, 4]]]


def test_empty_pattern_warns_and_is_missing():
    with pytest.warns(UserWarning, match="empty search patterns are not supported"):
        assert stri_count_regex("a", "") == [NA]


def test_unknown_option_is_ignored():
    with pytest.warns(UserWarning, match="incorrect opts_regex setting: 'foo'; ignoring"):
        assert stri_count_regex("A", "a", opts_regex={"case_insensitive": True, "foo": 1}) == [1]


def test_opts_must_be_a_dict():
    with pytest.raises(TypeError, match="argument `opts_regex` should be a list"):
        stri_count_regex("a", "a", opts_regex="no")


def test_duplicate_option_is_rejected():
    with pytest.raises(TypeError, match='formal argument "case_insensitive" matched by multiple actual arguments'):
        stri_count_regex("A", "a", opts_regex={"case_insensitive": True}, case_insensitive=True)


def test_replace_vector_length_and_split_n():
    with pytest.raises(ValueError, match="vector length not consistent with other arguments"):
        stri_replace_all_regex("ab", ["a"], ["Z", "Y"], vectorize_all=False)
    with pytest.raises(ValueError, match="incorrect argument `n`; value too large"):
        stri_split_regex("ab", ",", n=2147483646)
    with pytest.raises(ValueError, match="vector length not consistent with other arguments"):
        stri_subset_regex(["a"], ["a", "b"])


def test_match_mode_prefix_and_rejection():
    assert stri_match("ab12", r"(\d+)", mode="f") == [["12", "12"]]
    with pytest.raises(ValueError, match="should be one of"):
        stri_match("ab12", r"(\d+)", mode="nope")


def test_timeout_does_not_poison_later_matches():
    with pytest.raises(ValueError, match="U_REGEX_TIME_OUT"):
        stri_count_regex("a" * 30, "(a+)+b", time_limit=1)
    assert stri_count_regex("ababa", "aba") == [1]


def test_replacement_backreferences():
    assert stri_replace_all_regex("123|456|789", r"(\p{N}).(\p{N})", "$2-$1") == ["3-1|6-4|9-7"]
    assert stri_replace_rstr(["\\1", "\\12", "$"]) == ["$1", "$1\\2", "\\$"]

