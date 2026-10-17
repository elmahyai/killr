"""Literal fixed-search results checked against stringi 1.8.9."""

import json
import warnings

import pytest

from stringi._na import NA
from stringi.fixed import (
    stri_count_fixed,
    stri_detect_fixed,
    stri_endswith_fixed,
    stri_extract_all_fixed,
    stri_extract_first_fixed,
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

CI = {"case_insensitive": True}
BOTH = {"case_insensitive": True, "overlap": True}

# JSON lines captured from Rscript against the installed stringi 1.8.9.
EXPECTED = """
count1	[3,3,2,0,null,2,1,null,0,0]
count2	[1,2,0]
count3	[]
count4	[null,null]
detect1	[true,true,false,null,false,null,null]
detect2	[false,true,null,null]
detect3	[null,null]
detect4	[false,null,null]
detect5	[true]
detect6	[false,false,false,false,true,true,false]
start1	[true,true,false,true,false]
start2	[false,true,false,false,false,true]
start3	[false,null,true]
start4	[true,true]
start5	[null]
end1	[true,true,true]
end2	[true]
end3	[false,null]
exf1	[null,"a",null,"z","É"]
exl1	["AGA","aba"]
exa1	[["aba","aBA","Aba"],["aa","aa"],[null],[null],[null],["ÉÉ","ÉÉ"]]
exa2	[["a"],[],[]]
exa3	[["a","a","a"],[null,"",""]]
exa4	[["a","a","a"],[null,null,null]]
exa5	[["a","a","a"],["","",""]]
locf1	[[1,3],[null,null],[null,null],[2,2],[null,null]]
locf2	[[-1,-1],[-1,-1],[null,null]]
locl1	[[3,5],[3,5]]
loca1	[[[1,3],[3,5],[5,7]],[[1,2],[2,3]],[[1,2],[2,3]],[[null,null]],[[null,null]],[[null,null]]]
loca2	[[[1,3],[5,7]],[],[[null,null]]]
loca3	[[[1,3]],[[-1,-1]]]
repf1	["XAaA","abc",""]
repl1	["aAaX"]
repa1	["XXXX","ba",null,"",null,"abc"]
repa2	["The slow black bear jumped over the lazy dog."]
repa3	["XX","cd"]
repa4	[null,null]
repa5	[null,null]
repa6	[]
repa7	["ZbZ","ZaZ"]
spl1	[["a","b","c","","d"],["a","","b"],["","","",""],["aaa"]]
spl2	[["a","b","c","d"],["a","b","c","","d"],["a","b","c",null,"d"]]
spl3	[["a","b"],["a","b","c",""],[],["a","b","c","","d"]]
spl4	[["ab"],["d","ef"],["h"],[]]
spl5	[["ab","c",""],["d","ef","g"],["h","",""],["","",""]]
spl6	[["ab","c",null],["d","ef","g"],[null,"h",null],[null,null,null]]
spl7	[["a","b","",""],["c","","",""]]
spl8	[[null],[null]]
spl9	[["a","b","c"],["é","é"]]
sub1	["123"]
sub2	["a"]
sub3	["a",null]
sub4	["b"]
sub5	[null,null]
sub6	[]
sub7	[""]
sub8	["a",""]
sub9	[]
sub10	["Éva"]
""".strip()


def canon(value):
    if value is NA:
        return None
    if isinstance(value, list):
        return [canon(item) for item in value]
    return value


def cases():
    return {
        "count1": stri_count_fixed(
            ["babab", "aAaA", "ééé", "", NA, "aaa", "AbC", "x", "ßﬁ", "σίγμα"],
            ["b", "aa", "éé", "a", "a", "aa", "abc", "", "SS", "ΣΙΓΜΑ"],
            opts_fixed=BOTH,
        ),
        "count2": stri_count_fixed(["ab", "abab", "x"], ["a", "b"]),
        "count3": stri_count_fixed([], "a"),
        "count4": stri_count_fixed(["a", "b"], ""),
        "detect1": stri_detect_fixed(
            ["a", "b", "c", "a", "b", "", NA], ["a", "b"], max_count=2
        ),
        "detect2": stri_detect_fixed(
            ["ab", "cd", "ax", "ef"], "a", negate=True, max_count=1
        ),
        "detect3": stri_detect_fixed(["a", "b"], "a", max_count=0),
        "detect4": stri_detect_fixed(["", "abc", NA], ["a", ""]),
        "detect5": stri_detect_fixed("ala", "ALA", case_insensitive=True),
        "detect6": stri_detect_fixed(
            ["ß", "ẞ", "ﬁ", "և", "µ", "ı", "İ"],
            ["SS", "ß", "FI", "ԵՒ", "Μ", "I", "i"],
            opts_fixed=CI,
        ),
        "start1": stri_startswith_fixed(["a1", "a2", "b3", "a4", "c5"], "a"),
        "start2": stri_startswith_fixed("ababa", "ba", [1, 2, -1, -3, 0, 4]),
        "start3": stri_startswith_fixed(
            ["", NA, "éab"], ["a", "a", "ab"], from_=[1, 1, 2]
        ),
        "start4": stri_startswith_fixed(
            ["Ébc", "abÉ"], ["é", "BÉ"], from_=[1, -2], case_insensitive=True
        ),
        "start5": stri_startswith_fixed("abc", "a", from_=NA, negate=True),
        "end1": stri_endswith_fixed(
            ["ababa", "xyz", "abé"], ["ba", "y", "b"], to=[-1, 2, -2]
        ),
        "end2": stri_endswith_fixed("abÉ", "bé", to=-1, case_insensitive=True),
        "end3": stri_endswith_fixed(["", "abc"], "c", to=[-1, NA]),
        "exf1": stri_extract_first_fixed(
            ["", "abc", NA, "zzz", "Éxé"],
            ["a", "a", "a", "z", "é"],
            opts_fixed=CI,
        ),
        "exl1": stri_extract_last_fixed(
            ["agAGA", "ababa"], ["aga", "aba"], case_insensitive=True
        ),
        "exa1": stri_extract_all_fixed(
            ["abaBAba", "aaa", "zzz", "", NA, "ÉÉÉ"],
            ["Aba", "aa", "a", "a", "a", "éé"],
            opts_fixed=BOTH,
        ),
        "exa2": stri_extract_all_fixed(["abc", "zzz", ""], "a", omit_no_match=True),
        "exa3": stri_extract_all_fixed(["ababa", "x"], "a", simplify=True),
        "exa4": stri_extract_all_fixed(["ababa", "x"], "a", simplify=NA),
        "exa5": stri_extract_all_fixed(
            ["aaa", "bbb"], "a", simplify=True, omit_no_match=True
        ),
        "locf1": stri_locate_first_fixed(
            ["ababa", "", NA, "aéb", "zzz"], ["aba", "a", "a", "é", "q"]
        ),
        "locf2": stri_locate_first_fixed(["abc", "", NA], "z", get_length=True),
        "locl1": stri_locate_last_fixed(
            ["ababa", "agAGA"], ["aba", "aga"], case_insensitive=True
        ),
        "loca1": stri_locate_all_fixed(
            ["abababa", "aaa", "ééé", "", NA, "zzz"],
            ["ABA", "aa", "éé", "a", "a", "a"],
            opts_fixed=BOTH,
        ),
        "loca2": stri_locate_all_fixed(
            ["yes yes", "no", NA], "yes", omit_no_match=True
        ),
        "loca3": stri_locate_all_fixed(["ababa", "zzz"], "aba", get_length=True),
        "repf1": stri_replace_first_fixed(
            ["aAaA", "abc", ""], ["a", "z", "a"], ["X", "Q", "Z"], case_insensitive=True
        ),
        "repl1": stri_replace_last_fixed("aAaA", "a", "X", case_insensitive=True),
        "repa1": stri_replace_all_fixed(
            ["aAaA", "aaa", "aba", "", NA, "abc"],
            ["a", "aa", "a", "a", "a", "z"],
            ["X", "b", NA, "Z", "Z", "Q"],
            overlap=True,
            case_insensitive=True,
        ),
        "repa2": stri_replace_all_fixed(
            "The quick brown fox jumped over the lazy dog.",
            ["quick", "brown", "fox"],
            ["slow", "black", "bear"],
            vectorize_all=False,
        ),
        "repa3": stri_replace_all_fixed(
            ["ab", "cd"], ["a", "b"], "X", vectorize_all=False
        ),
        "repa4": stri_replace_all_fixed(
            ["ab", "cd"], ["a", NA], ["X", "Y"], vectorize_all=False
        ),
        "repa5": stri_replace_all_fixed(
            ["ab", "cd"], ["a", ""], "X", vectorize_all=False
        ),
        "repa6": stri_replace_all_fixed("abc", "b", []),
        "repa7": stri_replace_all_fixed(["aba", "bab"], ["a", "b"], "Z"),
        "spl1": stri_split_fixed(["a_b_c__d", "a__b", "___", "aaa"], "_"),
        "spl2": stri_split_fixed("a_b_c__d", "_", omit_empty=[True, False, NA]),
        "spl3": stri_split_fixed("a_b_c__d", "_", n=[2, 4, 0, -1], tokens_only=True),
        "spl4": stri_split_fixed(
            ["ab_c", "d_ef_g", "h", ""],
            "_",
            n=[1, 2, 3],
            tokens_only=True,
            omit_empty=True,
        ),
        "spl5": stri_split_fixed(
            ["ab,c", "d,ef,g", ",h", ""], ",", omit_empty=True, simplify=True
        ),
        "spl6": stri_split_fixed(
            ["ab,c", "d,ef,g", ",h", ""], ",", omit_empty=NA, simplify=NA
        ),
        "spl7": stri_split_fixed(["a_b", "c"], "_", n=4, simplify=True),
        "spl8": stri_split_fixed(["abc", "a_b"], ["", "_"], n=[0, NA]),
        "spl9": stri_split_fixed(["aXbXc", "éXé"], "x", case_insensitive=True),
        "sub1": stri_subset_fixed(["stringi R", "123", "ID456", ""], "1"),
        "sub2": stri_subset_fixed(["a", NA, "b", ""], "a", omit_na=True),
        "sub3": stri_subset_fixed(["a", NA, "b", ""], "a", omit_na=False),
        "sub4": stri_subset_fixed(["a", "b", "a"], "a", negate=True),
        "sub5": stri_subset_fixed(["a", "b"], ""),
        "sub6": stri_subset_fixed(["a", "b"], "", omit_na=True),
        "sub7": stri_subset_fixed(["a", ""], "a", negate=True),
        "sub8": stri_subset_fixed(["a", ""], "b", negate=True),
        "sub9": stri_subset_fixed([], "a"),
        "sub10": stri_subset_fixed(["Éva", "eva", "no"], "é", case_insensitive=True),
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
    assert stri_count_fixed("NA", "N") == [1]
    assert stri_count_fixed(NA, "N") == [NA]
    assert stri_replace_first_fixed("NA", "N", "X") == ["XA"]
    assert stri_subset_fixed(["NA", NA], "N") == ["NA", NA]


def test_inconsistent_lengths_raise():
    with pytest.raises(ValueError, match="vector length not consistent"):
        stri_subset_fixed(["a"], ["a", "b"])
    with pytest.raises(ValueError, match="vector length not consistent"):
        stri_replace_all_fixed(
            ["ab", "cd"], ["a"], ["X", "Y"], vectorize_all=False
        )
