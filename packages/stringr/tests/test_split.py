"""stringr 1.6.0 split functions, checked against the installed R results."""

from __future__ import annotations

import pytest

from stringi._na import NA
from stringr._size import RecycleError
from stringr.pattern import boundary, coll, fixed, regex
from stringr.split import str_split, str_split_1, str_split_fixed, str_split_i


FRUITS = [
    "apples and oranges and pears and bananas",
    "pineapples and mangos and guavas",
]


def test_manual_examples():
    assert str_split(FRUITS, " and ") == [
        ["apples", "oranges", "pears", "bananas"],
        ["pineapples", "mangos", "guavas"],
    ]
    assert str_split(FRUITS, " and ", simplify=True) == [
        ["apples", "oranges", "pears", "bananas"],
        ["pineapples", "mangos", "guavas", ""],
    ]
    assert str_split_1(FRUITS[0], " and ") == ["apples", "oranges", "pears", "bananas"]
    assert str_split(FRUITS, " and ", n=3) == [
        ["apples", "oranges", "pears and bananas"],
        ["pineapples", "mangos", "guavas"],
    ]
    assert str_split(FRUITS, " and ", n=2) == [
        ["apples", "oranges and pears and bananas"],
        ["pineapples", "mangos and guavas"],
    ]
    assert str_split(FRUITS, " and ", n=5) == [
        ["apples", "oranges", "pears", "bananas"],
        ["pineapples", "mangos", "guavas"],
    ]
    assert str_split_fixed(FRUITS, " and ", 3) == [
        ["apples", "oranges", "pears and bananas"],
        ["pineapples", "mangos", "guavas"],
    ]
    assert str_split_fixed(FRUITS, " and ", 4) == [
        ["apples", "oranges", "pears", "bananas"],
        ["pineapples", "mangos", "guavas", ""],
    ]
    assert str_split_i(FRUITS, " and ", 1) == ["apples", "pineapples"]
    assert str_split_i(FRUITS, " and ", 4) == ["bananas", NA]
    assert str_split_i(FRUITS, " and ", -1) == ["bananas", "guavas"]


def test_special_cases_and_pattern_kinds():
    assert str_split(NA, "") == [[NA]]
    assert str_split([], "") == []
    assert str_split(["bab", "cac", "dadad"], "a") == [["b", "b"], ["c", "c"], ["d", "d", "d"]]
    assert str_split("ab", "") == [["a", "b"]]
    assert str_split("ab", ("",)) == [["a", "b"]]
    assert str_split(["ab", "cd"], "") == [["a", "b"], ["c", "d"]]
    assert str_split("", "") == [[]]
    assert str_split("", "a") == [[""]]
    assert str_split("é你", "") == [["é", "你"]]
    assert str_split("this that.", boundary("word")) == [["this", "that"]]
    assert str_split(["x", "y"], boundary()) == [["x"], ["y"]]
    assert str_split("These are   some words.", boundary("word")) == [["These", "are", "some", "words"]]
    assert str_split("Hello. Bye.", boundary("sentence")) == [["Hello. ", "Bye."]]
    assert str_split("a\nb", boundary("line_break")) == [["a\n", "b"]]
    assert str_split("a-b", fixed("-")) == [["a", "b"]]
    assert str_split("aXb", coll("X", ignore_case=True)) == [["a", "b"]]
    assert str_split("straße", coll("ss", locale="de", strength=1)) == [["stra", "e"]]
    assert str_split("aXb", fixed("x", ignore_case=True)) == [["a", "b"]]
    assert str_split("aXb", regex("x", ignore_case=True)) == [["a", "b"]]
    assert str_split("a\nb\nc", regex("^.", multiline=True)) == [["", "\n", "\n", ""]]
    assert str_split("a\nb\nc", regex("^.")) == [["", "\nb\nc"]]
    assert str_split("ab", regex("a # comment\n b", comments=True)) == [["", ""]]
    assert str_split("a\nb", regex(".", dotall=True)) == [["", "", "", ""]]
    assert str_split(["a", NA], boundary("word")) == [["a"], [NA]]
    assert str_split(None, "a") == []
    assert str_split(None, "") == []


def test_n_simplify_and_padding():
    assert str_split(["a", "a-b"], "-", n=1) == [["a"], ["a-b"]]
    assert str_split(["a", "a-b"], "-", n=3) == [["a"], ["a", "b"]]
    assert str_split(["a", "a-b"], "-", n=5) == [["a"], ["a", "b"]]
    assert str_split("a-b-c", "-", n=float("inf")) == [["a", "b", "c"]]
    assert str_split("a-b-c", "-", n=2.0) == [["a", "b-c"]]
    assert str_split("a--b", "-") == [["a", "", "b"]]
    assert str_split(["ab", "cd"], ["a", "b"]) == [["", "b"], ["cd"]]
    assert str_split(["a", "b-c"], "-", n=3, simplify=NA) == [["a", NA, NA], ["b", "c", NA]]
    assert str_split(["a", "b-c"], "-", n=3, simplify=True) == [["a", "", ""], ["b", "c", ""]]
    assert str_split("", "", simplify=NA) == [[]]
    assert str_split([], "-", simplify=True) == []
    assert str_split_fixed(["a", "a-b"], "-", 1) == [["a"], ["a-b"]]
    assert str_split_fixed(["a", "a-b"], "-", 2) == [["a", ""], ["a", "b"]]
    assert str_split_fixed(["a", "a-b"], "-", 3) == [["a", "", ""], ["a", "b", ""]]
    assert str_split_fixed(["a"], "-", 3) == [["a", "", ""]]
    assert str_split_fixed("", "", 2) == [["", ""]]
    assert str_split_fixed("a-b-c", "-", float("inf")) == [["a", "b", "c"]]
    assert str_split_fixed([], "-", 2) == []


