"""stringr replace, remove, and replace_na against the 1.6.0 results."""

import pytest

from stringi._na import NA
from stringr._size import RecycleError
from stringr.pattern import boundary, coll, fixed, regex
from stringr.replace import (
    fix_replacement,
    str_remove,
    str_remove_all,
    str_replace,
    str_replace_all,
    str_replace_na,
)


FRUITS = ["one apple", "two pears", "three bananas"]


class Named(list):
    def __init__(self, values, names):
        super().__init__(values)
        self.names = list(names)


def upper(match):
    return [NA if item is NA else item.upper() for item in match]


def test_replace_examples():
    assert str_replace(FRUITS, "[aeiou]", "-") == ["-ne apple", "tw- pears", "thr-e bananas"]
    assert str_replace(FRUITS, "([aeiou])", "\\1\\1") == [
        "oone apple",
        "twoo pears",
        "threee bananas",
    ]
    assert str_replace(FRUITS, "[aeiou]", ["1", "2", "3"]) == [
        "1ne apple",
        "tw2 pears",
        "thr3e bananas",
    ]
    assert str_replace(FRUITS, ["a", "e", "i"], "-") == [
        "one -pple",
        "two p-ars",
        "three bananas",
    ]


def test_replace_all_examples():
    assert str_replace_all(FRUITS, "[aeiou]", "-") == [
        "-n- -ppl-",
        "tw- p--rs",
        "thr-- b-n-n-s",
    ]
    assert str_replace_all(FRUITS, "[aeiou]", upper) == [
        "OnE ApplE",
        "twO pEArs",
        "thrEE bAnAnAs",
    ]
    assert str_replace_all(FRUITS, "b", NA) == ["one apple", "two pears", NA]
    assert str_replace_all(
        "---".join(FRUITS), {"one": "1", "two": "2", "three": "3"}
    ) == ["1 apple---2 pears---3 bananas"]


def test_remove_matches_empty_replacement_and_upper():
    assert str_remove(FRUITS, "[aeiou]") == str_replace(FRUITS, "[aeiou]", "")
    assert str_remove_all(FRUITS, "[aeiou]") == str_replace_all(FRUITS, "[aeiou]", "")
    assert str_remove(FRUITS, "[aeiou]") == ["ne apple", "tw pears", "thre bananas"]
    assert str_remove_all(FRUITS, "[aeiou]") == ["n ppl", "tw prs", "thr bnns"]
    assert str_replace(FRUITS, "[aeiou]", upper) == [
        "One apple",
        "twO pears",
        "thrEe bananas",
    ]
    assert str_replace("aBa", "a", upper) == ["ABa"]
    assert str_remove("aBa", "a") == ["Ba"]
    assert str_replace_all("abc", "a|c", upper) == ["AbC"]
    assert str_remove_all("abc", "a|c") == ["b"]


def test_replace_na():
    assert str_replace_na([NA, "abc", "def"]) == ["NA", "abc", "def"]
    assert str_replace_na(NA) == ["NA"]
    assert str_replace_na([1, NA, 2.5]) == ["1", "NA", "2.5"]
    assert str_replace_na([True, NA, False]) == ["TRUE", "NA", "FALSE"]
    named = str_replace_na(Named([NA, "x"], ["A", "B"]))
    assert list(named) == ["NA", "x"]
    assert named.names == ["A", "B"]


def test_backreferences_and_dollars():
    assert str_replace_all("abcde", "(b)(c)(d)", "\\2") == ["ace"]
    assert str_replace_all("abcde", "(b)(c)(d)", "\\0") == ["abcde"]
    assert str_replace_all("abcde", "bcd", "\\\\1") == ["a\\1e"]
    assert str_replace_all("a!1!2!b", "!", "$") == ["a$1$2$b"]
    assert str_replace("aba", "(b)", "\\1$\\1$\\1") == ["ab$b$ba"]
    assert str_replace("aba", "b", "$$$") == ["a$$$a"]
    assert fix_replacement("$") == ["\\$"]
    assert fix_replacement("\\$") == ["\\\\$"]
    assert fix_replacement("\\1") == ["$1"]
    assert fix_replacement("\\\\1") == ["\\\\1"]
    assert fix_replacement("\\") == [""]
    assert fix_replacement("a\\") == ["a"]
    assert fix_replacement([NA, "a"]) == [NA, "a"]


def test_fixed_coll_and_regex_options():
    assert str_replace("x.x", fixed("."), "Y") == ["xYx"]
    assert str_replace_all("x.x.", fixed("."), "Y") == ["xYxY"]
    assert str_replace("Ab", fixed("a", ignore_case=True), "Z") == ["Zb"]
    assert str_replace("Ab", regex("a", ignore_case=True), "Z") == ["Zb"]
    assert str_replace("\u0131", coll("I", ignore_case=True, locale="tr"), "Y") == ["Y"]
    assert str_replace_all("\u0131I", coll("I", ignore_case=True, locale="tr"), "Y") == ["YY"]
    assert str_replace("a", fixed("a"), 1) == ["1"]
    assert str_replace([1, 12], "1", "X") == ["X", "X2"]
    assert str_replace("xx", "x", NA) == [NA]


