"""Collation and sort results checked against stringi 1.8.9."""

import warnings

import pytest

from stringi._na import NA, is_na
from stringi.collate import (
    s_ceq,
    s_cne,
    s_eq,
    s_ge,
    s_gt,
    s_le,
    s_lt,
    s_ne,
    stri_ceq,
    stri_cmp,
    stri_cmp_eq,
    stri_cmp_equiv,
    stri_cmp_ge,
    stri_cmp_gt,
    stri_cmp_le,
    stri_cmp_lt,
    stri_cmp_neq,
    stri_cmp_nequiv,
    stri_cne,
    stri_coll,
    stri_compare,
    stri_duplicated,
    stri_duplicated_any,
    stri_eq,
    stri_ge,
    stri_gt,
    stri_le,
    stri_lt,
    stri_ne,
    stri_order,
    stri_rank,
    stri_sort,
    stri_sort_key,
    stri_unique,
)
from stringi.opts import stri_opts_collator

NFKD_A = "a\u0328"
MARIOS = ["Mario", "mario", "Mário", "mário"]


def test_aliases_are_the_same_objects():
    assert stri_compare is stri_cmp
    assert stri_coll is stri_opts_collator
    assert stri_lt is s_lt
    assert stri_le is s_le
    assert stri_gt is s_gt
    assert stri_ge is s_ge
    assert stri_eq is s_eq
    assert stri_ne is s_ne
    assert stri_ceq is s_ceq
    assert stri_cne is s_cne


def test_polish_and_slovak_order_ch_differently():
    assert stri_cmp_lt("hladny", "chladny", locale="pl_PL") == [False]
    assert stri_cmp_lt("hladny", "chladny", locale="sk_SK") == [True]
    assert stri_cmp("hladny", "chladny", locale="pl_PL") == [1]
    assert stri_compare("hladny", "chladny", locale="sk_SK") == [-1]
    assert stri_sort(["hladny", "chladny"], locale="pl_PL") == ["chladny", "hladny"]
    assert stri_order(["hladny", "chladny"], locale="sk_SK") == [1, 2]
    assert stri_rank(["hladny", "chladny", "hladny"], locale="pl_PL") == [2, 1, 2]


def test_strength_case_level_and_code_points():
    assert stri_cmp_equiv(MARIOS, "mario", case_level=True, strength=2) == [
        False,
        True,
        False,
        False,
    ]
    assert stri_cmp_equiv(MARIOS, "mario", case_level=True, strength=1) == [
        False,
        True,
        False,
        True,
    ]
    assert stri_cmp_equiv(MARIOS, "mario", strength=1) == [True, True, True, True]
    assert stri_cmp_equiv(MARIOS, "mario", strength=2) == [True, True, False, False]
    assert stri_cmp_eq(NFKD_A, "\u0105") == [False]
    assert stri_cmp_equiv(NFKD_A, "\u0105") == [True]
    assert stri_cmp_equiv("\ufb00", "ff", strength=2) == [True]
    assert s_eq("a", "A") == [False]
    assert s_ceq("\ufeffa", "a") == [True]
    assert s_cne("a", "a") == [False]
    assert stri_cmp_neq("a", "b") == [True]


def test_numeric_shifted_french_phonebook_and_danish_case():
    assert stri_cmp("number100", "number2", numeric=True) == [1]
    assert stri_cmp("number100", "number2") == [-1]
    assert stri_cmp("above mentioned", "above-mentioned") == [-1]
    assert stri_cmp("above mentioned", "above-mentioned", alternate_shifted=True) == [0]
    assert stri_cmp_equiv(
        "Gärtner", "Gaertner", locale="de_DE@collation=phonebook", strength=1
    ) == [True]
    assert stri_cmp_equiv("Gärtner", "Gaertner", locale="de_DE", strength=1) == [False]
    assert stri_sort(["cote", "coté", "côte", "côté"], locale="en_US", french=True) == [
        "cote",
        "côte",
        "coté",
        "côté",
    ]
    assert stri_sort(["cote", "coté", "côte", "côté"], locale="en_US", french=False) == [
        "cote",
        "coté",
        "côte",
        "côté",
    ]
    assert stri_cmp(["a", "A"], ["A", "a"], locale="da_DK") == [1, -1]
    assert stri_cmp(["a", "A"], ["A", "a"], locale="da_DK", uppercase_first=NA) == [-1, 1]
    assert stri_cmp("a", "A", strength=2.9) == [0]
    assert stri_cmp("a", "A", strength=4) == [-1]
    assert stri_cmp("a", "A", locale="C") == [1]
    assert stri_cmp("a", "A", locale="c.UTF-8") == [1]
    assert stri_cmp_lt("hladny", "chladny", locale="pl_PL.UTF-8") == [False]
    assert stri_cmp_lt("hladny", "chladny", locale="pl-PL") == [False]


def test_bom_is_stripped_for_compare_and_kept_in_the_sort_key():
    assert stri_cmp_eq("\ufeffabc", "abc") == [True]
    assert stri_cmp_eq("\ufeff\ufeffa", "\ufeffa") == [False]
    assert stri_cmp_eq("a\ufeffb", "ab") == [False]
    assert stri_sort(["\ufeffabc", "abc", "abd"]) == ["abc", "abc", "abd"]
    assert [ord(ch) for ch in stri_unique(["\ufeff\ufeffa", "\ufeffa", "a"], strength=16)[0]] == [
        0xFEFF,
        ord("a"),
    ]
    assert stri_duplicated(["\ufeff\ufeffa", "\ufeffa", "a"], strength=16) == [
        False,
        False,
        True,
    ]
    default = stri_sort_key(["\ufeffabc", "abc", NA])
    assert default[0] == default[1]
    assert default[0].hex() == "2b2d2f01070107"
    assert is_na(default[2])
    identical = stri_sort_key(["\ufeffabc", "abc"], strength=16)
    assert identical[0].hex() == "2b2d2f010701070101fd07b505fb8e9394"
    assert identical[1].hex() == "2b2d2f010701070101929394"
    assert [key.hex() for key in stri_sort_key([10, 2], numeric=True)] == [
        "100c01050105",
        "100401050105",
    ]


