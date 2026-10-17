"""Subset replacement checked against stringi 1.8.9."""

import warnings

import pytest

from stringi._na import NA
from stringi.subset import (
    stri_subset_assign,
    stri_subset_charclass_assign,
    stri_subset_coll_assign,
    stri_subset_fixed_assign,
    stri_subset_regex_assign,
)


def _warns(fn):
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        try:
            value = fn()
            error = None
        except Exception as exc:
            value = None
            error = exc
    return value, error, [str(item.message) for item in caught]


def test_fixed_replaces_matches_and_leaves_the_caller_unchanged():
    src = ["ab", "ba", "cd"]
    out = stri_subset_fixed_assign(src, "a", value="Z")
    assert out == ["Z", "Z", "cd"]
    assert src == ["ab", "ba", "cd"]
    assert out is not src


def test_pattern_na_keeps_the_string_and_empty_pattern_is_na():
    assert stri_subset_fixed_assign(["ab", NA, "cd"], NA, value="Z") == ["ab", NA, "cd"]
    assert stri_subset_fixed_assign([NA, "a"], NA, value="Z") == [NA, "a"]
    value, error, messages = _warns(
        lambda: stri_subset_fixed_assign(["ab", "cd"], "", value="Z")
    )
    assert error is None
    assert value == [NA, NA]
    assert messages == ["empty search patterns are not supported"]


def test_value_follows_matches_not_string_positions():
    value, error, messages = _warns(
        lambda: stri_subset_fixed_assign(
            ["a", "x", "a", "x", "a"], "a", value=["A", "B"]
        )
    )
    assert error is None
    assert value == ["A", "x", "B", "x", "A"]
    assert messages == [
        "number of items to replace is not a multiple of replacement length"
    ]
    assert stri_subset_fixed_assign(
        ["ab", "xx", "a"], [NA, "x", "a"], value=["A", "B"]
    ) == ["ab", "A", "B"]


def test_negate_empty_string_and_case_fold():
    assert stri_subset_fixed_assign(
        ["", "a", ""], "a", negate=True, value="Z"
    ) == ["Z", "a", "Z"]
    assert stri_subset_fixed_assign(
        ["aa", "a", "b", "aba"], "a", negate=True, value="Z"
    ) == ["aa", "a", "Z", "aba"]
    assert stri_subset_fixed_assign(
        ["aß", "ss", "SS"], "ß", value="Q", case_insensitive=True
    ) == ["Q", "ss", "SS"]
    value, error, messages = _warns(
        lambda: stri_subset_fixed_assign(["aaa", "b"], "a", value="Z", overlap=True)
    )
    assert value == ["Z", "b"]
    assert messages == ["incorrect opts_fixed setting: 'overlap'; ignoring"]


def test_recycling_lengths_and_coercion():
    value, error, messages = _warns(
        lambda: stri_subset_fixed_assign(["a", "b", "c"], ["", "a"], value="Z")
    )
    assert value == [NA, "b", NA]
    assert messages == [
        "longer object length is not a multiple of shorter object length",
        "empty search patterns are not supported",
    ]
    with pytest.raises(ValueError, match="vector length not consistent"):
        stri_subset_fixed_assign(["a"], ["a", "b"], value="Z")
    with pytest.raises(ValueError, match="replacement has length zero"):
        stri_subset_fixed_assign(["a"], "a", value=[])
    with pytest.raises(ValueError, match="vector has length zero"):
        stri_subset_fixed_assign(["a"], None, value="Z")
    assert stri_subset_fixed_assign(None, "a", value="Z") == []
    assert stri_subset_fixed_assign([], "", value="Z") == []
    assert stri_subset_fixed_assign([1, 12, 3], "1", value="Z") == ["Z", "Z", "3"]
    assert stri_subset_fixed_assign([1, NA, 12], "1", value="Z") == ["Z", NA, "Z"]
    assert stri_subset_fixed_assign([True, False], "T", value="Q") == ["Q", "FALSE"]
    assert stri_subset_fixed_assign([1.5, 1e-4], "1", value="Q") == ["Q", "Q"]
    assert stri_subset_fixed_assign([True, 1], "1", value="Q") == ["Q", "Q"]


def test_negate_and_missing_arguments():
    value, error, messages = _warns(
        lambda: stri_subset_fixed_assign(["a", "b"], "a", negate=[True, False], value="Z")
    )
    assert value == ["a", "Z"]
    assert messages == [
        "argument `negate` should be a single logical value; only the first element is used"
    ]
    with pytest.raises(ValueError, match="missing values in argument `negate`"):
        stri_subset_fixed_assign(["a"], "a", negate=NA, value="Z")
    with pytest.raises(ValueError, match="non-empty vector"):
        stri_subset_fixed_assign(["a"], "a", negate=[], value="Z")
    with pytest.raises(ValueError, match='argument "value" is missing'):
        stri_subset_fixed_assign(["a"], "a")
    with pytest.raises(ValueError, match='argument "pattern" is missing'):
        stri_subset_fixed_assign(["a"], value="Z")


