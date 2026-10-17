"""Checks for the stringi encoding exports."""

from __future__ import annotations

import pytest

from stringi._na import NA, is_na
from stringi.encoding import (
    stri_conv,
    stri_enc_detect,
    stri_enc_detect2,
    stri_enc_fromutf32,
    stri_enc_get,
    stri_enc_info,
    stri_enc_isascii,
    stri_enc_isutf16be,
    stri_enc_isutf16le,
    stri_enc_isutf32be,
    stri_enc_isutf32le,
    stri_enc_isutf8,
    stri_enc_list,
    stri_enc_mark,
    stri_enc_set,
    stri_enc_toascii,
    stri_enc_tonative,
    stri_enc_toutf32,
    stri_enc_toutf8,
    stri_encode,
)

ENG = " ".join(["The quick brown fox jumps over the lazy dog."] * 8)
PL = " ".join(["Zażółć gęślą jaźń."] * 8)


def test_conv_is_encode():
    assert stri_conv is stri_encode


def test_isascii_keeps_na_distinct_from_text():
    assert stri_enc_isascii(["abc", "ą", "", NA, "NA", "a\x01b"]) == [
        True,
        False,
        True,
        NA,
        True,
        True,
    ]
    assert stri_enc_isascii("NA") is True
    assert stri_enc_isascii(NA) is NA
    assert stri_enc_isascii([]) == []
    assert stri_enc_isascii(b"") is True
    assert stri_enc_isascii(bytes([65, 0, 127, 128])) is False
    assert stri_enc_isascii([bytes([65, 66]), None, bytes([255]), b""]) == [
        True,
        NA,
        False,
        True,
    ]


def test_utf_checkers_follow_icu_rules():
    assert stri_enc_isutf8(["abc", "ą", NA, ""]) == [True, True, NA, True]
    assert stri_enc_isutf8(bytes([0xC0, 0x80])) is False
    assert stri_enc_isutf8(bytes([97, 0, 98])) is False
    assert stri_enc_isutf16be(b"ab") is True
    assert stri_enc_isutf16le(b"ab") is True
    assert stri_enc_isutf16be(bytes([0x00, 0x61, 0x00, 0x62])) is True
    assert stri_enc_isutf16le(bytes([0x61, 0x00, 0x62, 0x00])) is True
    assert stri_enc_isutf16be(bytes([0x00, 0x61, 0x00])) is False
    assert stri_enc_isutf32be(bytes([0, 0, 0, 0x61])) is True
    assert stri_enc_isutf32le(bytes([0x61, 0, 0, 0])) is True
    assert stri_enc_isutf32be(b"abcd") is False
    assert stri_enc_isutf32le(b"abcd") is False
    assert stri_enc_isutf16be(None) is NA


def test_fromutf32_and_toutf32_round_trip():
    assert stri_enc_fromutf32([65, 0x105]) == "Aą"
    with pytest.warns(UserWarning, match="invalid Unicode code point"):
        converted = stri_enc_fromutf32(
            [[65, 0x105], None, [], [NA], [0], [0x110000], [0xD800]]
        )
    assert converted[0] == "Aą"
    assert converted[1] is NA
    assert converted[2] == ""
    assert all(is_na(item) for item in converted[3:])
    assert stri_enc_fromutf32(None) is NA
    assert stri_enc_fromutf32([]) == []
    assert stri_enc_fromutf32([[]]) == [""]
    assert stri_enc_toutf32(["ab", NA, "", "ą", "\U0001F606", "\ufeffab"]) == [
        [97, 98],
        None,
        [],
        [261],
        [128518],
        [97, 98],
    ]


def test_ascii_utf8_native_and_mark():
    assert stri_enc_toascii(["ab", "ą", NA, ""]) == ["ab", "\x1a", NA, ""]
    assert stri_enc_toutf8(["\ufeffabc", "abc", NA]) == ["abc", "abc", NA]
    assert stri_enc_tonative(["ab", "ą", NA, "\ufeffabc"]) == ["ab", "ą", NA, "\ufeffabc"]
    assert stri_enc_mark(["abc", "ą", NA, "", "NA"]) == ["ASCII", "UTF-8", NA, "ASCII", "ASCII"]
    assert stri_enc_mark(bytes([0x41, 0xFF])) == ["ASCII", "ASCII"]


