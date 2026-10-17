"""Character-class and trim results checked against stringi 1.8.9."""

import json
import warnings

import pytest

from stringi._na import NA
from stringi.charclass import (
    stri_count_charclass,
    stri_detect_charclass,
    stri_endswith_charclass,
    stri_extract_all_charclass,
    stri_extract_first_charclass,
    stri_extract_last_charclass,
    stri_locate_all_charclass,
    stri_locate_first_charclass,
    stri_locate_last_charclass,
    stri_replace_all_charclass,
    stri_replace_first_charclass,
    stri_replace_last_charclass,
    stri_split_charclass,
    stri_startswith_charclass,
    stri_subset_charclass,
    stri_trim,
    stri_trim_both,
    stri_trim_left,
    stri_trim_right,
)

# JSON lines captured from Rscript against the installed stringi 1.8.9.
EXPECTED = r"""
count1	[6,6,3]
count2	[3,0,null,2,1,1,12]
count3	[1,2,0]
count4	[]
count5	[1,4]
count6	[1]
count7	[0]
count8	[null,null]
detect1	[true,false,false,false,false]
detect2	[true,null,null,null,null]
detect3	[null,null]
detect4	[true,null,true]
detect5	[false]
detect6	[false,false,false,false,false]
start1	[true,false,false,null]
start2	[true,true,true,true,true,false,false,true]
start3	[true,true,true,true]
start4	[false,true,true,false]
start5	[true]
start6	[true,true]
start7	[null]
start8	[true,true]
end1	[true,true,true,true,false,true,false,true]
end2	[false,false,false]
end3	[false,false,false]
end4	[false,null,true]
exf1	["a","1",null,null,"😀"]
exl1	["c","c","b"]
exa1	[["aab","cc"],["ABC"],[null],[null]]
exa2	[["a","a","b","c","c"]]
exa3	[[],["ab"]]
exa4	[["a","b"],["c",""],[null,""]]
exa5	[["a","b"],["c",null],[null,null]]
exa6	[["😀","😀"]]
exa7	[["ab"],["c"]]
locf1	[[2,1],[1,1],[-1,-1],[null,null]]
locf2	[[3,3],[null,null]]
locl1	[[4,4],[null,null]]
loca1	[[[1,3],[6,7]]]
loca2	[[[1,1],[2,2],[3,3],[6,6],[7,7]]]
loca3	[[[-1,-1]]]
loca4	[[]]
loca5	[[[-1,-1]],[[null,null]]]
loca6	[[[2,2]]]
loca7	[[[1,3],[6,2]]]
repf1	["abX2","abc",""]
repl1	["ab1X"]
repa1	["b"]
repa2	["a b c   d"]
repa3	["XY"]
repa4	["XYXYXY"]
repa5	["bb"]
repa6	["abc"]
repa7	["Xb","Xd"]
repa8	["XX","Yd"]
repa9	[null,null]
repa10	[]
repa11	["Xb","Yd"]
repa12	["Xb"]
spl1	[["Lorem","ipsum","dolor","sit","amet"]]
spl2	[["Lorem","ipsum","dolor"]]
spl3	[["a","b"],["a","","b"],["a",null,"b"]]
spl4	[["a","b"]]
spl5	[["a","b c d"]]
spl6	[["a","b",""],["c","d","e"]]
spl7	[[]]
spl8	[[""],[],[null]]
spl9	[["a"," b  c"]]
spl10	[[],["","aa"]]
spl11	[["a",null]]
spl12	[["a b c"]]
spl13	[["a b"]]
spl14	[[null],[null]]
sub1	["a","b",null]
sub2	["a"]
sub3	[]
sub4	["cd"]
sub5	[]
sub6	["NA",null]
sub7	[""]
sub8	[]
trim1	["a",null,"","a","\u200ba\u200b"]
trim2	["aaa"]
trim3	["r-project.org"]
trim4	["23.5"]
trim5	["23.5"]
trim6	["  a","b"]
trim7	["a  "]
trim8	["a"]
trim9	["a"," "]
trim10	[""]
trim11	["abc"]
trim12	[""]
trim13	["12ab34"]
trim14	[" a "]
trim15	[""]
trim16	["a\t"]
trim17	[]
""".strip()


