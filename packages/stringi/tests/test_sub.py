"""Checks for stringi substring extract and replace."""

import sys
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from stringi._na import NA
from stringi.sub import (
    IndexMatrix,
    stri_sub,
    stri_sub_all,
    stri_sub_all_assign,
    stri_sub_all_replace,
    stri_sub_assign,
    stri_sub_replace,
    stri_sub_replace_all,
)


def test_from_to_length_na_empty_and_past_end():
    text = ["abcdef", "xy", "", NA, "z"]
    assert stri_sub(text, from_=1, to=3) == ["abc", "xy", "", NA, "z"]
    assert stri_sub(text, from_=-2, to=-1) == ["ef", "xy", "", NA, "z"]
    assert stri_sub(text, from_=10, to=12) == ["", "", "", NA, ""]
    assert stri_sub("", from_=1, to=1) == [""]
    assert stri_sub("", from_=-1) == [""]
    assert stri_sub(text, from_=[1, NA, 2, 1, NA], to=2) == ["ab", NA, "", NA, NA]
    assert stri_sub(text, from_=2, length=0) == ["", "", "", NA, ""]
    assert stri_sub(text, from_=2, length=-1) == [NA, NA, NA, NA, NA]
    assert stri_sub(text, from_=2, length=-1, ignore_negative_length=True) == [NA]
    assert stri_sub("hello", from_=-3, length=[1, 2, 3, 4, 10]) == [
        "l",
        "ll",
        "llo",
        "llo",
        "llo",
    ]
    assert stri_sub("abc", from_=5, to=4) == [""]
    assert stri_sub("abc", from_=-10, to=-1) == ["abc"]
    assert stri_sub("NA", from_=1, to=2) == ["NA"]


def test_code_points_and_bom():
    assert stri_sub("a\u0301e\u0301", from_=1, to=2) == ["a\u0301"]
    assert stri_sub("a\u0301e\u0301", from_=2, to=3) == ["\u0301e"]
    assert stri_sub("a😀b", from_=2, to=2) == ["😀"]
    assert stri_sub("\ufeffabc", from_=1, to=1) == ["a"]
    assert stri_sub("\ufeff", from_=1, to=1) == [""]
    assert stri_sub_replace("a\u0301e\u0301", from_=2, to=3, replacement="Z") == ["aZ\u0301"]


def test_matrix_and_use_matrix():
    assert stri_sub(["abcdef", "xyz"], from_=[[1, 3], [2, 4]]) == ["abc", "yz"]
    assert stri_sub(["abcdef", "xyz"], from_={"from": [1, 2], "length": [2, 1]}) == [
        "ab",
        "y",
    ]
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        assert stri_sub("hello", from_=2, to=3, length=2) == ["el"]
    assert any("argument `to` is ignored" in str(item.message) for item in caught)
    try:
        stri_sub("abcdef", from_=[[1, 3, 5], [2, 4, 6]])
    except ValueError as exc:
        assert "matrix with 2 columns" in str(exc)
    else:
        raise AssertionError("expected a matrix error")


def test_sub_all_replace_is_the_all_form():
    assert stri_sub_all_replace is stri_sub_replace_all


def test_single_and_all_replacement_differ_at_from_zero():
    assert stri_sub_replace("hello", from_=0, length=3, replacement="Q") == ["Qllo"]
    assert stri_sub_replace_all("hello", from_=0, length=3, replacement="Q") == ["Qlo"]
    assert stri_sub_replace("hello", from_=3, length=-2, replacement="XX") == ["hello"]
    assert stri_sub_replace_all("hello", from_=2, length=-3, replacement="XX") == ["hello"]
    assert stri_sub_replace("hello", from_=10, to=12, replacement="XX") == ["helloXX"]
    assert stri_sub_replace("hello", from_=3, to=1, replacement="XX") == ["heXXllo"]
    assert stri_sub_assign(["ab", "cd"], from_=1, to=1, value="Z") == ["Zb", "Zd"]
    assert stri_sub_replace("hello", from_=1, to=1, replacement="A", value="B") == ["Bello"]


def test_all_indexes_and_assign():
    assert stri_sub_all("a b c", from_=[1, 3, 5], to=[1, 3, 5]) == [["a", "b", "c"]]
    assert stri_sub_all(["abcd", "xyz"], from_=[[1, 3], [1, 2]], to=[[2, 4], [1, 2]]) == [
        ["ab", "cd"],
        ["x", "y"],
    ]
    assert stri_sub_all("hello", from_=1, length=-2) == [[]]
    assert stri_sub("hello", from_=1, length=-2) == [NA]
    replaced = stri_sub_replace_all(
        "a b c", from_=[1, 3, 5], to=[1, 3, 5], replacement=["A", "B", "C"]
    )
    assert replaced == ["A B C"]
    assert stri_sub_all_assign(
        "a b c", from_=[1, 3, 5], to=[1, 3, 5], value=["A", "B", "C"]
    ) == ["A B C"]
    try:
        stri_sub_replace_all("abcdef", from_=[1, 3], to=[4, 5], replacement=["A", "B"])
    except ValueError as exc:
        assert "sorted and mutually disjoint" in str(exc)
    else:
        raise AssertionError("expected an overlap error")
    assert stri_sub_replace_all(
        "abcdef", from_=[1, NA], to=[2, 4], replacement=["A", "B"], omit_na=True
    ) == ["Acdef"]
    assert (
        stri_sub_replace_all(
            "abcdef", from_=[1, NA], to=[2, 4], replacement=["A", "B"]
        )
        == [NA]
    )
    assert stri_sub_all(
        ["hello", "world"],
        from_=[IndexMatrix([[1, 2], [-1, 1]], colnames=("from", "length"))],
    ) == [["he", "o"], ["wo", "d"]]