def test_encode_bytes_and_errors():
    assert stri_encode(["ab", "ą", "€", NA], to="ISO-8859-2", to_raw=True) == [
        [97, 98],
        [0xB1],
        [0x1A],
        None,
    ]
    assert stri_encode(bytes([0xB1]), from_="ISO-8859-2", to="UTF-8") == "ą"
    assert stri_encode("é", to="ISO-8859-1") == "é"
    assert stri_encode("ą", to="ISO-8859-2") == b"\xb1"
    assert stri_encode(bytes([0xFF, 0x41]), from_="UTF-8", to="UTF-8", to_raw=True) == [
        239,
        191,
        189,
        65,
    ]
    assert stri_encode("ab", to="UTF-16BE", to_raw=True) == [0, 97, 0, 98]
    assert stri_encode("ab", to="UTF-16", to_raw=True) == [255, 254, 97, 0, 98, 0]
    with pytest.raises(ValueError, match="embedded nul"):
        stri_encode("ab", to="UTF-16BE")
    with pytest.raises(ValueError, match="U_FILE_ACCESS_ERROR"):
        stri_enc_info("not-a-charset")


def test_detect_matches_icu_guesses():
    frame = stri_enc_detect(ENG)
    assert frame["Encoding"][0] == "ISO-8859-1"
    assert frame["Language"][0] == "en"
    assert frame["Confidence"][0] == pytest.approx(0.53)
    assert frame["Language"][1] == ""
    polish = stri_enc_detect(PL)
    assert polish["Encoding"][0] == "UTF-8"
    assert polish["Confidence"][0] == pytest.approx(1)
    empty = stri_enc_detect("")
    assert empty["Encoding"] == ["UTF-8"]
    assert empty["Language"] == [""]
    assert empty["Confidence"] == pytest.approx([0.15])
    missing = stri_enc_detect(NA)
    assert missing["Encoding"] == [NA]
    assert missing["Language"] == [NA]
    assert missing["Confidence"] == [NA]
    assert stri_enc_detect([]) == []


def test_detect2_skips_null_locale_and_scores_polish():
    with pytest.warns(UserWarning, match="stri_enc_detect2 is deprecated"):
        hello = stri_enc_detect2("hello")
    assert hello["Encoding"] == ["US-ASCII"]
    assert hello["Language"] == [NA]
    assert hello["Confidence"] == pytest.approx([1])
    with pytest.warns(UserWarning, match="stri_enc_detect2 is deprecated"):
        polish = stri_enc_detect2(PL)
    assert polish["Encoding"] == ["UTF-8"]
    assert polish["Confidence"] == pytest.approx([1])
    raw = bytes(stri_encode(PL, to="windows-1250", to_raw=True))
    with pytest.warns(UserWarning, match="stri_enc_detect2 is deprecated"):
        guessed = stri_enc_detect2([raw], locale="pl")[0]
    assert guessed["Encoding"][:3] == ["windows-1250", "ibm-1250_P100-1995", "ISO-8859-2"]
    assert guessed["Confidence"][2] == pytest.approx(0.6111111111111112)
    with pytest.warns(UserWarning, match="stri_enc_detect2 is deprecated"):
        failed = stri_enc_detect2("")
    assert failed["Confidence"] == [NA]


def test_list_info_get_and_locked_set():
    names = stri_enc_list()
    assert len(names) == 1203
    assert names[:8] == ["037", "273", "277", "278", "280", "284", "285", "297"]
    assert names[-1] == "x11-compound-text"
    families = stri_enc_list(False)
    assert len(families) == 232
    assert families["UTF-8"][0] == "cp1208"
    assert "UTF-8" in families["UTF-8"]
    assert isinstance(stri_enc_list("TRUE"), dict)
    info = stri_enc_info("UTF-8")
    assert info["Name.friendly"] == "UTF-8"
    assert info["Name.ICU"] == "UTF-8"
    assert info["Name.IBM"] == "ibm-1208"
    assert info["ASCII.subset"] is True
    assert info["Unicode.1to1"] is NA
    assert info["CharSize.min"] == 1
    assert info["CharSize.max"] == 3
    latin = stri_enc_info("ISO-8859-2")
    assert latin["Name.friendly"] == "ISO-8859-2"
    assert latin["Name.ICU"] == "ibm-912_P100-1995"
    assert latin["Unicode.1to1"] is True
    assert stri_enc_get() == "UTF-8"
    with pytest.warns(UserWarning, match="no effect"):
        previous = stri_enc_set("ISO-8859-2")
    assert previous == "UTF-8"
    assert stri_enc_get() == "UTF-8"
    with pytest.raises(ValueError, match="missing values"):
        stri_enc_set(NA)
    with pytest.raises(ValueError, match="incorrect character encoding identifier"):
        stri_enc_set("")
