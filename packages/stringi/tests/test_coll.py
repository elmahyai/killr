"""Collation search results checked against stringi 1.8.9."""

import json
import warnings

import pytest

from stringi._na import NA
from stringi.coll import (
    stri_count_coll,
    stri_detect_coll,
    stri_endswith_coll,
    stri_extract_all_coll,
    stri_extract_first_coll,
    stri_extract_last_coll,
    stri_locate_all_coll,
    stri_locate_first_coll,
    stri_locate_last_coll,
    stri_replace_all_coll,
    stri_replace_first_coll,
    stri_replace_last_coll,
    stri_split_coll,
    stri_startswith_coll,
    stri_subset_coll,
)
from stringi.opts import stri_opts_collator

DE = {"strength": 1, "locale": "de"}

# JSON captured from Rscript against the installed stringi 1.8.9.
EXPECTED = """
count_aa	[1]
count_primary	[3]
count_tertiary	[1]
count_eszett	[1,1,1]
count_empty_pat	[null]
count_empty_str	[0]
count_na	[null,null]
count_recycle	[1,1,2]
count_text_na	[1]
count_none	[]
detect_posix	[false]
detect_shifted	[true]
detect_tr	[false,true,true,false]
detect_da	[false]
detect_root	[true]
detect_order	[false,null,true,null]
detect_zero	[null,null]
locate_aa	[[[1,2]]]
locate_ss	[[[1,1],[2,2]]]
locate_mark	[[[1,2]]]
locate_auml	[[[1,2],[3,3]]]
locate_emoji	[[[2,2],[4,4]]]
locate_length	[[[1,2],[3,1]]]
locate_empty	[[-1,-1],[-1,-1],[null,null]]
locate_last	[[4,1]]
extract_ss	[["ß"],["ß"]]
extract_first	["Y",null]
extract_last	["ß"]
extract_simplify	[["ß"],[null]]
extract_omit	[["ß"],[]]
replace_all	["X","StraXe","sXs","X"]
replace_first	["Xß"]
replace_last	["ßX"]
replace_each	["YX","bY"]
replace_na_pat	[null,null]
split_de	[["Stra","e"],["","",""],["a","b"]]
split_n	[["a","aßa"]]
split_tokens	[["a","a"]]
split_omit	[["a","b","c","d"],["a","b","c","","d"],["a","b","c",null,"d"]]
start	[true,false,true]
start_from	[true]
start_zero	[false]
end	[true,false,true]
end_to	[true]
subset	["ß","ss",null]
subset_neg	["b"]
subset_na_text	["NA",null]
emoji_span	[[2,2]]
emoji_eszett	[[[3,3]]]
""".strip()


def canon(value):
    if value is NA:
        return None
    if isinstance(value, list):
        return [canon(item) for item in value]
    return value


def cases():
    return {
        "count_aa": stri_count_coll("aaa", "aa"),
        "count_primary": stri_count_coll("aAa", "A", strength=1),
        "count_tertiary": stri_count_coll("aAa", "A", strength=3),
        "count_eszett": stri_count_coll(["ß", "Straße", "sßs"], "ss", **DE),
        "count_empty_pat": stri_count_coll("a", ""),
        "count_empty_str": stri_count_coll("", "a"),
        "count_na": stri_count_coll([NA, "a"], ["a", NA]),
        "count_recycle": stri_count_coll(["ab", "ba", "aa"], ["a", "b"]),
        "count_text_na": stri_count_coll("NA", "N"),
        "count_none": stri_count_coll([], "a"),
        "detect_posix": stri_detect_coll("a", "A", locale="C", strength=1),
        "detect_shifted": stri_detect_coll("a-b", "ab", alternate_shifted=True, strength=1),
        "detect_tr": stri_detect_coll(["I", "i", "İ", "ı"], "i", strength=1, locale="tr"),
        "detect_da": stri_detect_coll("æ", "ae", strength=1, locale="da"),
        "detect_root": stri_detect_coll("æ", "ae", strength=1, locale="root"),
        "detect_order": stri_detect_coll(["xx", "yy", "yes", "zz"], ["yes", "yy"], max_count=1),
        "detect_zero": stri_detect_coll(["a", "b"], "a", max_count=0),
        "locate_aa": stri_locate_all_coll("aaa", "aa"),
        "locate_ss": stri_locate_all_coll("ßß", "ss", **DE),
        "locate_mark": stri_locate_all_coll("a\u0308", "a", strength=1),
        "locate_auml": stri_locate_all_coll("a\u0308a", "ä", strength=1, locale="de"),
        "locate_emoji": stri_locate_all_coll("a\U0001f600b\U0001f600", "\U0001f600"),
        "locate_length": stri_locate_all_coll("a\u0308a", "a", get_length=True, strength=1),
        "locate_empty": stri_locate_first_coll(["", "x", NA], "a", get_length=True),
        "locate_last": stri_locate_last_coll("aßaßa", "ss", get_length=True, **DE),
        "extract_ss": stri_extract_all_coll(["ß", "Straße"], "ss", **DE),
        "extract_first": stri_extract_first_coll(["Yyý", "AAA"], "y", strength=2, locale="sk_SK"),
        "extract_last": stri_extract_last_coll("aßa", "ss", **DE),
        "extract_simplify": stri_extract_all_coll(["aßa", "x"], "ss", simplify=True, **DE),
        "extract_omit": stri_extract_all_coll(["ß", "x"], "ss", omit_no_match=True, **DE),
        "replace_all": stri_replace_all_coll(["ß", "Straße", "sßs", "ss"], "ss", "X", **DE),
        "replace_first": stri_replace_first_coll("ßß", "ss", "X", **DE),
        "replace_last": stri_replace_last_coll("ßß", "ss", "X", **DE),
        "replace_each": stri_replace_all_coll(
            ["aß", "ba"], ["ss", "a"], ["X", "Y"], vectorize_all=False, **DE
        ),
        "replace_na_pat": stri_replace_all_coll(
            ["ab", "cd"], ["a", NA], ["X", "Y"], vectorize_all=False
        ),
        "split_de": stri_split_coll(
            ["Straße", "ßß", "a-b"], ["ss", "ss", "-"], opts_collator={"strength": 1, "locale": "de"}
        ),
        "split_n": stri_split_coll("aßaßa", "ss", n=2, **DE),
        "split_tokens": stri_split_coll("aßaßa", "ss", n=2, tokens_only=True, **DE),
        "split_omit": stri_split_coll("a_b_c__d", "_", omit_empty=[True, False, NA]),
        "start": stri_startswith_coll(["ßx", "xß", "ß"], "ss", **DE),
        "start_from": stri_startswith_coll("xß", "ss", from_=2, **DE),
        "start_zero": stri_startswith_coll("xß", "ss", from_=0, **DE),
        "end": stri_endswith_coll(["xß", "ßx", "aß"], "ss", **DE),
        "end_to": stri_endswith_coll("ßabc", "ss", to=1, **DE),
        "subset": stri_subset_coll(["ß", "ss", "a", NA], "ss", **DE),
        "subset_neg": stri_subset_coll(["ß", "b"], "ss", negate=True, **DE),
        "subset_na_text": stri_subset_coll(["NA", NA, ""], "N"),
        "emoji_span": stri_locate_first_coll("a\U0001f600b", "\U0001f600"),
        "emoji_eszett": stri_locate_all_coll("a\U0001f600ßb", "ss", **DE),
    }