def test_option_warnings_follow_the_installed_order():
    value, error, messages = _warns(
        lambda: stri_subset_fixed_assign(
            [], "a", opts_fixed={"nope": True}, value="Z"
        )
    )
    assert value == []
    assert messages == ["incorrect opts_fixed setting: 'nope'; ignoring"]
    value, error, messages = _warns(
        lambda: stri_subset_fixed_assign(
            ["a"], "a", opts_fixed={"nope": True}, value=[]
        )
    )
    assert isinstance(error, ValueError)
    assert str(error) == "replacement has length zero"
    assert messages == ["incorrect opts_fixed setting: 'nope'; ignoring"]
    value, error, messages = _warns(
        lambda: stri_subset_regex_assign([], "a", opts_regex={"nope": True}, value="Z")
    )
    assert value == [] and messages == []
    value, error, messages = _warns(
        lambda: stri_subset_regex_assign(["a"], "a", opts_regex={"nope": True}, value=[])
    )
    assert str(error) == "replacement has length zero"
    assert messages == []
    with pytest.raises(ValueError, match="argument `opts_fixed` should be a list"):
        stri_subset_fixed_assign(["a"], "a", opts_fixed="nope", value="Z")
    with pytest.raises(TypeError, match="unused argument \\(nope = 1\\)"):
        stri_subset_regex_assign(["a"], "a", nope=1, value="Z")
    with pytest.raises(TypeError, match="multiple actual arguments"):
        stri_subset_fixed_assign(
            ["Ab"],
            "a",
            value="Z",
            opts_fixed={"case_insensitive": True},
            case_insensitive=False,
        )


def test_regex_searches_the_empty_string():
    assert stri_subset_regex_assign(
        ["stringi R", "123", "ID456", ""],
        "[0-9]+$",
        negate=True,
        value=NA,
    ) == [NA, "123", "ID456", NA]
    assert stri_subset_regex_assign(["", "a", ""], "a*", value="Z") == ["Z", "Z", "Z"]
    assert stri_subset_regex_assign(["", "x"], "^$", value="E") == ["E", "x"]
    assert stri_subset_regex_assign(["a\nb", "ab"], "a.b", value="Z", dotall=True) == [
        "Z",
        "ab",
    ]
    with pytest.raises(ValueError, match="U_REGEX_MISMATCHED_PAREN"):
        stri_subset_regex_assign(["ab"], "(", value="Z")


def test_collation_replacement_uses_subset_coll():
    assert stri_subset_coll_assign(
        ["aß", "b", "ss"], "ss", value="Q", strength=1, locale="de"
    ) == ["Q", "b", "Q"]
    assert stri_subset_coll_assign(
        ["aß", "b"], "ss", negate=True, value="Q", strength=1, locale="de"
    ) == ["aß", "Q"]
    assert stri_subset_coll_assign(["", "a"], "a", value="Z") == ["", "Z"]
    assert stri_subset_coll_assign(["aa", "a", "b"], "a", negate=True, value="Z") == [
        "aa",
        "a",
        "Z",
    ]
    value, error, messages = _warns(
        lambda: stri_subset_coll_assign(
            ["a", "a", "b"], "a", locale="not_a_locale_zzz", value="Z"
        )
    )
    assert value == ["Z", "Z", "b"]
    assert messages == [
        "A resource bundle lookup returned a result either from the root or the default locale."
    ]
    assert stri_subset_coll_assign([], "a", opts_collator="nope", value="Z") == []
    with pytest.raises(ValueError, match="incorrect collator option specifier"):
        stri_subset_coll_assign(["a"], "a", opts_collator="nope", value="Z")


def test_charclass_replacement():
    assert stri_subset_charclass_assign(["ab", "12", "c", ""], "\\p{L}", value="L") == [
        "L",
        "12",
        "L",
        "",
    ]
    assert stri_subset_charclass_assign(
        ["ab", "12", ""], "\\p{L}", negate=True, value="N"
    ) == ["ab", "N", "N"]
    assert stri_subset_charclass_assign(["", "a", "b"], "[a]", negate=True, value="Z") == [
        "Z",
        "a",
        "Z",
    ]
    assert stri_subset_charclass_assign([NA, "12"], "\\p{N}", value="Z") == [NA, "Z"]
    assert stri_subset_charclass_assign(["ab", NA], NA, value="Z") == ["ab", NA]
    assert stri_subset_charclass_assign([], "", value="Z") == []
    with pytest.raises(ValueError, match="U_MALFORMED_SET"):
        stri_subset_charclass_assign(["ab"], "", value="Z")
    with pytest.raises(TypeError, match="unused argument \\(nope = 1\\)"):
        stri_subset_charclass_assign(["a"], "\\p{L}", nope=1, value="Z")


def test_dispatcher_requires_exactly_one_engine():
    assert stri_subset_assign(["ab", "12"], regex="[0-9]", value="N") == ["ab", "N"]
    assert stri_subset_assign(["ab", "12"], fixed="a", value="F") == ["F", "12"]
    assert stri_subset_assign(
        ["aß", "b"], coll="ss", value="C", strength=1, locale="de"
    ) == ["C", "b"]
    assert stri_subset_assign(["ab", "12"], charclass="\\p{N}", value="D") == ["ab", "D"]
    assert stri_subset_assign(["ab", "12"], regex="[0-9]", negate=True, value="N") == [
        "N",
        "12",
    ]
    assert stri_subset_assign(["ab"], regex=NA, value="Z") == ["ab"]
    with pytest.raises(ValueError, match="vector has length zero"):
        stri_subset_assign(["ab"], regex=None, value="Z")
    with pytest.raises(ValueError, match="you have to specify either"):
        stri_subset_assign(["ab"], value="Z")
    with pytest.raises(ValueError, match="you have to specify either"):
        stri_subset_assign(["ab"], regex="a", fixed="a", value="Z")
    with pytest.raises(ValueError, match='argument "value" is missing'):
        stri_subset_assign(["ab"], fixed="a")
    with pytest.raises(TypeError, match="unused argument \\(nope = 1\\)"):
        stri_subset_assign(["ab"], fixed="a", value="Z", nope=1)
