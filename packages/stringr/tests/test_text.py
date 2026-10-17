"""Behavior that the stringr text wrappers must keep."""

import pytest
from rlang import Named
from stringi._na import NA
from stringi.sub import IndexMatrix

from stringr.dup import str_dup
from stringr.escape import str_conv, str_escape
from stringr.join import str_c, str_flatten, str_flatten_comma
from stringr.length import str_length, str_width
from stringr.sub import str_sub, str_sub_all, str_sub_assign


def test_length_and_width_are_lists():
    assert str_length("abc") == [3]
    assert str_length(NA) == [NA]
    assert str_length(NA)[0] is NA
    assert str_length("NA") == [2]
    assert str_length(None) == []
    assert str_length([]) == []
    assert str_length(["\u00fc", "u\u0308"]) == [1, 2]
    assert str_width(["\u00fc", "u\u0308"]) == [1, 1]
    assert str_width(["\u6c49\u5b57", "\U0001f60a"]) == [4, 2]
    assert str_length([True, False]) == [4, 5]
    named = str_length(Named(["ab", NA], ["a", "b"]))
    assert list(named) == [2, NA]
    assert named.names == ["a", "b"]


def test_dup_recycles_and_paste_keeps_na_letters():
    assert str_dup(["apple", "pear"], 2) == ["appleapple", "pearpear"]
    assert str_dup(["a", NA], 2) == ["aa", NA]
    assert str_dup(["a", NA], 2, sep="-") == ["a-a", "NA-NA"]
    assert str_dup(["a", NA], 0, sep="-") == ["", ""]
    assert str_dup("ab", 2.9) == ["abab"]
    assert str_dup(None, [1, 2, 3]) == []
    assert str_dup("a", None) == []
    assert str_dup([], 1) == []
    named = str_dup(Named(["ab"], ["a"]), [1, 2, 3])
    assert list(named) == ["ab", "abab", "ababab"]
    assert named.names == ["a", "a", "a"]
    with pytest.raises(ValueError, match="subscript out of bounds"):
        str_dup("ab", [1, 2, 3], sep="-")
    with pytest.raises(ValueError, match="invalid 'times' argument"):
        str_dup("a", -1, sep="-")
    with pytest.raises(ValueError, match="Can't recycle `string`"):
        str_dup([], [1, 2, 3])
    with pytest.raises(ValueError, match="Can't recycle `string` \\(size 2\\)"):
        str_dup(["a", "b"], [])


def test_c_drops_null_and_rejects_a_bad_size():
    assert str_c(None, "a", None, "b") == ["ab"]
    assert str_c() == []
    assert str_c("x", []) == []
    assert str_c(["a", NA, "b"], "-d") == ["a-d", NA, "b-d"]
    assert str_c(["a", NA, "b"], "-d")[1] is NA
    assert str_c(list("abc"), collapse=", ") == ["a, b, c"]
    assert str_c(collapse=",") == [""]
    with pytest.raises(ValueError, match="Can't recycle `..1` \\(size 2\\)"):
        str_c([1, 2], [1, 2, 3])
    with pytest.raises(ValueError, match="`sep` must be a single string, not a character vector"):
        str_c("a", sep=["b", "c"])
    with pytest.raises(ValueError, match="`collapse` must be a single string or `NULL`, not `NA`"):
        str_c("a", collapse=NA)


def test_flatten_and_the_oxford_comma():
    assert str_flatten(list("abc"), ", ", " and ") == ["a, b and c"]
    assert str_flatten(list("ab"), ", ", ", and ") == ["a, and b"]
    assert str_flatten_comma(list("abc"), ", and ") == ["a, b, and c"]
    assert str_flatten_comma(list("ab"), ", and ") == ["a and b"]
    assert str_flatten_comma(list("ab"), ",") == ["ab"]
    assert str_flatten(["a", NA, "b"]) == [NA]
    assert str_flatten(["a", NA, "b"], na_rm=True) == ["ab"]
    assert str_flatten_comma(["a", NA], ", and ", na_rm=True) == ["a"]
    assert str_flatten(None) == [""]
    assert str_flatten([NA, NA], na_rm=True) == [""]
    with pytest.raises(ValueError, match="`na.rm` must be `TRUE` or `FALSE`, not `NA`"):
        str_flatten("a", na_rm=NA)


