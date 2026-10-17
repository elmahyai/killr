"""Checks for the reserved stringi helpers."""

from __future__ import annotations

import math
import warnings
from pathlib import Path

import pytest

from stringi._na import NA, is_na
from stringi.files import stri_read_lines, stri_read_raw, stri_write_lines
from stringi.info import stri_info
from stringi.infix import s_plus, s_times, stri_plus, stri_times
from stringi.join import stri_dup, stri_join
from stringi.locale import (
    stri_locale_get,
    stri_locale_info,
    stri_locale_list,
    stri_locale_set,
)
from stringi.random import stri_rand_lipsum, stri_rand_shuffle, stri_rand_strings
from stringi.sprintf import s_dollar, stri_dollar, stri_printf, stri_sprintf, stri_string_format
from stringi.stats import stri_stats_general, stri_stats_latex
from stringi.wrap import stri_wrap


def test_times_and_plus_call_join():
    assert s_times is stri_times
    assert s_plus is stri_plus
    assert s_times(["a", NA, "ba"], 4) == stri_dup(["a", NA, "ba"], 4)
    assert s_times("a", [1, 2, 3, 4, 5]) == ["a", "aa", "aaa", "aaaa", "aaaaa"]
    left = ["abc", "123", "xy"]
    right = list("abcdef")
    assert s_plus(left, right) == stri_join(left, right, sep="")
    assert s_plus("ID_", [1, 2, 3, 4, 5]) == ["ID_1", "ID_2", "ID_3", "ID_4", "ID_5"]
    assert s_plus(["a", NA], ["b", "c"]) == ["ab", NA]
    assert s_plus("", None) == []
    assert s_plus(["NA", NA], "x") == ["NAx", NA]


def test_sprintf_matches_the_probed_specifiers():
    assert stri_string_format is stri_sprintf
    assert s_dollar is stri_dollar
    assert stri_sprintf("%s", "hello") == ["hello"]
    assert stri_sprintf("%d", 3) == ["3"]
    assert stri_sprintf("%f", 1.5) == ["1.500000"]
    assert stri_sprintf("%s", NA) == [NA]
    assert stri_sprintf("%d", NA) == [NA]
    assert stri_sprintf("%f", NA) == [NA]
    assert stri_sprintf("%f", float("nan")) == ["NaN"]
    assert stri_sprintf("%f", float("inf")) == ["Inf"]
    assert stri_sprintf("%f", float("-inf")) == ["-Inf"]
    assert stri_sprintf("%s", NA, na_string="NA") == ["NA"]
    assert stri_sprintf("[%10s]", "abcd") == ["[      abcd]"]
    assert stri_sprintf("[%10s]", "ąĆ") == ["[        ąĆ]"]
    assert stri_sprintf("[%-10.3s]", "xxabcd") == ["[xxa       ]"]
    assert stri_sprintf("[%10s]", "一", use_length=True) == ["[         一]"]
    assert stri_sprintf("[%10s]", "一") == ["[        一]"]
    assert stri_sprintf("[%.3s]", "一一一ab") == ["[一]"]
    assert stri_sprintf("%1$#- *2$.*3$f", 1.23456, 10, 3) == [" 1.235    "]
    assert stri_sprintf(["%s", "%f"], math.pi) == ["3.14159265358979", "3.141593"]
    assert stri_sprintf("%s=%d", ["a", "b"], [1, 2]) == ["a=1", "b=2"]
    assert stri_sprintf("%s", 1e5) == ["1e+05"]
    assert stri_sprintf("%s", 1e-4) == ["1e-04"]
    assert stri_sprintf("%a", 1.5) == ["0x1.8p+0"]
    assert stri_sprintf("%A", 1.5) == ["0X1.8P+0"]
    assert stri_sprintf("%g", 1e6) == ["1e+06"]
    assert stri_sprintf("%.0f", 2.5) == ["2"]
    assert stri_sprintf("%s %d", True, False) == ["TRUE 0"]
    assert stri_sprintf("%d", 3.9) == ["3"]
    assert stri_sprintf("100%%") == ["100%"]
    assert stri_sprintf(["%d", NA], [1, 2]) == ["1", NA]
    assert stri_sprintf("%s", None) == []
    assert s_dollar("value='%d'", [1, 2, 3]) == ["value='1'", "value='2'", "value='3'"]
    assert s_dollar("%s=%d", (["a", "b"], [1, 2])) == ["a=1", "b=2"]
    assert s_dollar("%s", NA) == [NA]
    with pytest.raises(ValueError, match="too few arguments"):
        stri_sprintf("%d")
    with pytest.raises(ValueError, match="not valid"):
        stri_sprintf("%q", 1)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        assert stri_sprintf("%d", 1, 2, 3) == ["1"]
    assert any("2 arguments have not been used" in str(item.message) for item in caught)