def canon(value):
    if value is NA:
        return None
    if isinstance(value, list):
        return [canon(item) for item in value]
    return value


def cases():
    tod = "\U000105c0"
    emoji = "\U0001f600"
    mixed = "a b\t\n\u00a0\u200b9é."
    return {
        "count1": stri_count_charclass(
            ["stRRRingi", "STrrrINGI", "123"], ["\\p{Ll}", "\\p{Lu}", "\\p{N}"]
        ),
        "count2": stri_count_charclass(
            ["abc", "", NA, "NA", tod, emoji, "0123456789#*"],
            ["\\p{L}", "\\p{Z}", "\\p{N}", "\\p{L}", "\\p{Lo}", "\\p{Emoji}", "\\p{Emoji}"],
        ),
        "count3": stri_count_charclass(["a", "bb", "ccc"], ["[a]", "[b]"]),
        "count4": stri_count_charclass([], "\\p{L}"),
        "count5": stri_count_charclass([" \t\n", mixed], ["\\p{Z}", "\\p{WhiteSpace}"]),
        "count6": stri_count_charclass("w", "[\\w]"),
        "count7": stri_count_charclass("ab", "[{ab}]"),
        "count8": stri_count_charclass([NA, "abc"], NA),
        "detect1": stri_detect_charclass(
            ["a", "b", "1", "c", "2"], ["\\p{L}", "\\p{N}"], max_count=2
        ),
        "detect2": stri_detect_charclass(
            ["a", "1", "b", "2", "c"], "\\p{N}", max_count=1, negate=True
        ),
        "detect3": stri_detect_charclass(["a", "b"], "\\p{L}", max_count=0),
        "detect4": stri_detect_charclass(["", NA, "1"], "\\p{L}", negate=[True, False]),
        "detect5": stri_detect_charclass("", "\\p{Cc}"),
        "detect6": stri_detect_charclass(
            ["a", "1", "b", "2", "c"], ["\\p{N}", "\\p{L}"], max_count=2
        ),
        "start1": stri_startswith_charclass(["abc", "1bc", "", NA], "\\p{L}"),
        "start2": stri_startswith_charclass(
            "abc", "\\p{L}", from_=[1, 2, 0, -1, -3, 4, 5, -4]
        ),
        "start3": stri_startswith_charclass("", "\\p{L}", from_=[1, 0, -1, 2], negate=True),
        "start4": stri_startswith_charclass("ab", "[\\u0000]", from_=[2, 3, 4, -1]),
        "start5": stri_startswith_charclass("", "\\p{Cc}"),
        "start6": stri_startswith_charclass(["éab", tod], "\\p{L}", from_=[2, 1]),
        "start7": stri_startswith_charclass("abc", "\\p{L}", from_=NA),
        "start8": stri_startswith_charclass("abc", "\\p{L}", from_=[1.2, -1.2]),
        "end1": stri_endswith_charclass("abc", "\\p{L}", to=[-1, 1, 2, 3, 0, -2, -4, 4]),
        "end2": stri_endswith_charclass("", "\\p{L}", to=[-1, 1, 0]),
        "end3": stri_endswith_charclass("ab", "[\\u0000]", to=[3, -1, 0]),
        "end4": stri_endswith_charclass(["ab1", NA, ""], "\\p{N}", to=-1, negate=True),
        "exf1": stri_extract_first_charclass(
            ["AaBbCc", "123", "", NA, emoji],
            ["\\p{Ll}", "\\p{N}", "\\p{L}", "\\p{L}", "\\p{So}"],
        ),
        "exl1": stri_extract_last_charclass(["AaBbCc", "abc", "a1b2"], "\\p{Ll}"),
        "exa1": stri_extract_all_charclass(["aab12cc", "ABC", "", NA], "\\p{L}", merge=True),
        "exa2": stri_extract_all_charclass("aab12cc", "\\p{L}", merge=False),
        "exa3": stri_extract_all_charclass(["123", "ab"], "\\p{L}", omit_no_match=True),
        "exa4": stri_extract_all_charclass(
            ["ab", "c", "12"], "\\p{L}", merge=False, simplify=True
        ),
        "exa5": stri_extract_all_charclass(
            ["ab", "c", "12"], "\\p{L}", merge=False, simplify=NA
        ),
        "exa6": stri_extract_all_charclass("a" + emoji + "b" + emoji + "c", "\\p{So}", merge=True),
        "exa7": stri_extract_all_charclass(["ab", "c"], "\\p{L}", simplify=[True, False]),
        "locf1": stri_locate_first_charclass(["a1", "12", "", NA], "\\p{N}", get_length=True),
        "locf2": stri_locate_first_charclass(["ab1", ""], "\\p{N}"),
        "locl1": stri_locate_last_charclass(["a1b2", "x"], "\\p{N}"),
        "loca1": stri_locate_all_charclass("aab12cc", "\\p{L}", merge=True),
        "loca2": stri_locate_all_charclass("aab12cc", "\\p{L}", merge=False),
        "loca3": stri_locate_all_charclass("12", "\\p{L}", get_length=True),
        "loca4": stri_locate_all_charclass(
            "12", "\\p{L}", omit_no_match=True, get_length=True
        ),
        "loca5": stri_locate_all_charclass(["", NA], "\\p{L}", get_length=True),
        "loca6": stri_locate_all_charclass("a" + emoji + "b", "\\p{So}"),
        "loca7": stri_locate_all_charclass("aab12cc", "\\p{L}", merge=True, get_length=True),
        "repf1": stri_replace_first_charclass(["ab12", "abc", ""], "\\p{N}", ["X", NA, "Z"]),
        "repl1": stri_replace_last_charclass("ab12", "\\p{N}", "X"),
        "repa1": stri_replace_all_charclass("aaaa", "[a]", "b", merge=True),
        "repa2": stri_replace_all_charclass(
            "a\nb\tc   d", "\\p{WHITE_SPACE}", " ", merge=[False, True]
        ),
        "repa3": stri_replace_all_charclass("aaa", "[a]", "XY", merge=True),
        "repa4": stri_replace_all_charclass("aaa", "[a]", "XY", merge=False),
        "repa5": stri_replace_all_charclass("ababa", "[a]", "", merge=True),
        "repa6": stri_replace_all_charclass("abc", "\\p{N}", NA),
        "repa7": stri_replace_all_charclass(
            ["ab", "cd"], ["[a]", "[c]"], "X", vectorize_all=False
        ),
        "repa8": stri_replace_all_charclass(
            ["ab", "cd"], ["[a]", "[c]", "[b]"], ["X", "Y"], vectorize_all=False
        ),
        "repa9": stri_replace_all_charclass(["ab", NA], ["[a]", NA], "X", vectorize_all=False),
        "repa10": stri_replace_all_charclass([], "[a]", "b", vectorize_all=False),
        "repa11": stri_replace_all_charclass(
            ["ab", "cd"], ["[a]", "[c]"], ["X", "Y"], vectorise_all=False
        ),
        "repa12": stri_replace_all_charclass("ab", "[a]", "X", vectorise_all=False),
        "spl1": stri_split_charclass("Lorem ipsum dolor sit amet", "\\p{WHITE_SPACE}"),
        "spl2": stri_split_charclass(
            " Lorem  ipsum dolor", "\\p{WHITE_SPACE}", n=3, omit_empty=True
        ),
        "spl3": stri_split_charclass("a  b", "\\p{Z}", omit_empty=[True, False, NA]),
        "spl4": stri_split_charclass("a b c d", "\\p{Z}", n=2, tokens_only=True),
        "spl5": stri_split_charclass("a b c d", "\\p{Z}", n=2, tokens_only=False),
        "spl6": stri_split_charclass(["a b", "c d e"], "\\p{Z}", simplify=True, n=3),
        "spl7": stri_split_charclass("abc", "\\p{Z}", n=0),
        "spl8": stri_split_charclass("", "\\p{Z}", omit_empty=[False, True, NA]),
        "spl9": stri_split_charclass("  a  b  c", "\\p{Z}", n=2, omit_empty=True),
        "spl10": stri_split_charclass("aaa", "[a]", n=[-1, 2], omit_empty=[True, False]),
        "spl11": stri_split_charclass("a ", "\\p{Z}", omit_empty=NA),
        "spl12": stri_split_charclass("a b c", "\\p{Z}", n=1),
        "spl13": stri_split_charclass("a b", "\\p{Z}", n=1.8),
        "spl14": stri_split_charclass(["a", "b"], "\\p{Z}", n=NA),
        "sub1": stri_subset_charclass(["a", "1", "b", NA, ""], "\\p{L}"),
        "sub2": stri_subset_charclass(["a", "1", NA], "\\p{N}", omit_na=True, negate=True),
        "sub3": stri_subset_charclass([], "\\p{L}"),
        "sub4": stri_subset_charclass(["ab", "cd", "ef"], ["\\p{N}", "[c]"]),
        "sub5": stri_subset_charclass(["a", "1", "b", "2", "c"], ["\\p{N}", "\\p{L}"]),
        "sub6": stri_subset_charclass(["NA", NA, ""], "[N]"),
        "sub7": stri_subset_charclass(["", "a"], "\\p{L}", negate=True),
        "sub8": stri_subset_charclass([], ["\\p{L}", "\\p{N}"]),
        "trim1": stri_trim(["  a  ", NA, "", "\u00a0a\t", "\u200ba\u200b"]),
        "trim2": stri_trim_left("               aaa"),
        "trim3": stri_trim_right("r-project.org/", "\\P{P}"),
        "trim4": stri_trim_both(" Total of 23.5 bitcoins. ", "\\p{N}"),
        "trim5": stri_trim_both(" Total of 23.5 bitcoins. ", "\\P{N}", negate=True),
        "trim6": stri_trim(["  a", "b  "], side="r"),
        "trim7": stri_trim("  a  ", side="l"),
        "trim8": stri_trim("  a  ", "b"),
        "trim9": stri_trim_both([" a ", " b"], ["\\P{Z}", "\\P{L}"]),
        "trim10": stri_trim_both("   ", "\\P{Z}"),
        "trim11": stri_trim_left("abc", "\\p{L}"),
        "trim12": stri_trim_both("abc", "\\p{N}"),
        "trim13": stri_trim_both("  12ab34  ", "\\p{N}"),
        "trim14": stri_trim_both(" a ", "[]", negate=True),
        "trim15": stri_trim_both(" a ", "[]"),
        "trim16": stri_trim("\u00a0a\t", pattern="\\P{Z}"),
        "trim17": stri_trim([]),
    }