def test_sub_positions_matrix_and_replacement():
    hw = "Hadley Wickham"
    assert str_sub(hw, 1, 6) == ["Hadley"]
    assert str_sub(hw, end=6) == ["Hadley"]
    assert str_sub(hw, -1) == ["m"]
    assert str_sub(hw, [1, 8], [6, 14]) == ["Hadley", "Wickham"]
    assert str_sub(["abcde", "ghifgh"], [1, 2], [2, 4]) == ["ab", "hif"]
    assert str_sub_all(["abcde", "ghifgh"], [1, 2], [2, 4]) == [
        ["ab", "bcd"],
        ["gh", "hif"],
    ]
    assert str_sub(hw, [[2, 5], [6, 7]]) == ["adle", "y "]
    assert str_sub("abcdef", {"start": [1, 2], "length": [3, 2]}) == ["abc", "bc"]
    assert str_sub_all(
        ["abcde", "ghifgh"],
        IndexMatrix([[2, 5], [6, 7]], colnames=("start", "end")),
    ) == [["bcde", ""], ["hifg", "h"]]
    assert str_sub_all(["abcdef", "ghijkl"], [[1, 3], [2, 4]], -1) == [
        ["abcdef", "cdef"],
        ["hijkl", "jkl"],
    ]
    assert str_sub("abc", 3, 1) == [""]
    assert str_sub("abc", NA, 2) == [NA]
    named = str_sub(Named(["abcdef"], ["a"]), [1, 2], [2, 3])
    assert named == ["ab", "bc"]
    assert not hasattr(named, "names") or named.names is None or getattr(named, "names", None) in (None, [])
    text = "BBCDEF"
    text = str_sub_assign(text, 1, 1, "A")
    text = str_sub_assign(text, -1, -1, "K")
    text = str_sub_assign(text, -2, -2, "GHIJ")
    text = str_sub_assign(text, 2, -2, "")
    assert text == ["AK"]
    assert str_sub_assign("abcdef", NA, 2, "Z", omit_na=True) == ["abcdef"]
    assert str_sub_assign("abcdef", NA, 2, "Z") == [NA]
    assert str_sub_assign(["abcdef", "ghijkl"], [[1, 2], [2, 3]], value=["X", "YZ"]) == [
        "Xcdef",
        "gYZjkl",
    ]
    with pytest.raises(ValueError, match="Can't recycle `start`"):
        str_sub(hw, [[2, 5], [6, 7]], end=[1, 2, 3])
    with pytest.raises(ValueError, match='argument "value" is missing'):
        str_sub_assign("abc")


def test_escape_and_conv():
    assert str_escape(".") == ["\\."]
    assert str_escape(["a.b", NA, ""]) == ["a\\.b", NA, ""]
    assert str_escape(".^$\\|*+?{}[]()") == ["\\.\\^\\$\\\\\\|\\*\\+\\?\\{\\}\\[\\]\\(\\)"]
    raw = bytes([177])
    assert str_conv(raw, "ISO-8859-2") == ["\u0105"]
    assert str_conv(raw, "ISO-8859-1") == ["\u00b1"]
    assert str_conv(None, "UTF-8") == [NA]
    assert str_conv([], "UTF-8") == []
    named = str_conv(Named(["a"], ["p"]), "UTF-8")
    assert list(named) == ["a"]
    assert named.names == ["p"]
    with pytest.raises(ValueError, match="U_FILE_ACCESS_ERROR"):
        str_conv("a", "not-an-encoding")
