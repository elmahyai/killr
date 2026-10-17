"""Locations, extracts, and capture groups against the stringr 1.6.0 examples."""

from __future__ import annotations

import pytest

from stringi._na import NA
from stringr._size import RecycleError
from stringr.extract import str_extract, str_extract_all
from stringr.locate import invert_match, str_locate, str_locate_all
from stringr.match import str_match, str_match_all
from stringr.pattern import boundary, coll, fixed, regex


class Named(list):
    def __init__(self, values, names):
        super().__init__(values)
        self.names = names


FRUIT = ["apple", "banana", "pear", "pineapple"]


def test_locate_first_match_and_zero_length_end():
    assert str_locate("abc", "b") == [[2, 2]]
    assert str_locate(FRUIT, "$") == [[6, 5], [7, 6], [5, 4], [10, 9]]
    assert str_locate(FRUIT, "a") == [[1, 1], [2, 2], [3, 3], [5, 5]]
    assert str_locate(FRUIT, "e") == [[5, 5], [NA, NA], [2, 2], [4, 4]]
    assert str_locate(FRUIT, ["a", "b", "p", "p"]) == [[1, 1], [1, 1], [1, 1], [1, 1]]
    assert str_locate("a\U0001f600b", "b") == [[3, 3]]


def test_locate_all_omits_the_miss():
    assert str_locate_all(FRUIT, "a") == [
        [[1, 1]],
        [[2, 2], [4, 4], [6, 6]],
        [[3, 3]],
        [[5, 5]],
    ]
    assert str_locate_all(FRUIT, "e")[1] == []
    assert str_locate_all("abc", "") == [[[1, 1], [2, 2], [3, 3]]]
    assert str_locate_all(["abab"], ["a", "b"]) == [[[1, 1], [3, 3]], [[2, 2], [4, 4]]]


def test_locate_fixed_coll_and_boundary():
    assert str_locate("x.x", fixed(".")) == [[2, 2]]
    assert str_locate_all("x.x.", fixed(".")) == [[[2, 2], [4, 4]]]
    turkish = coll("I", ignore_case=True, locale="tr")
    assert str_locate("\u0131", turkish) == [[1, 1]]
    assert str_locate_all("\u0131I", turkish) == [[[1, 1], [2, 2]]]
    assert str_locate(" x  y", "") == [[1, 1]]
    assert str_locate(" xy", boundary("word")) == [[2, 3]]
    assert str_locate_all(" ab  cd", boundary("word")) == [[[2, 3], [6, 7]]]


def test_locate_recycling_and_names():
    with pytest.raises(RecycleError, match="Can't recycle `string`"):
        str_locate(["a", "b"], ["a", "b", "c"])
    with pytest.raises(RecycleError, match="Can't recycle `string`"):
        str_locate_all([1, 2], [1, 2, 3])
    named = Named(["3", "2", "1"], ["C", "B", "A"])
    located = str_locate(named, "[0-9]")
    assert located.names == ["C", "B", "A"]
    assert str_locate_all(named, "[0-9]").names == ["C", "B", "A"]
    assert getattr(str_locate(Named(["ab"], ["A"]), ["a", "b"]), "names", None) is None
    both = str_locate(Named(["abc", "def"], ["A", "B"]), ["a", "d"])
    assert both.names == ["A", "B"]
    assert both == [[1, 1], [1, 1]]


def test_invert_match_follows_the_cbind():
    loc = str_locate_all("1 and 2 and 4 and 456", "[0-9]+")[0]
    assert loc == [[1, 1], [7, 7], [13, 13], [19, 21]]
    assert invert_match(loc) == [[0, 0], [2, 6], [8, 12], [14, 18], [22, -1]]
    assert invert_match([]) == [[0, -1]]
    assert invert_match([[NA, NA]]) == [[0, NA], [NA, -1]]
    assert invert_match([[1, 2], [NA, NA]]) == [[0, 0], [3, NA], [NA, -1]]
    assert invert_match({"start": [1, 19], "end": [1, 21]}) == [[0, 0], [2, 18], [22, -1]]


def test_extract_first_group_and_engines():
    shopping = ["apples x4", "bag of flour", "bag of sugar", "milk x2"]
    assert str_extract(shopping, r"\d") == ["4", NA, NA, "2"]
    assert str_extract(shopping, "[a-z]+") == ["apples", "bag", "bag", "milk"]
    assert str_extract(shopping, r"\b[a-z]{1,4}\b") == [NA, "bag", "bag", "milk"]
    assert str_extract(shopping, "([a-z]+) of ([a-z]+)") == [
        NA,
        "bag of flour",
        "bag of sugar",
        NA,
    ]
    assert str_extract(shopping, "([a-z]+) of ([a-z]+)", group=1) == [NA, "bag", "bag", NA]
    assert str_extract(shopping, "([a-z]+) of ([a-z]+)", group=2) == [
        NA,
        "flour",
        "sugar",
        NA,
    ]
    assert str_extract("abc", "(.).(.)", group=1) == ["a"]
    assert str_extract("abc", "(.).(.)", group=2) == ["c"]
    assert str_extract("abc", "(.).(.)", group=0) == ["abc"]
    assert str_extract("abc", "(a)", group=[1, 0]) == ["a", "a"]
    assert str_extract("x.x", fixed(".")) == ["."]
    assert str_extract("\u0131", coll("I", ignore_case=True, locale="tr")) == ["\u0131"]
    assert str_extract("a b c", "") == ["a"]
    assert str_extract("a b c", boundary("word")) == ["a"]
    assert str_extract("Cat", "[a-z]+") == ["at"]
    assert str_extract("Cat", regex("[a-z]+", ignore_case=True)) == ["Cat"]
    named = str_extract(Named(["abc", "xyz"], ["A", "B"]), "(a)|(x)", group=1)
    assert named == ["a", NA]
    assert named.names == ["A", "B"]