def test_printf_writes_the_cat_newlines(tmp_path: Path):
    path = tmp_path / "out.txt"
    path.write_bytes(b"")
    assert stri_printf("%s", ["a", "b"], file=str(path)) is None
    assert path.read_bytes() == b"a\nb\n"
    assert stri_printf("%s", "only", file=str(path), sep="|") is None
    assert path.read_bytes() == b"only"


def test_locale_and_info_use_icu_76():
    previous = stri_locale_get()
    stri_locale_set("en_US")
    assert stri_info(True) == (
        "stringi_1.8.9 (en_US.UTF-8; ICU4C 76.1 [system#U_CHARSET_IS_UTF8]; Unicode 16.0)"
    )
    info = stri_info(False)
    assert info["Unicode.version"] == "16.0"
    assert info["ICU.version"] == "76.1"
    assert info["ICU.system"] is True
    assert info["ICU.UTF8"] is True
    assert info["Charset.internal"] == ["UTF-8", "UTF-16"]
    assert info["Charset.native"]["Name.friendly"] == "UTF-8"
    assert info["Charset.native"]["Name.IBM"] == "ibm-1208"
    assert is_na(info["Charset.native"]["Unicode.1to1"])
    assert stri_locale_info("pl_PL") == stri_locale_info("Pl_pL")
    assert stri_locale_info("C")["Name"] == "en_US_POSIX"
    assert stri_locale_info("en_US.UTF-8")["Name"] == "en_US"
    assert stri_locale_info("zh_Hant_TW")["Name"] == "zh_Hant_TW"
    names = stri_locale_list()
    assert names[0] == "af"
    assert names[-1] == "zu_ZA"
    assert len(names) == 869
    try:
        assert stri_locale_set("de_AT") == "en_US"
        assert stri_locale_get() == "de_AT"
        assert stri_locale_info(None)["Name"] == "de_AT"
        assert stri_locale_info("@collation=phonebook")["Name"] == "de_AT@collation=phonebook"
        assert "de_AT.UTF-8" in stri_info(True)
    finally:
        stri_locale_set(previous)


def test_stats_match_the_installed_counts():
    sample = [
        "Lorem ipsum dolor sit amet, consectetur adipisicing elit.",
        "nibh augue, suscipit a, scelerisque sed, lacinia in, mi.",
        "Cras vel lorem. Etiam pellentesque aliquet tellus.",
        "",
    ]
    assert stri_stats_general(sample) == {
        "Lines": 4,
        "LinesNEmpty": 3,
        "Chars": 163,
        "CharsNWhite": 142,
    }
    assert stri_stats_general(["a", NA, "  ", "\u00a0b"]) == {
        "Lines": 3,
        "LinesNEmpty": 2,
        "Chars": 5,
        "CharsNWhite": 2,
    }
    latex = [
        "Lorem \\textbf{ipsum} dolor sit \\textit{amet}, consectetur adipisicing elit.",
        "\\begin{small}Proin nibh augue,\\end{small} suscipit a, scelerisque sed, lacinia in, mi.",
        "",
    ]
    assert stri_stats_latex(latex) == {
        "CharsWord": 96,
        "CharsCmdEnvir": 38,
        "CharsWhite": 27,
        "Words": 18,
        "Cmds": 2,
        "Envirs": 1,
    }
    assert stri_stats_latex(["a % comment", "\\% not", "42test 42.2", NA])["Words"] == 3
    with pytest.raises(ValueError, match="newline"):
        stri_stats_general("a\nb")


