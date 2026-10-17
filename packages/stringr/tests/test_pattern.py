"""stringr 1.6.0 modifier functions."""

import warnings

import pytest

from stringi._na import NA, is_na
from stringr.pattern import boundary, coll, fixed, pattern_opts, pattern_type, regex


def test_fixed_stores_case_insensitive():
    plain = fixed("a.b")
    assert list(plain) == ["a.b"]
    assert plain.kind == "fixed"
    assert plain.options == {"case_insensitive": False}
    assert pattern_type(plain) == "fixed"
    assert pattern_opts(plain) == {"case_insensitive": False}
    assert fixed("a.b", True).options == {"case_insensitive": True}
    assert list(fixed(["abb", "a.b"])) == ["abb", "a.b"]
    assert list(fixed(NA)) == [NA]
    assert list(fixed(NA))[0] is NA


def test_fixed_coerces_logical_and_null():
    with pytest.warns(UserWarning, match="Coercing `pattern` to a plain character vector."):
        assert list(fixed(True)) == ["TRUE"]
    with pytest.warns(UserWarning, match="Coercing `pattern` to a plain character vector."):
        assert list(fixed(False)) == ["FALSE"]
    with pytest.warns(UserWarning, match="Coercing `pattern` to a plain character vector."):
        assert list(fixed(None)) == []
    with pytest.raises(ValueError, match="TRUE"):
        fixed("a", 1)


def test_fixed_subset_keeps_options():
    both = fixed(["a", "b"], ignore_case=True)
    assert list(both[1]) == ["b"]
    assert both[1].kind == "fixed"
    assert both[1].options == {"case_insensitive": True}


def test_coll_defaults_and_strength():
    assert coll("a").options == {"locale": "en", "strength": 3}
    assert coll("a", True).options == {"locale": "en", "strength": 2}
    assert coll("a", True, strength=1).options == {"locale": "en", "strength": 1}
    turkish = coll("i", ignore_case=True, locale="tr")
    assert turkish.options == {"locale": "tr", "strength": 2}
    assert coll("a", numeric=True).options == {
        "locale": "en",
        "strength": 3,
        "numeric": True,
    }
    assert coll("a", strength=None).options["strength"] == 3
    assert is_na(coll("a", strength=NA).options["strength"])
    with pytest.raises(ValueError, match="locale"):
        coll("a", locale=1)


def test_regex_stores_the_four_flags():
    assert regex("a.b").options == {
        "case_insensitive": False,
        "comments": False,
        "dotall": False,
        "multiline": False,
    }
    flagged = regex("[a-z]+", True, multiline=True, comments=True, dotall=True)
    assert flagged.options == {
        "case_insensitive": True,
        "comments": True,
        "dotall": True,
        "multiline": True,
    }
    limited = regex("a", time_limit=10)
    assert list(limited.options) == [
        "case_insensitive",
        "comments",
        "time_limit",
        "dotall",
        "multiline",
    ]
    assert regex("a", dot_all=True).options["dotall"] is False
    assert regex("a", dotall=True, dot_all=False).options["dotall"] is True
    assert pattern_type(flagged) == "regex"


def test_boundary_word_and_default():
    default = boundary()
    assert list(default) == [NA]
    assert list(default)[0] is NA
    assert default.kind == "bound"
    assert default.options == {"type": "character", "skip_word_none": False}
    word = boundary("word")
    assert list(word) == [NA]
    assert list(word)[0] is NA
    assert word.options == {"type": "word", "skip_word_none": True}
    assert boundary("sentence").options == {"type": "sentence", "skip_word_none": False}
    assert boundary("line_break").options["type"] == "line_break"
    assert boundary("word", skip_word_none=False).options["skip_word_none"] is False
    assert boundary("character", skip_word_none=True).options["skip_word_none"] is True
    assert boundary("word", locale="tr").options == {
        "type": "word",
        "locale": "tr",
        "skip_word_none": True,
    }
    with pytest.raises(ValueError, match="word"):
        boundary("w")
    with pytest.raises(ValueError, match="not"):
        boundary("nope")


def test_plain_pattern_type_and_empty_opts():
    assert pattern_type("a.b") == "regex"
    assert pattern_opts("a.b") is None
    assert pattern_type("") == "empty"
    assert pattern_type([""]) == "empty"
    assert pattern_type(["", ""]) == "regex"
    assert pattern_opts("") == {"type": "character"}
    assert pattern_opts([""]) == {"type": "character"}
    assert pattern_type(fixed("")) == "fixed"
    assert pattern_opts(fixed("")) == {"case_insensitive": False}
    with pytest.raises(ValueError, match="NAs"):
        pattern_type(NA)
    with pytest.raises(ValueError, match="NAs"):
        pattern_type(["a", NA])
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        again = fixed(fixed("a"))
    assert list(again) == ["a"]
    assert again.options == {"case_insensitive": False}