def test_extract_all_and_simplify():
    shopping = ["apples x4", "bag of flour", "bag of sugar", "milk x2"]
    assert str_extract_all(shopping, "[a-z]+") == [
        ["apples", "x"],
        ["bag", "of", "flour"],
        ["bag", "of", "sugar"],
        ["milk", "x"],
    ]
    assert str_extract_all(shopping, r"\d") == [["4"], [], [], ["2"]]
    assert str_extract_all("a", "b") == [[]]
    assert str_extract_all(shopping, r"\b[a-z]+\b", simplify=True) == [
        ["apples", "", ""],
        ["bag", "of", "flour"],
        ["bag", "of", "sugar"],
        ["milk", "", ""],
    ]
    assert str_extract_all(shopping, r"\d", simplify=True) == [["4"], [""], [""], ["2"]]
    assert str_extract_all(["a", "b"], "z", simplify=True) == [[], []]
    assert str_extract_all("a b c", "") == [["a", " ", "b", " ", "c"]]
    assert str_extract_all("a b c", boundary("word")) == [["a", "b", "c"]]
    assert str_extract_all("x.x.", fixed(".")) == [[".", "."]]
    assert str_extract_all("\u0131I", coll("I", ignore_case=True, locale="tr")) == [
        ["\u0131", "I"]
    ]
    words = str_extract_all("This is, suprisingly, a sentence.", boundary("word"))
    assert words == [["This", "is", "suprisingly", "a", "sentence"]]
    with pytest.raises(ValueError, match="TRUE"):
        str_extract_all("a", "a", simplify=1)
    with pytest.raises(RecycleError):
        str_extract(["a", "b"], ["a", "b", "c"])


def test_match_matrix_and_optional_groups():
    assert str_match(NA, "(a)") == [[NA, NA]]
    assert str_match([], "(a)") == []
    assert str_match(["a", "b"], ".") == [["a"], ["b"]]
    phones = ["(123) 456 7890", "blah", NA]
    matched = str_match(phones, r"\(([0-9]{3})\) ([0-9]{3}) ([0-9]{4})")
    assert matched[0] == ["(123) 456 7890", "123", "456", "7890"]
    assert matched[1] == [NA, NA, NA, NA]
    assert matched[2] == [NA, NA, NA, NA]
    assert str_match(["ab", "a"], "(a)(b)?") == [["ab", "a", "b"], ["a", "a", NA]]
    assert str_match_all("a", "(a)(b)?") == [[["a", "a", NA]]]
    tags = str_match(["<a> <b>", "<a> <>", "<a>", "", NA], "<(.*?)> <(.*?)>")
    assert tags[0] == ["<a> <b>", "a", "b"]
    assert tags[1] == ["<a> <>", "a", ""]
    assert tags[2] == [NA, NA, NA]
    assert tags[4] == [NA, NA, NA]
    every = str_match_all(["<a> <b>", "<a> <>", "<a>", "", NA], "<(.*?)>")
    assert every[0] == [["<a>", "a"], ["<b>", "b"]]
    assert every[1] == [["<a>", "a"], ["<>", ""]]
    assert every[3] == []
    assert every[4] == [[NA, NA]]
    named = str_match("219 733 8965", "(?<area>[0-9]{3}) (?<phone>[0-9]{3} [0-9]{4})")
    assert named == [["219 733 8965", "219", "733 8965"]]
    assert named.colnames == ["", "area", "phone"]
    with pytest.raises(ValueError, match="regular expression"):
        str_match("x", fixed("x"))
    with pytest.raises(ValueError, match="regular expression"):
        str_match_all("x", coll("y"))
    with pytest.raises(ValueError, match="regular expression"):
        str_match("x", "")
    with pytest.raises(ValueError, match="regular expression"):
        str_match("x", boundary("word"))
    with pytest.raises(RecycleError):
        str_match(["a", "b"], ["a", "b", "c"])
    labelled = Named(["3", "2", "1"], ["C", "B", "A"])
    assert str_match(labelled, "([0-9])").names == ["C", "B", "A"]
    assert str_match_all(labelled, "([0-9])").names == ["C", "B", "A"]
