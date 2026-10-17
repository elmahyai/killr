"""Dispatchers choose one finished mode function and forward the rest."""

from __future__ import annotations

import pytest

from stringi._na import NA
from stringi.charclass import stri_detect_charclass, stri_startswith_charclass
from stringi.coll import stri_count_coll, stri_extract_first_coll
from stringi.dispatch import (
    stri_count,
    stri_detect,
    stri_endswith,
    stri_extract,
    stri_extract_all,
    stri_extract_first,
    stri_extract_last,
    stri_locate,
    stri_locate_all,
    stri_locate_first,
    stri_locate_last,
    stri_replace,
    stri_replace_all,
    stri_replace_first,
    stri_replace_last,
    stri_split,
    stri_startswith,
    stri_subset,
)
from stringi.fixed import (
    stri_count_fixed,
    stri_detect_fixed,
    stri_endswith_fixed,
    stri_extract_last_fixed,
    stri_locate_all_fixed,
    stri_locate_first_fixed,
    stri_locate_last_fixed,
    stri_replace_all_fixed,
    stri_replace_first_fixed,
    stri_replace_last_fixed,
    stri_split_fixed,
    stri_startswith_fixed,
    stri_subset_fixed,
)
from stringi.regex import (
    stri_count_regex,
    stri_extract_all_regex,
    stri_extract_first_regex,
    stri_locate_all_regex,
    stri_split_regex,
    stri_subset_regex,
)

_NEED = "you have to specify either `regex`, `fixed`, `coll`, or `charclass`"
_NEED_OF = "you have to specify one of: `regex`, `fixed`, `coll`, or `charclass`"
_NEED_EDGE = "you have to specify either `fixed`, `coll`, or `charclass`"
_MODE = "'arg' should be one of \u201cfirst\u201d, \u201call\u201d, \u201clast\u201d"
LOREM = "Lorem ipsum dolor"


def test_count_chooses_one_engine_and_forwards_keywords():
    assert stri_count(LOREM, regex="o") == stri_count_regex(LOREM, "o") == [3]
    assert stri_count(LOREM, fixed="dolor") == stri_count_fixed(LOREM, "dolor") == [1]
    assert stri_count(["a", "A"], coll="a", strength=1) == stri_count_coll(["a", "A"], "a", strength=1)
    assert stri_count(["a", "A"], coll="a", strength=1) == [1, 1]
    assert stri_count(LOREM, fixed="LOREM", case_insensitive=True) == [1]
    assert stri_count(LOREM, regex=None) == []
    assert stri_count(LOREM, fixed=None) == []
    with pytest.raises(ValueError, match=_NEED):
        stri_count(LOREM)
    with pytest.raises(ValueError, match=_NEED):
        stri_count(LOREM, regex="o", fixed="o")
    with pytest.raises(ValueError, match=_NEED):
        stri_count(LOREM, regex=None, fixed=None)
    with pytest.raises(ValueError, match=_NEED):
        stri_count(LOREM, f="o")
    with pytest.raises(ValueError, match=_NEED):
        stri_count(LOREM, "o")


def test_detect_message_and_positional_negate():
    assert stri_detect(["ab", "cd"], True, fixed="a") == stri_detect_fixed(["ab", "cd"], "a", True)
    assert stri_detect(["ab", "cd"], True, fixed="a") == [False, True]
    assert stri_detect(["ab", "12"], charclass=r"\p{L}") == stri_detect_charclass(["ab", "12"], r"\p{L}")
    assert stri_detect(["ab", "12"], charclass=r"\p{L}") == [True, False]
    with pytest.raises(ValueError, match=_NEED_OF):
        stri_detect(LOREM)
    with pytest.raises(ValueError, match=_NEED_OF):
        stri_detect(LOREM, regex="a", coll="a")


def test_extract_mode_is_match_arg():
    assert stri_extract(LOREM, fixed="or") == ["or"]
    assert stri_extract(LOREM, fixed="or", mode=None) == ["or"]
    assert stri_extract(LOREM, fixed="or", mode=["first", "all", "last"]) == ["or"]
    assert stri_extract(LOREM, fixed="or", mode="f") == ["or"]
    assert stri_extract(LOREM, fixed="or", mode="l") == ["or"]
    assert stri_extract(LOREM, fixed="or", mode="a") == [["or", "or"]]
    assert stri_extract(LOREM, fixed="or", mode=["all"]) == [["or", "or"]]
    assert stri_extract_all("XaaaaX", regex="a+") == stri_extract_all_regex("XaaaaX", "a+")
    assert stri_extract_first("XaaaaX", regex="a+") == stri_extract_first_regex("XaaaaX", "a+")
    assert stri_extract_last("XaXaX", fixed="a") == stri_extract_last_fixed("XaXaX", "a")
    assert stri_extract_first(["Yy", "AAA"], coll="y", strength=2) == stri_extract_first_coll(
        ["Yy", "AAA"], "y", strength=2
    )
    assert stri_extract(LOREM, regex=None) == []
    with pytest.raises(ValueError, match=_MODE):
        stri_extract(LOREM, mode="nope")
    with pytest.raises(ValueError, match=_MODE):
        stri_extract(LOREM, mode="")
    with pytest.raises(ValueError, match=_MODE):
        stri_extract(LOREM, mode=NA)
    with pytest.raises(ValueError, match="must be of length 1"):
        stri_extract(LOREM, mode=["all", "first"])
    with pytest.raises(ValueError, match="must be of length 1"):
        stri_extract(LOREM, mode=[])
    with pytest.raises(ValueError, match="NULL or a character vector"):
        stri_extract(LOREM, mode=1)
    with pytest.raises(ValueError, match=_NEED):
        stri_extract(LOREM, mode="all")
    with pytest.raises(TypeError):
        stri_extract(LOREM, fixed="or", m="all")


