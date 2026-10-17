"""stringr detect, count, and subset against the 1.6.0 tests."""

import warnings

import lifecycle
import pytest
from stringi._na import NA

from stringr._size import RecycleError
from stringr.count import str_count
from stringr.detect import _Named, like_to_regex, str_detect, str_ends, str_ilike, str_like, str_starts, str_which
from stringr.pattern import boundary, coll, fixed, regex
from stringr.subset import str_subset


FRUIT = ["apple", "banana", "pear", "pineapple"]


def named(values, names):
    return _Named(values, names)


def test_detect_examples_and_vectorised_patterns():
    assert str_detect(FRUIT, "a") == [True, True, True, True]
    assert str_detect(FRUIT, "^a") == [True, False, False, False]
    assert str_detect(FRUIT, "a$") == [False, True, False, False]
    assert str_detect(FRUIT, "b") == [False, True, False, False]
    assert str_detect(FRUIT, "[aeiou]") == [True, True, True, True]
    assert str_detect(FRUIT, "^p", negate=True) == [True, True, False, False]
    assert str_detect("ab", ["a", "b", "c"]) == [True, True, False]
    assert str_detect(["ca", "ab"], ["a", "c"]) == [True, False]
    assert str_detect("ab", ["a", "b", "c"], negate=True) == [False, False, True]
    assert all(item is True or item is False for item in str_detect(FRUIT, "a"))


def test_detect_missing_and_empty():
    assert str_detect(NA, "x") == [NA]
    assert str_detect(["a", NA], "a") == [True, NA]
    assert str_detect([], "x") == []
    assert str_detect("x", []) == []
    assert str_detect([], []) == []


def test_starts_and_ends_group_the_anchor():
    assert str_starts(["ab", "ba"], "a") == [True, False]
    assert str_ends(["ab", "ba"], "a") == [False, True]
    assert str_starts(["ab", "ba"], "a", negate=True) == [False, True]
    assert str_ends(["ab", "ba"], "a", negate=True) == [True, False]
    assert str_starts(["ab", "ba", "cb"], "a|b") == [True, True, False]
    assert str_ends(["ab", "ba", "bc"], "a|b") == [True, True, False]
    assert str_starts(FRUIT, "p") == [False, False, True, True]
    assert str_ends(FRUIT, "e") == [True, False, False, True]
    assert str_starts("A", regex("a", ignore_case=True)) == [True]
    assert str_starts(["a\nb", "xb"], regex("b", multiline=True)) == [True, False]
    assert str_ends("a\nb", regex("a", multiline=True)) == [True]
    assert str_starts(["NA", "x", NA], regex(NA)) == [True, False, NA]


def test_fixed_and_collation():
    assert str_detect("X", fixed(".")) == [False]
    assert str_starts("X", fixed(".")) == [False]
    assert str_ends("X", fixed(".")) == [False]
    turkish = coll("I", ignore_case=True, locale="tr")
    assert str_detect("\u0131", turkish) == [True]
    assert str_starts("\u0131", turkish) == [True]
    assert str_ends("\u0131", turkish) == [True]
    assert str_starts("Apple", fixed("a", ignore_case=True)) == [True]
    assert str_ends("ab", fixed("B", ignore_case=True)) == [True]


def test_empty_and_boundary_are_rejected():
    with pytest.raises(ValueError, match="empty string"):
        str_detect("x", "")
    with pytest.raises(ValueError, match="empty string"):
        str_starts("x", "")
    with pytest.raises(ValueError, match="empty string"):
        str_ends("x", "")
    with pytest.raises(ValueError, match="boundary"):
        str_detect("x", boundary())
    with pytest.raises(ValueError, match="boundary"):
        str_subset(["a", "b c"], boundary())
    with pytest.raises(ValueError, match="NAs"):
        str_detect("a", NA)
    with pytest.raises(TypeError, match="character"):
        str_detect("a", 1)
    with pytest.raises(ValueError, match="TRUE"):
        str_detect("a", "b", negate=1)