def test_named_patterns():
    assert str_replace_all(["ab", "ba"], {"a": "A", "b": "B"}) == ["AB", "BA"]
    assert str_replace_all("aba", {"a": "b"}, "X") == ["bbb"]
    assert str_replace("aba", Named(["b"], ["a"]), "X") == ["aXa"]
    dot = fixed(["X"])
    dot.names = ["."]
    assert str_replace_all("a.b", dot) == ["aXb"]
    folded = regex(["a"], ignore_case=True)
    folded.names = ["X"]
    assert str_replace_all(["x", "y"], folded) == ["a", "y"]
    assert str_replace_all("aba", {"(b)": "\\1"}) == ["aba"]


def test_function_replacement():
    assert str_replace("abc", "a|c", upper) == ["Abc"]
    assert str_replace_all("abc", "a|c", upper) == ["AbC"]
    assert str_replace("abc", "z", upper) == ["abc"]
    assert str_replace("abc", "$", upper) == ["abc"]
    assert str_replace_all("abc", "$|^", lambda xs: ["X"] * len(xs)) == ["XabcX"]
    assert str_replace_all("abc", "a|c", lambda xs: [item + item for item in xs]) == ["aabcc"]
    assert str_replace_all(["a", "b", "c"], "d", lambda xs: ["x " + x for x in xs]) == [
        "a",
        "b",
        "c",
    ]
    assert str_replace("abc", "b", lambda xs: [NA] * len(xs)) == ["abc"]
    assert str_replace_all("abc", "b", lambda xs: [NA] * len(xs)) == [NA]
    assert str_replace("abc", ["a", "b"], upper) == ["Abc", "aBc"]
    assert str_replace("abc", "", upper) == ["Abc"]
    assert str_replace_all("abc", "", upper) == ["ABC"]
    assert str_replace("x x", boundary("word"), upper) == ["X x"]
    assert str_replace_all("x x", boundary("word"), upper) == ["X X"]
    assert str_replace("abc", "b", lambda xs: 1) == ["a1c"]
    assert str_replace("abc", "b", lambda xs: ["Q", "R"]) == ["aQc", "aRc"]
    assert str_replace_all(["ab", NA, "c"], "a|c", upper) == ["Ab", NA, "C"]
    assert str_replace_all("aaa", fixed("aa"), "b") == ["ba"]


def test_empty_input_calls_only_the_first_function():
    seen = []

    def spy(xs):
        seen.append(len(xs))
        return list(xs)

    assert str_replace([], "a", spy) == []
    assert seen == [0]
    assert str_replace_all([], "a", spy) == []
    assert seen == [0]
    assert str_replace(None, "a", "b") == []
    assert str_replace_all(None, {"a": "b"}) == []


def test_names():
    named = str_replace(Named(["3", "2", "1"], ["C", "B", "A"]), "[0-9]", "x")
    assert list(named) == ["x", "x", "x"]
    assert named.names == ["C", "B", "A"]
    dropped = str_replace(Named(["ab"], ["A"]), ["a", "b"], "x")
    assert dropped == ["xb", "ax"]
    assert getattr(dropped, "names", None) is None
    kept = str_replace(Named(["ab", "cd"], ["A", "B"]), ["a", "b"], "x")
    assert list(kept) == ["xb", "cd"]
    assert kept.names == ["A", "B"]
    recycled = str_replace(Named(["abc"], ["A"]), "b", ["Q", "R"])
    assert list(recycled) == ["aQc", "aRc"]
    assert recycled.names == ["A", "A"]
    differing = str_replace_all(Named(["a1", "b2", "c3"], ["A", "B", "C"]), {"a": "1", "b": "2"})
    assert differing == ["11", "22", "c3"]
    assert getattr(differing, "names", None) is None
    fun = str_replace(Named(["abc", "def"], ["A", "B"]), "a|d", upper)
    assert fun == ["Abc", "Def"]
    assert getattr(fun, "names", None) is None


def test_errors():
    with pytest.raises(ValueError, match="empty string"):
        str_replace("x", "", "")
    with pytest.raises(ValueError, match="boundary"):
        str_replace_all("x", boundary("word"), "")
    with pytest.raises(ValueError, match="character vector"):
        str_replace("x", "x", 1)
    with pytest.raises(RecycleError, match="replacement"):
        str_replace(["a", "b"], "", ["x", "y", "z"])
    with pytest.raises(RecycleError, match="pattern"):
        str_replace(["a", "b"], ["a", "b", "c"], None)
    with pytest.raises(ValueError, match="a number"):
        str_replace_all("x", "x", lambda xs: 1)
    with pytest.raises(ValueError, match="not length 2"):
        str_replace_all("x", "x", lambda xs: ["a", "b"])
    with pytest.raises(ValueError, match="Failed to apply"):
        str_replace_all(["a", "c"], "a|c", lambda xs: xs[99])
    with pytest.raises(ValueError, match="NAs"):
        str_replace("ab", NA, "X")
    with pytest.raises(ValueError, match="single string"):
        str_replace_na("a", ["x", "y"])
    with pytest.raises(ValueError, match="`NA`"):
        str_replace_na("a", NA)
    with pytest.raises(ValueError, match="U_INDEX_OUTOFBOUNDS_ERROR"):
        str_replace_all("abcde", "(b)(c)(d)", "\\4")
    with pytest.raises(TypeError, match="missing"):
        str_replace_all("x", "x")
    with pytest.raises(ValueError, match="NULL"):
        str_replace("a", "a", None)
    assert str_replace("a", fixed("a"), None) == []
    with pytest.raises(ValueError, match="empty string"):
        str_replace(None, "", "a")