def test_locate_replace_split_and_subset():
    assert stri_locate("stringi", fixed="i") == stri_locate_first_fixed("stringi", "i") == [[4, 4]]
    assert stri_locate("stringi", fixed="i", mode="last") == stri_locate_last_fixed("stringi", "i")
    assert stri_locate("stringi", fixed="i", mode="last") == [[7, 7]]
    assert stri_locate_all("stringi", fixed="i") == stri_locate_all_fixed("stringi", "i")
    assert stri_locate_all("stringi", regex="i") == stri_locate_all_regex("stringi", "i")
    assert stri_locate_first("stringi", fixed="i") == [[4, 4]]
    assert stri_locate_last("ababa", fixed="aba") == [[3, 5]]
    assert stri_replace(LOREM, "#", fixed="or") == stri_replace_first_fixed(LOREM, "or", "#")
    assert stri_replace(LOREM, "#", fixed="or") == ["L#em ipsum dolor"]
    assert stri_replace(LOREM, "#", fixed="or", mode="all") == ["L#em ipsum dol#"]
    assert stri_replace(LOREM, "#", fixed="or", mode="al") == stri_replace_all(LOREM, "#", fixed="or")
    assert stri_replace_all("ababa", "X", fixed="a") == stri_replace_all_fixed("ababa", "a", "X") == ["XbXbX"]
    assert stri_replace_first("ababa", "X", fixed="a") == ["Xbaba"]
    assert stri_replace_last("ababa", "X", fixed="a") == stri_replace_last_fixed("ababa", "a", "X") == ["ababX"]
    assert stri_replace(LOREM, None, fixed="o") == []
    assert stri_split("a_b_c_d", fixed="_") == stri_split_fixed("a_b_c_d", "_")
    assert stri_split("a_b_c", 2, fixed="_") == [["a", "b_c"]]
    assert stri_split("a-b-c", regex="-") == stri_split_regex("a-b-c", "-")
    assert stri_subset(["ab", "cd", "ef"], fixed="a") == stri_subset_fixed(["ab", "cd", "ef"], "a") == ["ab"]
    assert stri_subset(["stringi R", "123", ""], regex="^[0-9]+$") == stri_subset_regex(
        ["stringi R", "123", ""], "^[0-9]+$"
    )
    with pytest.raises(ValueError, match=_MODE):
        stri_locate(LOREM, mode="nope")
    with pytest.raises(ValueError, match=_MODE):
        stri_replace(LOREM, "#", mode="nope")
    with pytest.raises(ValueError, match=_NEED):
        stri_replace(LOREM, "#")
    with pytest.raises(ValueError, match='argument "replacement" is missing, with no default'):
        stri_replace(LOREM, fixed="o")
    with pytest.raises(ValueError, match=_NEED):
        stri_split(LOREM)
    with pytest.raises(ValueError, match=_NEED):
        stri_subset(LOREM, regex="a", charclass=r"\p{L}")


def test_start_and_end_have_no_regex_argument():
    assert stri_startswith("ababa", 2, fixed="ba") == stri_startswith_fixed("ababa", "ba", 2) == [True]
    assert stri_startswith(["a1", "b3"], fixed="a") == [True, False]
    assert stri_startswith(" trim me! ", charclass=r"\p{WSpace}") == stri_startswith_charclass(
        " trim me! ", r"\p{WSpace}"
    )
    assert stri_endswith(["ab", "cd"], fixed="b") == stri_endswith_fixed(["ab", "cd"], "b") == [True, False]
    assert stri_startswith(LOREM, fixed=None) == []
    assert stri_endswith(LOREM, coll=None) == []
    with pytest.raises(ValueError, match=_NEED_EDGE):
        stri_startswith(LOREM)
    with pytest.raises(ValueError, match=_NEED_EDGE):
        stri_startswith(LOREM, regex="^L")
    with pytest.raises(ValueError, match=_NEED_EDGE):
        stri_endswith(LOREM, fixed="a", coll="a")
    with pytest.raises(TypeError):
        stri_startswith(LOREM, fixed="L", regex="^L")