def test_sort_order_rank_unique_and_duplicates():
    assert stri_sort([1, 100, 2, 101, 11, 10]) == ["1", "10", "100", "101", "11", "2"]
    assert stri_sort([1, 100, 2, 101, 11, 10], numeric=True) == [
        "1",
        "2",
        "10",
        "11",
        "100",
        "101",
    ]
    assert stri_sort([1e5, 2, 10, 1e-4]) == ["10", "1e-04", "1e+05", "2"]
    assert stri_sort(["b", NA, "a"]) == ["a", "b"]
    assert stri_sort(["b", NA, "a"], na_last=True) == ["a", "b", NA]
    assert stri_sort(["b", NA, "a"], na_last=False, decreasing=True) == [NA, "b", "a"]
    assert stri_sort(["b", "a", "b", "c"], decreasing=True) == ["c", "b", "b", "a"]
    assert stri_sort(["a", "b"], decreasing=1) == ["b", "a"]
    assert stri_order(["b", NA, "a", NA]) == [3, 1, 2, 4]
    assert stri_order(["b", NA, "a", NA], na_last=False) == [2, 4, 3, 1]
    assert stri_order(["b", NA, "a", NA], na_last=NA) == [3, 1]
    assert stri_order(["a", "a", "b"], decreasing=True) == [3, 1, 2]
    assert stri_order(["a", "\u0105", NFKD_A, "b"], strength=1) == [1, 2, 3, 4]
    assert stri_rank(["b", "a", "b", NA, "A"]) == [3, 1, 3, NA, 2]
    assert stri_rank(["b", "a", "a", "c"]) == [3, 1, 1, 4]
    assert stri_unique(["b", NA, "a", NA, "b", "B"]) == ["b", NA, "a", "B"]
    assert stri_unique(["b", "B", "a", "\u0105", NFKD_A], strength=1) == ["b", "a"]
    assert stri_unique(["groß", "GROSS", "Groß", "Gross"], strength=1) == ["groß"]
    assert stri_unique(["\u0105", NFKD_A, "a"]) == ["\u0105", "a"]
    assert stri_duplicated(["a", "b", "a", NA, "a", NA]) == [
        False,
        False,
        True,
        False,
        True,
        True,
    ]
    assert stri_duplicated(["a", "b", "a", NA, "a", NA], from_last=True) == [
        True,
        False,
        True,
        True,
        False,
        False,
    ]
    assert stri_duplicated(["\u0105", NFKD_A]) == [False, True]
    assert stri_duplicated_any(["a", "b", "a", NA, "a", NA]) == [3]
    assert stri_duplicated_any(["a", "b", "a", NA, "a", NA], from_last=True) == [4]
    assert stri_duplicated_any([]) == [0]
    assert stri_duplicated_any(None) == [0]


def test_missing_values_recycling_and_empty_input():
    assert stri_cmp([NA, "a", None], ["a", NA, "b"]) == [NA, NA, NA]
    assert stri_cmp_eq([NA, "NA", ""], ["NA", NA, ""]) == [NA, NA, True]
    assert stri_cmp("NA", "NA") == [0]
    assert stri_cmp([], "a") == []
    assert stri_cmp(None, None) == []
    assert stri_cmp(["a", "b", "c"], "b") == [-1, 0, 1]
    assert stri_sort(None) == []
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        assert stri_cmp(["a", "b", "c"], ["a", "b"]) == [0, 0, 1]
    assert any("not a multiple" in str(item.message) for item in caught)


def test_option_errors_and_warnings():
    with pytest.raises(ValueError, match="Illegal argument"):
        stri_cmp("a", "A", strength=5)
    with pytest.raises(ValueError, match="missing values in argument `decreasing`"):
        stri_sort(["a"], decreasing=NA)
    with pytest.raises(ValueError, match="non-empty vector"):
        stri_sort(["a"], decreasing=[])
    with pytest.raises(ValueError, match="incorrect collator option specifier"):
        stri_cmp("a", "b", opts_collator=1)
    with pytest.raises(TypeError, match="unused argument"):
        stri_cmp("a", "b", foo=1)
    with pytest.raises(TypeError, match="matched by multiple actual arguments"):
        stri_cmp("a", "b", opts_collator={"numeric": True}, numeric=False)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        assert stri_cmp("a", "b", locale="zz") == [-1]
    assert any("root or the default locale" in str(item.message) for item in caught)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        assert stri_cmp("a", "b", opts_collator={"foo": 1}) == [-1]
    assert any("incorrect opts_collator setting: 'foo'" in str(item.message) for item in caught)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        assert stri_duplicated_any(["a", "a"], fromLast=True) == [1]
    assert any("deprecated alias" in str(item.message) for item in caught)
    assert stri_coll(numeric=True) == {"numeric": True}
    assert stri_coll(normalisation=True) == {"normalization": True}
    assert stri_cmp("number100", "number2", normalisation=False, numeric=True) == [1]
