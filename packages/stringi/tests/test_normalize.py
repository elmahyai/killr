"""Normalization matches the stringi 1.8.9 cases checked against R."""

from stringi._na import NA
from stringi.normalize import (
    stri_trans_isnfc,
    stri_trans_isnfd,
    stri_trans_isnfkc,
    stri_trans_isnfkc_casefold,
    stri_trans_isnfkd,
    stri_trans_nfc,
    stri_trans_nfd,
    stri_trans_nfkc,
    stri_trans_nfkc_casefold,
    stri_trans_nfkd,
)

import pytest


def _cps(text):
    return " ".join(f"{ord(char):04X}" for char in text)


def test_nfc_composes_and_keeps_na_and_empty():
    assert stri_trans_nfc("a\u0301") == "\u00e1"
    assert stri_trans_nfc(["a\u0301", "\u00e1", NA, ""]) == ["\u00e1", "\u00e1", NA, ""]
    assert stri_trans_nfc("NA") == "NA"
    assert stri_trans_nfc(()) == []


def test_nfd_decomposes_ogonek_and_reorders_marks():
    assert _cps(stri_trans_nfd("\u0105")) == "0061 0328"
    assert stri_trans_nfd([NA, ""]) == [NA, ""]
    assert _cps(stri_trans_nfd("q\u0307\u0323")) == "0071 0323 0307"


def test_nfkc_and_nfkd():
    assert stri_trans_nfkc("\ufb01") == "fi"
    assert len(stri_trans_nfkc("\ufdfa")) == 18
    assert _cps(stri_trans_nfkc("\ufdfa")) == (
        "0635 0644 0649 0020 0627 0644 0644 0647 0020 "
        "0639 0644 064A 0647 0020 0648 0633 0644 0645"
    )
    assert stri_trans_nfkd("\u2126") == "\u03a9"
    assert stri_trans_nfkd("\ufb01") == "fi"
    assert stri_trans_nfc("\u1100\u1161") == "\uac00"


def test_nfkc_casefold_matches_the_installed_probes():
    assert stri_trans_nfkc_casefold("AbC") == "abc"
    assert stri_trans_nfkc_casefold("\ufb01") == "fi"
    assert stri_trans_nfkc_casefold("\u2126") == "\u03c9"
    assert stri_trans_nfkc_casefold("\u2126") != stri_trans_nfkc("\u2126")
    assert _cps(stri_trans_nfkc_casefold("\u037a\u0301")) == "0020 03AF"
    assert stri_trans_nfkc_casefold("a\u00adb") == "ab"
    assert stri_trans_nfkc_casefold("") == ""
    assert stri_trans_nfkc_casefold(["AbC", NA, ""])[1] is NA


def test_is_forms_keep_na_and_treat_empty_as_normalized():
    assert stri_trans_isnfc(["\u00e1", "a\u0301", NA, ""]) == [True, False, NA, True]
    assert stri_trans_isnfd(["a\u0328", "\u0105", NA, ""]) == [True, False, NA, True]
    assert stri_trans_isnfkc(["fi", "\ufb01", NA, ""]) == [True, False, NA, True]
    assert stri_trans_isnfkd(["\u03a9", "\u2126", NA, ""]) == [True, False, NA, True]
    assert stri_trans_isnfkc_casefold(["abc", "AbC", "a\u00adb", NA, ""]) == [
        True,
        False,
        False,
        NA,
        True,
    ]
    assert stri_trans_isnfc("\u00e1") is True


def test_scalar_string_stays_a_string_and_bad_input_errors():
    assert isinstance(stri_trans_nfc("ab"), str)
    with pytest.raises(TypeError):
        stri_trans_nfc(1)
    with pytest.raises(TypeError):
        stri_trans_isnfd([None])