def test_battery_matches_installed_stringi():
    expected = {}
    for line in EXPECTED.splitlines():
        name, payload = line.split("\t", 1)
        expected[name] = json.loads(payload)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        got = cases()
    assert set(got) == set(expected)
    for name, want in expected.items():
        assert canon(got[name]) == want, name


def test_text_na_is_not_missing():
    assert stri_count_charclass("NA", "[N]") == [1]
    assert stri_count_charclass(NA, "[N]") == [NA]
    assert stri_trim("NA") == ["NA"]


def test_pattern_errors_match_icu_names():
    with pytest.raises(ValueError, match=r"U_MALFORMED_SET"):
        stri_count_charclass("w", r"\w")
    with pytest.raises(ValueError, match=r"U_MALFORMED_SET"):
        stri_count_charclass("a", "WhiteSpace")
    with pytest.raises(ValueError, match=r"U_ILLEGAL_ARGUMENT_ERROR"):
        stri_count_charclass("a", r"\p{NO_SUCH}")
    with pytest.raises(ValueError, match="vector length not consistent"):
        stri_subset_charclass(["a"], [r"\p{L}", r"\p{N}"])
    with pytest.raises(ValueError, match="value too large"):
        stri_split_charclass("a b", r"\p{Z}", n=2147483647)


def test_side_prefix_and_bad_side():
    assert stri_trim("  a  ", side="bo") == ["a"]
    with pytest.raises(ValueError, match="both"):
        stri_trim(" a ", side="lefty")