def test_wrap_matches_the_probed_paragraphs():
    text = (
        "Lorem ipsum dolor sit amet, consectetur adipisicing elit. Proin "
        "nibh augue, suscipit a, scelerisque sed, lacinia in, mi. Cras vel "
        "lorem. Etiam pellentesque aliquet tellus."
    )
    greedy = stri_wrap(text, 20, 0.0)
    assert greedy[0] == "Lorem ipsum dolor"
    assert greedy[-1] == "tellus."
    assert len(greedy) == 11
    dynamic = stri_wrap(text, 20, 2.0)
    assert dynamic[0] == "Lorem ipsum"
    assert len(dynamic) == 11
    wrapped = stri_wrap(
        text, 24, 0, indent=2, exdent=4, prefix="> ", initial="* ", normalize=False
    )
    assert wrapped[0].startswith("*   Lorem")
    assert wrapped[1].startswith(">     ")
    assert stri_wrap("hello   world  wide", 10, 0, whitespace_only=True, normalize=False) == [
        "hello  ",
        "world ",
        "wide",
    ]
    assert stri_wrap("一一 一一 一", 4, 0, use_length=False, normalize=False) == ["一一", "一一", "一"]
    assert stri_wrap("a😀 b cd", 3, 0, normalize=False) == ["a😀", "b", "cd"]
    assert stri_wrap("hello\nworld  there", 10, 0, normalize=True) == ["hello", "world", "there"]
    assert stri_wrap(["ab cd ef", NA], 4, 0, normalize=False) == ["ab", "cd", "ef", NA]
    with pytest.raises(ValueError, match="newline"):
        stri_wrap("hello\nworld", 10, 0, normalize=False)


def test_files_round_trip(tmp_path: Path):
    path = tmp_path / "lines.txt"
    assert stri_write_lines(["a", "b", ""], str(path)) is None
    assert stri_read_raw(str(path)) == [97, 10, 98, 10, 10]
    assert stri_read_lines(str(path)) == ["a", "b", ""]
    latin = tmp_path / "latin.txt"
    stri_write_lines("café", str(latin), encoding="latin1")
    assert stri_read_raw(str(latin)) == [99, 97, 102, 233, 10]
    assert stri_read_lines(str(latin), encoding="latin1") == ["café"]
    mixed = tmp_path / "mixed.txt"
    mixed.write_bytes(b"hello\r\nworld\n\n")
    assert stri_read_lines(str(mixed)) == ["hello", "world", ""]
    with pytest.raises(ValueError, match="can only write vector objects"):
        stri_write_lines(["a", NA], str(path))
    with pytest.raises(ValueError, match="auto"):
        stri_read_lines(str(path), encoding="auto")


def test_random_properties_do_not_require_a_shared_stream():
    shuffled = stri_rand_shuffle(["abcd", NA, ""])
    assert sorted(shuffled[0]) == list("abcd")
    assert shuffled[1] is NA
    assert shuffled[2] == ""
    drawn = stri_rand_strings(4, [3, 5], ["[0-9]", "[abc]"])
    assert [len(item) for item in drawn] == [3, 5, 3, 5]
    assert set(drawn[0]) <= set("0123456789")
    assert set(drawn[1]) <= set("abc")
    assert stri_rand_strings(0, 3) == []
    paragraphs = stri_rand_lipsum(2, True)
    assert len(paragraphs) == 2
    assert paragraphs[0].startswith("Lorem ipsum dolor sit amet")
    assert all(item.endswith(".") and "\n" not in item for item in paragraphs)
    plain = stri_rand_lipsum(1, False)
    assert len(plain) == 1 and plain[0].endswith(".")
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        alias = stri_rand_lipsum(nparagraphs=1)
    assert len(alias) == 1
    assert any("nparagraphs" in str(item.message) for item in caught)