def test_recycling_rules():
    with pytest.raises(RecycleError, match="size 2"):
        str_detect([1, 2], [1, 2, 3])
    with pytest.raises(RecycleError, match="size 2"):
        str_starts(["a", "b"], ["a", "b", "c"])
    with pytest.raises(RecycleError, match="size 2"):
        str_ends(["a", "b"], ["a", "b", "c"])
    with pytest.raises(RecycleError, match="size 2"):
        str_like(["a", "b"], ["a", "b", "c"])
    with pytest.raises(RecycleError, match="size 2"):
        str_count(["a", "b"], ["a", "b", "c"])


def test_names_follow_pattern_length():
    strings = named(["3", "2", "1"], ["C", "B", "A"])
    assert str_detect(strings, "[123]").names == ["C", "B", "A"]
    assert str_starts(strings, "1").names == ["C", "B", "A"]
    assert str_ends(strings, "1").names == ["C", "B", "A"]
    assert str_like(strings, "%").names == ["C", "B", "A"]
    assert str_ilike(strings, "%").names == ["C", "B", "A"]
    assert str_count(strings, ".").names == ["C", "B", "A"]

    scalar = named(["ab"], ["A"])
    assert type(str_detect(scalar, ["a", "b"])) is list
    assert type(str_starts(scalar, ["a", "b"])) is list
    assert type(str_like(scalar, ["a", "b"])) is list
    assert type(str_count(scalar, ["a", "b"])) is list

    pair = named(["ab", "cd"], ["A", "B"])
    assert str_detect(pair, ["a", "c"]).names == ["A", "B"]
    assert str_count(pair, ["a", "c"]).names == ["A", "B"]


def test_like_and_ilike():
    assert like_to_regex(["ab%", "ab_", "ab\\%", "ab[%]"]) == ["^ab.*$", "^ab.$", "^ab\\%$", "^ab[%]$"]
    assert str_like("abc", "ab%") == [True]
    assert str_like("abc", "AB%") == [False]
    assert str_ilike("abc", "ab%") == [True]
    assert str_ilike("abc", "AB%") == [True]
    assert str_like(FRUIT, "app") == [False, False, False, False]
    assert str_like(FRUIT, "app%") == [True, False, False, False]
    assert str_like(FRUIT, "ba_ana") == [False, True, False, False]
    assert str_like(FRUIT, "%apple") == [True, False, False, True]
    assert str_ilike(FRUIT, "APP%") == [True, False, False, False]
    patterns = ["ab\\%", "ab_", "a\\_b", "ab%", "100%", "a\\%b\\_c"]
    strings = ["ab%", "abX", "a_b", "abc", "100", "a%b_c"]
    assert str_like(strings, patterns) == [True, True, True, True, True, True]
    assert str_like(["NA", "x", NA], NA) == [True, False, NA]
    with pytest.raises(RuntimeError, match="plain string"):
        str_like("abc", regex("x"))
    with pytest.raises(RuntimeError, match="plain string"):
        str_ilike("abc", fixed("x"))
    with pytest.raises(TypeError, match="character"):
        str_like("a", 1)


def test_ignore_case_is_deprecated_and_still_selects_ilike():
    lifecycle._warned.clear()
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        assert str_like("abc", "AB%", ignore_case=True) == [True]
        assert str_like("abc", "AB%", ignore_case=False) == [False]
    assert len(caught) == 1
    message = str(caught[0].message)
    assert "ignore_case" in message
    assert "stringr 1.6.0" in message
    assert str_like("abc", "AB%") == [False]