def test_split_1_and_i():
    assert str_split_1("abc", "") == ["a", "b", "c"]
    assert str_split_1(["abc"], "") == ["a", "b", "c"]
    assert str_split_1("", "") == []
    assert str_split_i(["1-2-3", "4-5"], "-", 1) == ["1", "4"]
    assert str_split_i(["1-2-3", "4-5"], "-", -1) == ["3", "5"]
    assert str_split_i(["a", "b-c"], "-", 2) == [NA, "c"]
    assert str_split_i(["a", "b-c"], "-", 3) == [NA, NA]
    assert str_split_i(["1-2-3", "4-5"], "-", -3) == ["1", NA]
    assert str_split_i(["1-2-3", "4-5"], "-", -4) == [NA, NA]
    assert str_split_i(["a"], "-", 3) == [NA]
    assert str_split_i("", "", 1) == [NA]
    assert str_split_i("", "", -1) == [NA]
    assert str_split_i([NA, "a-b"], "-", 1) == [NA, "a"]
    assert str_split_i([NA, "a-b"], "-", 2) == [NA, "b"]
    assert str_split_i(NA, "-", -1) == [NA]
    assert str_split_i(["ab", "cd"], ["a", "b"], 1) == ["", "cd"]
    assert str_split_i(["ab"], ["a", "b"], 1) == ["", "a"]
    assert str_split_i("ab", "", 2) == ["b"]
    assert str_split_i("a", "", -1) == ["a"]
    assert str_split_i("a-b-c", "-", -1.0) == ["c"]
    assert str_split_i([], "-", 1) == []
    assert str_split_i([], "-", -1) == []


def test_empty_patterns_warn():
    with pytest.warns(UserWarning, match="empty search patterns are not supported"):
        assert str_split("ab", fixed("")) == [[NA]]
    with pytest.warns(UserWarning, match="empty search patterns are not supported"):
        assert str_split("ab", ["", ""]) == [[NA], [NA]]


def test_input_checks():
    with pytest.raises(RecycleError, match=r"Can't recycle `string` \(size 3\) to match `pattern` \(size 2\)"):
        str_split(["a", "b", "c"], ["a", "b"])
    with pytest.raises(RecycleError, match=r"size 0"):
        str_split([], ["a", "b"])
    with pytest.raises(TypeError, match="pattern must be a character vector"):
        str_split("x", 1)
    with pytest.raises(ValueError, match="pattern can not contain NAs"):
        str_split("x", NA)
    with pytest.raises(ValueError, match="pattern can not contain NAs"):
        str_split("x", ["a", NA])
    with pytest.raises(ValueError, match="`n` must be a number larger than 1, not the number 0"):
        str_split("x", "x", n=0)
    with pytest.raises(ValueError, match="`n` must be a number larger than 1, not the number -1"):
        str_split("x", "x", n=-1)
    with pytest.raises(ValueError, match="`n` must be a whole number, not the number 1.5"):
        str_split("x", "x", n=1.5)
    with pytest.raises(ValueError, match="`n` must be a whole number, not `TRUE`"):
        str_split("x", "x", n=True)
    with pytest.raises(ValueError, match="`n` must be a whole number, not `NA`"):
        str_split("a", "-", n=NA)
    with pytest.raises(ValueError, match="number 0"):
        str_split("x", 1, n=0)
    with pytest.raises(ValueError, match="`simplify` must be `TRUE`, `FALSE`, or `NA`, not the number 1"):
        str_split("x", "x", simplify=1)
    with pytest.raises(ValueError, match="character vector"):
        str_split_1(["a", "b"], "")
    with pytest.raises(ValueError, match="empty character vector"):
        str_split_1([], "")
    with pytest.raises(ValueError, match="character `NA`"):
        str_split_1(NA, "")
    with pytest.raises(IndexError, match="subscript out of bounds"):
        str_split_1("abc", [])
    with pytest.raises(ValueError, match="`n` must be a number larger than 1, not the number 0"):
        str_split_fixed("x", "x", 0)
    with pytest.raises(ValueError, match="`i` must not be 0"):
        str_split_i("x", "x", 0)
    with pytest.raises(ValueError, match="`i` must not be 0"):
        str_split_i(1, 1, 0)
    with pytest.raises(ValueError, match="`i` must be a whole number, not the number 0.5"):
        str_split_i("x", "x", 0.5)
    with pytest.raises(ValueError, match="`i` must be a whole number, not `Inf`"):
        str_split_i("a", "-", float("inf"))
    with pytest.raises(ValueError, match="`i` must be a whole number, not `NA`"):
        str_split_i("a", "-", NA)
