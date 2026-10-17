"""Checks for stri_length, stri_isempty, stri_numbytes, and stri_width."""

from __future__ import annotations

import pytest

from stringi._na import NA, is_na
from stringi.length import (
    _character_double,
    stri_isempty,
    stri_length,
    stri_numbytes,
    stri_width,
)


def test_length_keeps_na_distinct_from_the_string_na():
    assert stri_length(NA) is NA
    assert stri_length("NA") == 2
    assert stri_length("") == 0
    assert stri_length("abc") == 3
    assert stri_length(["abc", NA, "", "NA"]) == [3, NA, 0, 2]
    assert all(item is NA or isinstance(item, int) for item in stri_length(["abc", NA]))


def test_length_coerces_numbers_the_way_r_does():
    assert stri_length([1, 2, 3]) == [1, 1, 1]
    assert stri_length(True) == 4
    assert stri_length(False) == 5
    assert stri_length([1, True]) == [1, 1]
    assert stri_length(1e-4) == 5
    assert stri_length(1e5) == 5
    assert stri_length(10000000) == 8
    assert stri_length(10000000.0) == 5
    assert stri_length([10000000, 1.0]) == [5, 1]
    assert stri_length(float("inf")) == 3
    assert stri_length(float("-inf")) == 4
    assert stri_length(float("nan")) == 3
    assert stri_length(1 + 2j) == 4
    assert stri_length([1, 1 + 2j]) == [4, 4]
    assert stri_length(["a", 1, True, NA, 1.5]) == [1, 1, 4, NA, 3]
    assert stri_length(None) == []
    assert stri_length([]) == []


def test_double_formatting_matches_probed_r_strings():
    cases = {
        0.0: "0",
        -0.0: "0",
        1.0: "1",
        -1.0: "-1",
        0.1: "0.1",
        1 / 3: "0.333333333333333",
        1e-4: "1e-04",
        1e-10: "1e-10",
        1e5: "1e+05",
        1e16: "1e+16",
        1e20: "1e+20",
        9999999.0: "9999999",
        1e7: "1e+07",
        1.2345678901234567: "1.23456789012346",
        2**-1074: "4.94065645841247e-324",
        float("inf"): "Inf",
        float("-inf"): "-Inf",
        float("nan"): "NaN",
        123456789012345.0: "123456789012345",
        0.0001234567890123456: "0.000123456789012346",
        float(2**53): "9007199254740992",
        float(2**53 + 2): "9007199254740994",
        1223383794756801.25: "1223383794756801",
        4069807855039402.5: "4069807855039402",
    }
    for value, text in cases.items():
        assert _character_double(value) == text
        assert stri_length(value) == len(text)


def test_numbytes_is_utf8_length_and_keeps_na():
    assert stri_numbytes("\u0105") == 2
    assert stri_length("\u0105") == 1
    assert stri_numbytes("\U0001F600") == 4
    assert stri_length("\U0001F600") == 1
    assert stri_numbytes(NA) is NA
    assert stri_numbytes("") == 0
    assert stri_numbytes("abc") == 3
    assert stri_numbytes(["\u0105", NA, ""]) == [2, NA, 0]


def test_isempty_is_true_only_for_an_empty_string():
    assert stri_isempty("") is True
    assert stri_isempty(NA) is NA
    assert stri_isempty("a") is False
    assert stri_isempty("NA") is False
    assert stri_isempty(" ") is False
    assert stri_isempty(["", NA, "a"]) == [True, NA, False]
    assert is_na(stri_isempty(NA))
    assert stri_isempty([1, 2, 3]) == [False, False, False]
    assert stri_isempty(None) == []


def test_width_follows_the_installed_rules():
    assert stri_width(list("ABCDE")) == [1, 1, 1, 1, 1]
    assert stri_width("\U0001F606") == 2
    assert stri_width("\uFF21") == 2
    assert stri_width("\u3000") == 2
    assert stri_width("\u00AD") == 1
    assert stri_width("\u200B") == 0
    assert stri_width("\u0301") == 0
    assert stri_width("\u0000") == 0
    assert stri_width("\u1161") == 0
    assert stri_width("\u11A8") == 0
    assert stri_width("\uD7B0") == 0
    assert stri_width("\uD7CB") == 0
    assert stri_width("\u1100") == 2
    assert stri_width("A\u0301") == 1
    assert stri_width("\uFE0F") == 0
    assert stri_width("\U0001F3FB") == 0
    assert stri_width("\U0001F1FA\U0001F1F8") == 2
    assert stri_width("\U0001F1FA\U0001F1F8\U0001F1E6\U0001F1F9") == 4
    assert stri_width("\U0001F1E6\U0001F1E7\U0001F1E8") == 4
    assert stri_width("\U0001F468\u200D\U0001F469") == 2
    assert stri_width("\U0001F468\u200D\U0001F469\u200D\U0001F467") == 2
    assert stri_width("\u200D\u2640") == 0
    assert stri_width("\u200D\u0061") == 1
    assert stri_width("\u2764\uFE0F") == 2
    assert stri_width(NA) is NA
    assert stri_width("") == 0


def test_width_unicode16_marks_symbols_and_emoji():
    assert stri_width(chr(0x1171E)) == 1
    assert stri_width(chr(0x897)) == 0
    assert stri_width(chr(0x1D360)) == 2
    assert stri_width(chr(0x1F8B2)) == 2
    assert stri_width("\u200D" + chr(0x1F8B2)) == 2
    assert stri_width(chr(0x1FAE9)) == 2
    assert stri_width("\u200D" + chr(0x1FAE9)) == 0
    assert stri_width(chr(0x2427)) == 2
    assert stri_width(chr(0x18CFF)) == 2


def test_rejected_values():
    with pytest.raises(TypeError):
        stri_length(b"abc")
    with pytest.raises(TypeError):
        stri_length([None])
    with pytest.raises(TypeError):
        stri_width({"a": "b"})