def test_which_is_one_based_and_skips_missing():
    assert str_which(FRUIT, "a") == [1, 2, 3, 4]
    assert str_which(FRUIT, "^p", negate=True) == [1, 2]
    assert str_which(["a", NA, "b"], ".") == [1, 3]
    assert str_which(["a", "b", "c", "d", "e", "f"], "[aeiou]") == [1, 5]
    assert str_which(["a", "b", "c", "d", "e", "f"], "[aeiou]", negate=True) == [2, 3, 4, 6]
    assert str_which([], "a") == []
    assert all(type(item) is int for item in str_which(FRUIT, "a"))
    positions = str_which(named(["apple"], ["A"]), ["a", "x", "p"])
    assert positions == [1, 3]
    assert type(positions) is list
    found = str_which(named(["apple", "banana"], ["A", "B"]), "a")
    assert list(found) == [1, 2]
    assert found.names == ["A", "B"]
    missed = str_which(named(["x", "y"], ["A", "B"]), "z")
    assert list(missed) == []
    assert missed.names == []


def test_subset_keeps_matches_and_drops_missing():
    assert str_subset(["a", "b", "c"], "a|c") == ["a", "c"]
    assert str_subset(["a", "b", "c"], "a|c", negate=True) == ["b"]
    assert str_subset(["i", "I"], fixed("i")) == ["i"]
    assert str_subset(["i", "I"], fixed("i", ignore_case=True)) == ["i", "I"]
    assert str_subset(["i", "I"], fixed("i"), negate=True) == ["I"]
    assert str_subset(["x", "."], fixed(".")) == ["."]
    assert str_subset(["i", "\u0131"], coll("I", ignore_case=True, locale="tr")) == ["\u0131"]
    assert str_subset(FRUIT, "a") == FRUIT
    assert str_subset(FRUIT, "b") == ["banana"]
    assert str_subset(FRUIT, "^p", negate=True) == ["apple", "banana"]
    assert str_subset(["a", NA, "b"], ".") == ["a", "b"]
    assert str_subset(NA, ".") == []
    assert str_subset([], "x") == []
    fruit = named(FRUIT, ["A", "B", "C", "D"])
    assert str_subset(fruit, "b").names == ["B"]
    assert str_subset(fruit, "p").names == ["A", "C", "D"]
    assert str_subset(fruit, "x").names == []
    kept = str_subset(named(["3", "2", "1"], ["C", "B", "A"]), "[12]")
    assert list(kept) == ["2", "1"]
    assert kept.names == ["B", "A"]
    past = str_subset(named(["apple"], ["A"]), ["a", "b", "p"])
    assert list(past) == ["apple", NA]
    assert past.names == ["A", NA]
    assert str_subset("apple", ["a", "z", "p"]) == ["apple", NA]


def test_count_regex_fixed_coll_and_boundaries():
    assert str_count(FRUIT, "a") == [1, 3, 1, 1]
    assert str_count(FRUIT, "p") == [2, 0, 1, 3]
    assert str_count(FRUIT, "e") == [1, 0, 1, 2]
    assert str_count(FRUIT, ["a", "b", "p", "n"]) == [1, 1, 1, 1]
    assert str_count(["a.", "...", ".a.a"], ".") == [2, 3, 4]
    assert str_count(["a.", "...", ".a.a"], fixed(".")) == [1, 3, 2]
    assert str_count("x.", fixed(".")) == [1]
    assert str_count("\u0131", coll("I", ignore_case=True, locale="tr")) == [1]
    assert str_count("a b c", "") == [5]
    assert str_count("a b c", ("",)) == [5]
    assert str_count("a b c", boundary("word")) == [3]
    assert str_count(["abc", ""], boundary("character")) == [3, 0]
    assert str_count("Hello. World!", boundary("sentence")) == [2]
    assert str_count(NA, "a") == [NA]
    assert str_count([]) == []
    assert str_count(FRUIT) == [5, 6, 4, 9]
    assert all(type(item) is int for item in str_count(FRUIT, "a"))
    with pytest.raises(ValueError, match="empty string"):
        str_subset(["a", "b c"], "")
