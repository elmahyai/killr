"""Installed stringi 1.8.9 option builders."""

import warnings

import pytest

from stringi._na import NA
from stringi.opts import (
    stri_opts_brkiter,
    stri_opts_collator,
    stri_opts_fixed,
    stri_opts_regex,
)


def test_omitted_arguments_are_absent():
    assert stri_opts_fixed() == {}
    assert stri_opts_collator() == {}
    assert stri_opts_regex() == {}
    assert stri_opts_brkiter() == {}


def test_explicit_defaults_are_stored():
    assert stri_opts_fixed(False, False) == {
        "case_insensitive": False,
        "overlap": False,
    }
    assert list(stri_opts_fixed(False, False)) == ["case_insensitive", "overlap"]


def test_overlap_true_is_the_only_supplied_setting():
    assert stri_opts_fixed(overlap=True) == {"overlap": True}
    assert stri_opts_fixed(case_insensitive=False, overlap=True) == {
        "case_insensitive": False,
        "overlap": True,
    }


def test_longer_vector_keeps_the_first_element_and_warns():
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        result = stri_opts_fixed([True, False], [False, True])
    assert result == {"case_insensitive": True, "overlap": False}
    assert len(caught) == 2
    assert all(
        str(item.message) == "number of items to replace is not a multiple of replacement length"
        for item in caught
    )


def test_empty_replacement_is_an_error():
    with pytest.raises(ValueError, match=r"^replacement has length zero$"):
        stri_opts_fixed(overlap=[])
    with pytest.raises(ValueError, match=r"^replacement has length zero$"):
        stri_opts_collator(strength=())
    with pytest.raises(ValueError, match=r"^replacement has length zero$"):
        stri_opts_brkiter(type=[])


def test_null_drops_the_name_and_a_wrapped_null_is_kept():
    assert stri_opts_fixed(overlap=None) == {}
    assert stri_opts_fixed(case_insensitive=True, overlap=None) == {"case_insensitive": True}
    assert stri_opts_fixed(overlap=[None]) == {"overlap": None}
    assert stri_opts_collator(normalization=None, normalisation=True) == {}
    assert stri_opts_regex(dotall=None, dot_all=True) == {}


def test_length_one_list_unwraps_and_a_nested_vector_stays():
    assert stri_opts_fixed(overlap=[True]) == {"overlap": True}
    assert stri_opts_fixed(overlap=[[True, False]]) == {"overlap": [True, False]}
    assert stri_opts_fixed(overlap=[[]]) == {"overlap": []}


def test_partial_names_and_unused_arguments():
    assert stri_opts_fixed(over=True) == {"overlap": True}
    assert stri_opts_fixed(True, case=False) == {
        "case_insensitive": False,
        "overlap": True,
    }
    with pytest.raises(TypeError, match=r"^unused argument \(foo = TRUE\)$"):
        stri_opts_fixed(foo=True)
    with pytest.raises(TypeError, match=r"^unused argument \(3\)$"):
        stri_opts_fixed(1, 2, 3)
    with pytest.raises(TypeError, match=r"^unused arguments \(3, foo = TRUE\)$"):
        stri_opts_fixed(1, 2, 3, foo=True)
    with pytest.raises(TypeError, match=r"^unused argument \(foo = c\(1, 2\)\)$"):
        stri_opts_fixed(foo=[1, 2])
    with pytest.raises(TypeError, match=r"^argument 1 matches multiple formal arguments$"):
        stri_opts_regex(dot=True)
    with pytest.raises(TypeError, match=r"^argument 2 matches multiple formal arguments$"):
        stri_opts_regex(True, dot=True)
    with pytest.raises(TypeError, match=r"^argument 1 matches multiple formal arguments$"):
        stri_opts_collator(norm=True)
    with pytest.raises(TypeError, match=r"^argument 1 matches multiple formal arguments$"):
        stri_opts_brkiter(skip=True)


def test_collator_order_alias_and_na():
    result = stri_opts_collator(
        numeric=True,
        locale="en",
        strength=1,
        normalisation=True,
        french=False,
        uppercase_first=NA,
    )
    assert list(result) == [
        "locale",
        "strength",
        "french",
        "uppercase_first",
        "numeric",
        "normalization",
    ]
    assert result["locale"] == "en"
    assert result["strength"] == 1
    assert result["uppercase_first"] is NA
    assert result["normalization"] is True
    assert stri_opts_collator(normalization=False, normalisation=True) == {
        "normalization": False
    }
    assert stri_opts_collator(normalis=True) == {"normalization": True}
    assert stri_opts_collator(locale="") == {"locale": ""}
    assert stri_opts_collator(locale=None, numeric=True, strength=2) == {
        "strength": 2,
        "numeric": True,
    }


def test_regex_alias_and_limit_order():
    result = stri_opts_regex(
        case_insensitive=True,
        dot_all=True,
        multi_line=True,
        time_limit=5,
        stack_limit=9,
    )
    assert list(result.items()) == [
        ("case_insensitive", True),
        ("stack_limit", 9),
        ("time_limit", 5),
        ("dotall", True),
        ("multiline", True),
    ]
    assert stri_opts_regex(dotall=False, dot_all=True) == {"dotall": False}
    assert stri_opts_regex(multiline=False, multi_line=True) == {"multiline": False}
    assert stri_opts_regex() == {}
    assert stri_opts_regex(time_limit=0, stack_limit=0) == {
        "stack_limit": 0,
        "time_limit": 0,
    }


def test_brkiter_keeps_supplied_skips_in_signature_order():
    result = stri_opts_brkiter(
        skip_sentence_sep=True,
        type="word",
        locale="pl_PL",
        skip_word_none=True,
        skip_line_soft=False,
    )
    assert list(result.items()) == [
        ("type", "word"),
        ("locale", "pl_PL"),
        ("skip_word_none", True),
        ("skip_line_soft", False),
        ("skip_sentence_sep", True),
    ]
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        recycled = stri_opts_brkiter(type=["word", "line_break"])
    assert recycled == {"type": "word"}
    assert len(caught) == 1
