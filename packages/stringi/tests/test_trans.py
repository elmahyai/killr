"""Checks for case mapping, character translation, and transliteration."""

from __future__ import annotations

import warnings

import pytest

from stringi._na import NA, is_na
from stringi.trans import (
    stri_trans_casefold,
    stri_trans_char,
    stri_trans_general,
    stri_trans_list,
    stri_trans_tolower,
    stri_trans_totitle,
    stri_trans_toupper,
)


def test_turkish_case_is_icu_not_python_lower():
    assert stri_trans_tolower("I", "tr_TR") == "\u0131"
    assert stri_trans_tolower("i", "tr_TR") == "i"
    assert stri_trans_toupper("i", "tr_TR") == "\u0130"
    assert stri_trans_toupper("I", "tr_TR") == "I"
    assert stri_trans_tolower("\u0130", "tr") == "i"
    assert stri_trans_toupper("\u0131", "tr") == "I"
    assert "I".lower() == "i"
    assert stri_trans_tolower("I", "en_US") == "i"
    assert stri_trans_toupper("i", "en_US") == "I"
    assert stri_trans_toupper("i", "") == "I"
    assert stri_trans_toupper("i", None) == "I"


def test_lithuanian_and_context_sensitive_case():
    assert stri_trans_tolower("I\u0307", "lt") == "i\u0307\u0307"
    assert "I\u0307".lower() == "i\u0307"
    assert stri_trans_toupper("i\u0307", "lt") == "I"
    assert stri_trans_tolower("\u03a3\u03a3", "el") == "\u03c3\u03c2"
    assert stri_trans_tolower("A\u03a3A", "el") == "a\u03c3a"
    assert stri_trans_toupper("\u00df", "de_DE") == "SS"


def test_casefold_is_icu_full_fold():
    assert stri_trans_casefold("AbC") == "abc"
    assert stri_trans_casefold("\u00df") == "ss"
    assert stri_trans_casefold("\u0130") == "i\u0307"
    assert stri_trans_casefold("\ufb01") == "fi"
    assert stri_trans_casefold("\u03a3") == "\u03c3"
    assert stri_trans_casefold("") == ""
    folded = stri_trans_casefold(["AbC", "\u00df", "\u0130", NA, "NA", ""])
    assert folded == ["abc", "ss", "i\u0307", NA, "na", ""]
    assert folded[3] is NA
    assert stri_trans_casefold("NA") == "na"


def test_case_mapping_keeps_na_and_coerces_a_scalar():
    assert stri_trans_tolower(NA) is NA
    assert stri_trans_toupper("NA") == "NA"
    assert stri_trans_tolower(["AbC", NA, "NA", ""]) == ["abc", NA, "na", ""]
    assert stri_trans_tolower(None) == []
    assert stri_trans_toupper(1) == "1"
    with pytest.raises(ValueError, match="locale"):
        stri_trans_tolower("a", NA)


def test_title_word_sentence_and_turkish():
    sentence = "stringi is a FREE R pAcKaGe. WItH NO StrinGS attached."
    assert (
        stri_trans_totitle(sentence)
        == "Stringi Is A Free R Package. With No Strings Attached."
    )
    assert (
        stri_trans_totitle(sentence, type="sentence")
        == "Stringi is a free r package. With no strings attached."
    )
    assert stri_trans_totitle("one. two. three.") == "One. Two. Three."
    assert stri_trans_totitle("one. two. three.", type="sentence") == "One. two. three."
    assert (
        stri_trans_totitle("one. Two. three.", type="sent") == "One. Two. three."
    )
    assert stri_trans_totitle("iPhone ISTANBUL", locale="tr_TR") == "\u0130phone Istanbul"
    titled = stri_trans_totitle(["ab c", NA, "NA"])
    assert titled == ["Ab C", NA, "Na"]
    assert titled[1] is NA
    with pytest.raises(ValueError):
        stri_trans_totitle("Hello", type="not-a-type")


def test_trans_char_maps_code_points_and_keeps_the_last_duplicate():
    assert stri_trans_char("id.123", ".", "_") == "id_123"
    assert stri_trans_char("babaab", "ab", "01") == "101001"
    assert stri_trans_char("abc", "aab", "XYZ") == "YZc"
    assert stri_trans_char(["ab", NA, "NA"], "ab", "XY") == ["XY", NA, "NA"]
    assert stri_trans_char(NA, "a", "b") is NA
    assert stri_trans_char(["ab", "cd"], NA, "X") == [NA, NA]
    assert stri_trans_char("ab", "a", NA) is NA
    assert stri_trans_char(None, "a", "b") == []
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        assert stri_trans_char("abc", "", "") == "abc"


def test_trans_char_warns_when_the_code_point_counts_differ():
    with pytest.warns(UserWarning, match="vector length not consistent"):
        assert stri_trans_char("abc", "abcd", "01") == "01c"
    with pytest.warns(UserWarning, match="vector length not consistent"):
        assert stri_trans_char("aaa", "a", "xy") == "xxx"
    with pytest.warns(UserWarning, match="only the first element is used"):
        assert stri_trans_char("abc", ["ab", "cd"], "12") == "12c"


def test_trans_general_ids_rules_and_na():
    assert stri_trans_general("gro\u00df", "Latin-ASCII") == "gross"
    assert stri_trans_general("gro\u00df", "latin-ascii") == "gross"
    assert stri_trans_general("\u2620", "Any-Hex") == "\\u2620"
    assert stri_trans_general("\\u0061\\u00df", "Any-Hex", forward=False) == "a\u00df"
    assert stri_trans_general("\u0104", "nfd; lower") == "a\u0328"
    assert stri_trans_general("stringi", "upper") == "STRINGI"
    assert stri_trans_general("abc", "a > X; b > Y;", rules=True) == "XYc"
    assert stri_trans_general(["A", NA, ""], "Latin-ASCII") == ["A", NA, ""]
    assert stri_trans_general("A", NA) is NA
    assert stri_trans_general(None, "Latin-ASCII") == []
    with pytest.raises(ValueError, match="unknown transliterator"):
        stri_trans_general("a", "not-a-transform")


def test_trans_list_is_the_sorted_icu_inventory():
    names = stri_trans_list()
    assert names[0] == "Accents-Any"
    assert names[-1] == "zu-zu_FONIPA"
    assert "Latin-ASCII" in names
    assert "Any-Hex" in names
    assert len(names) == 756
    assert stri_trans_list() == names