def test_battery_matches_installed_stringi():
    expected = {}
    for line in EXPECTED.splitlines():
        name, payload = line.split("\t", 1)
        expected[name] = json.loads(payload)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        got = cases()
    assert set(got) == set(expected)
    for name, want in expected.items():
        assert canon(got[name]) == want, name


def test_text_na_is_not_missing():
    assert stri_count_coll("NA", "N") == [1]
    assert stri_count_coll(NA, "N") == [NA]


def test_empty_pattern_warns():
    with pytest.warns(UserWarning, match="empty search patterns are not supported"):
        assert stri_count_coll("abc", "") == [NA]


def test_normalisation_key_is_not_read():
    with pytest.warns(UserWarning, match="normalisation"):
        assert stri_detect_coll("é", "e\u0301", opts_collator={"normalisation": True}) == [True]


def test_keyword_normalisation_is_stored_as_normalization():
    assert stri_detect_coll("é", "e\u0301", normalisation=True) == [True]


def test_opts_builder_round_trip():
    opts = stri_opts_collator(strength=1, locale="de")
    assert stri_count_coll("ß", "ss", opts_collator=opts) == [1]


def test_duplicate_setting_is_an_error():
    with pytest.raises(TypeError, match="multiple actual arguments"):
        stri_count_coll("a", "a", strength=1, opts_collator={"strength": 3})


def test_unknown_name_with_dots_is_unused():
    with pytest.warns(UserWarning, match="bogus"):
        assert stri_count_coll("a", "a", opts_collator={"bogus": True}) == [1]
    with pytest.raises(TypeError, match="unused argument"):
        stri_count_coll("a", "a", strength=1, opts_collator={"bogus": True})


def test_bad_opts_specifier():
    with pytest.raises(TypeError, match="incorrect collator option specifier"):
        stri_count_coll("a", "a", opts_collator="de")


def test_illegal_strength_and_numeric_search():
    with pytest.raises(RuntimeError, match="U_ILLEGAL_ARGUMENT_ERROR"):
        stri_count_coll("a", "A", strength=5)
    with pytest.raises(RuntimeError, match="U_UNSUPPORTED_ERROR"):
        stri_detect_coll("a10", "2", numeric=True)
    assert stri_count_coll("", "a", numeric=True) == [0]
    assert stri_count_coll(NA, "a", numeric=True) == [NA]


def test_inconsistent_lengths_raise():
    with pytest.raises(ValueError, match="vector length not consistent"):
        stri_subset_coll(["a"], ["a", "b"])
    with pytest.raises(ValueError, match="vector length not consistent"):
        stri_replace_all_coll(["ab", "cd"], ["a"], ["X", "Y"], vectorize_all=False)


def test_empty_subset_skips_a_bad_collator():
    assert stri_subset_coll([], ["a", "b"], opts_collator="nope") == []


def test_ambiguous_collator_prefix():
    with pytest.raises(TypeError, match="multiple formal arguments"):
        stri_count_coll("a", "a", n=1)


def test_root_locale_warns_for_an_unknown_id():
    with pytest.warns(UserWarning, match="root or the default locale"):
        assert stri_detect_coll("a", "a", locale="zz") == [True]


def test_vectorise_spelling():
    assert stri_replace_all_coll(["ab"], "a", "Z", vectorise_all=False) == ["Zb"]
