"""stringr sort, order, rank, unique, and equal."""

import pytest

from stringi._na import NA
from stringr._size import RecycleError
from stringr.equal import str_equal
from stringr.sort import str_order, str_rank, str_sort
from stringr.unique import str_unique


def test_sort_examples_and_edges():
    words = ["apple", "car", "happy", "char"]
    assert str_sort(words) == ["apple", "car", "char", "happy"]
    assert str_sort(words, locale="cs") == ["apple", "car", "happy", "char"]
    numbers = ["100a10", "100a5", "2b", "2a"]
    assert str_sort(numbers) == ["100a10", "100a5", "2a", "2b"]
    assert str_sort(numbers, numeric=True) == ["2a", "2b", "100a5", "100a10"]
    assert str_sort(["a", "A", "b", "B"]) == ["a", "A", "b", "B"]
    assert str_sort(["a", "A", "b", "B"], uppercase_first=True) == ["A", "a", "B", "b"]
    assert str_sort(["a", "c", "b"], decreasing=True) == ["c", "b", "a"]
    assert str_sort(["b", NA, "a"], na_last=False) == [NA, "a", "b"]
    assert str_sort(["b", NA, "a"], na_last=NA) == ["a", "b"]
    assert str_sort(["\ufeffabc", "abc", "b", NA, "a"]) == ["a", "\ufeffabc", "abc", "b", NA]
    assert str_sort([10, 2, 1]) == [1, 10, 2]
    assert str_sort([True, False, True]) == [False, True, True]
    assert str_sort(NA) == [NA]
    assert str_sort(NA, na_last=NA) == []
    assert str_sort([]) == []
    assert str_sort(None) is None
    assert str_sort(["cote", "coté", "côte", "côté"], french=True) == [
        "cote",
        "côte",
        "coté",
        "côté",
    ]


def test_order_and_rank():
    words = ["apple", "car", "happy", "char"]
    assert str_order(words) == [1, 2, 4, 3]
    assert str_rank(words) == [1, 2, 4, 3]
    assert str_order(words, locale="cs") == [1, 2, 3, 4]
    assert str_rank(words, locale="cs") == [1, 2, 3, 4]
    digits = ["2", "1", "10"]
    assert str_order(digits) == [2, 3, 1]
    assert str_order(digits, numeric=True) == [2, 1, 3]
    assert str_rank(digits) == [3, 1, 2]
    assert str_rank(digits, numeric=True) == [2, 1, 3]
    assert str_order(["b", "a", "b", "a"]) == [2, 4, 1, 3]
    assert str_rank(["b", "a", "b", "a", NA]) == [3, 1, 3, 1, NA]
    assert str_order(["b", NA, "a"], na_last=False) == [2, 3, 1]
    assert str_order(["b", NA, "a"], na_last=True) == [3, 1, 2]
    assert str_order(["b", NA, "a"], na_last=NA) == [3, 1]
    assert str_order(["a", "b", "a"], decreasing=True) == [2, 1, 3]
    assert str_order(["\ufeffabc", "abc", "b", NA, "a"]) == [5, 1, 2, 3, 4]
    assert str_rank([10, 2, 1]) == [2, 3, 1]
    assert str_rank([NA, "a", NA]) == [NA, 1, NA]
    assert str_order(NA, na_last=NA) == []
    assert str_order([]) == []
    assert str_rank([]) == []
    assert str_order(None) == []
    assert str_rank(None) == []


def test_unique():
    assert str_unique(["a", "b", "c", "b", "a"]) == ["a", "b", "c"]
    assert str_unique(["a", "b", "c", "B", "A"]) == ["a", "b", "c", "B", "A"]
    assert str_unique(["a", "b", "c", "B", "A"], ignore_case=True) == ["a", "b", "c"]
    assert str_unique(["a", "A"], ignore_case=True) == ["a"]
    assert str_unique(["a", "A"], ignore_case=True, strength=3) == ["a", "A"]
    assert str_unique(["a", "A"], strength=2) == ["a"]
    motley = ["motley", "mötley", "pinguino", "pingüino"]
    assert str_unique(motley) == motley
    assert str_unique(motley, strength=1) == ["motley", "pinguino"]
    assert str_unique(["\ufeffa", "a", "A", NA, NA]) == ["\ufeffa", "A", NA]
    assert str_unique([NA, NA]) == [NA]
    assert str_unique(["02", "2", "10", "10", "2"], numeric=True) == ["02", "10"]
    assert str_unique(["02", "2", "10"]) == ["02", "2", "10"]
    assert str_unique([1, 1, 2]) == [1, 2]
    assert str_unique([]) == []
    assert str_unique(None) is None


def test_equal():
    assert str_equal("\u00e1", "a\u0301") == [True]
    assert str_equal("\u2126", "\u03a9") == [True]
    assert str_equal("a", "A") == [False]
    assert str_equal("a", "A", ignore_case=True) == [True]
    assert str_equal("a", "A", strength=1) == [True]
    assert str_equal("a", "A", ignore_case=True, strength=3) == [False]
    assert str_equal("a", ["a", "b"]) == [True, False]
    assert str_equal(["a", "b", "A"], ["A", "b", "a"], ignore_case=True) == [True, True, True]
    assert str_equal("a", []) == []
    assert str_equal([], "a") == []
    assert str_equal([], []) == []
    assert str_equal(["a", NA], ["a", "a"]) == [True, NA]
    assert str_equal(NA, "a") == [NA]
    assert str_equal("\ufeffa", "a") == [True]
    assert str_equal("02", "2", numeric=True) == [True]
    assert str_equal("02", "2") == [False]
    assert str_equal(True, "TRUE") == [True]
    assert str_equal(None, ["a", "b"]) == []
    assert str_equal(["a", "b"], None) == []
    assert str_equal(None, None) == []
    with pytest.raises(RecycleError, match=r"Can't recycle `x` \(size 3\) to match `y` \(size 2\)"):
        str_equal(["a", "b", "c"], ["a", "b"])
    with pytest.raises(RecycleError, match=r"Can't recycle `x` \(size 0\) to match `y` \(size 3\)"):
        str_equal([], ["a", "b", "c"])


def test_argument_checks():
    with pytest.raises(ValueError, match="decreasing"):
        str_sort(["a"], decreasing=1)
    with pytest.raises(ValueError, match="na_last"):
        str_order(["a"], na_last=1)
    with pytest.raises(ValueError, match="locale"):
        str_rank(["a"], locale=["en"])
    with pytest.raises(ValueError, match="numeric"):
        str_sort(["a"], numeric=NA)
    with pytest.raises(ValueError, match="ignore_case"):
        str_unique(["a"], ignore_case="yes")
    with pytest.raises(ValueError, match="locale"):
        str_equal("a", "a", locale=1)
    with pytest.raises(TypeError, match="unused argument"):
        str_sort(["b", "a"], foo=1)
    with pytest.raises(RecycleError):
        str_equal(["a", "b", "c"], ["a", "b"], locale=1)
