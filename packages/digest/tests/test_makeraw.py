"""makeRaw against the installed digest 0.6.39 coercions."""

import warnings
from pathlib import Path

import pytest

from digest.makeraw import DigestHex, makeRaw, make_raw_digest

_HEX_ERROR = "'x' cannot be coerced to class \"hexmode\""
_CHAR_WARN = (
    "argument should be a character vector of length 1\n"
    "all but the first element will be ignored"
)
_RAW_WARN = "out-of-range values treated as 0 in coercion to raw"


def test_example_string_is_char_to_raw():
    text = "1234567890ABCDE"
    assert makeRaw(text) == text.encode("ascii")
    assert makeRaw(text) == bytes.fromhex(
        "31 32 33 34 35 36 37 38 39 30 41 42 43 44 45"
    )


def test_example_output_matches_r_print():
    root = Path(__file__).resolve().parents[1]
    r_text = (root / "docs" / "output" / "makeRaw-r.txt").read_text(encoding="ascii")
    py_text = (root / "docs" / "output" / "makeRaw-python.txt").read_text(encoding="ascii")
    expected = " [1] 31 32 33 34 35 36 37 38 39 30 41 42 43 44 45\n"
    assert r_text == expected
    assert py_text == expected


def test_raw_returns_the_same_bytes():
    raw = b"\x00\xff\x10"
    assert makeRaw(raw) is raw
    mutable = bytearray(b"\x01\x02")
    copied = makeRaw(mutable)
    assert copied == b"\x01\x02"
    mutable[0] = 9
    assert copied == b"\x01\x02"


def test_utf8_and_ascii_bytes():
    assert makeRaw("hello") == b"hello"
    assert makeRaw("café") == bytes([0x63, 0x61, 0x66, 0xC3, 0xA9])
    assert makeRaw("") == b""


def test_longer_character_vector_warns_and_keeps_the_first():
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        assert makeRaw(["AB", "CD"]) == b"AB"
        assert makeRaw(("é", "x", "y")) == "é".encode("utf-8")
    assert len(caught) == 2
    assert str(caught[0].message) == _CHAR_WARN
    assert str(caught[1].message) == _CHAR_WARN


def test_one_string_in_a_list_does_not_warn():
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        assert makeRaw(["AB"]) == b"AB"


def test_plain_string_is_not_parsed_as_hex():
    assert makeRaw("ab") == b"ab"
    assert makeRaw("gg") == b"gg"
    assert make_raw_digest("ab") == bytes([0xAB])
    assert makeRaw(DigestHex("ab")) == bytes([0xAB])
    with pytest.raises(ValueError, match="hexmode") as raised:
        makeRaw(DigestHex("gg"))
    assert str(raised.value) == _HEX_ERROR


def test_digest_pairs_and_odd_length():
    assert make_raw_digest("deadbeef") == bytes.fromhex("deadbeef")
    assert make_raw_digest("DEADBEEF") == bytes.fromhex("deadbeef")
    assert make_raw_digest("abc") == bytes([0xAB, 0x0C])
    assert make_raw_digest("abcde") == bytes([0xAB, 0xCD, 0x0E])
    assert make_raw_digest("100") == bytes([0x10, 0x00])
    assert make_raw_digest("a") == bytes([0x0A])
    assert make_raw_digest("+a") == bytes([0x0A])
    assert make_raw_digest("-0") == bytes([0x00])
    assert make_raw_digest(" f") == bytes([0x0F])
    assert make_raw_digest("\t1") == bytes([0x01])
    assert make_raw_digest("Ff") == bytes([0xFF])


def test_digest_rejects_bad_hex_and_an_empty_string():
    for text in ("gg", "0g", "g0", "-1", "0x", "0x10", "f ", ""):
        with pytest.raises(ValueError) as raised:
            make_raw_digest(text)
        if text == "":
            assert str(raised.value) == "wrong sign in 'by' argument"
        else:
            assert str(raised.value) == _HEX_ERROR


def test_as_raw_truncation_and_one_warning():
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        assert makeRaw([-0.1, 255.9, 0.9, 1.2, 254.9]) == bytes([0, 255, 0, 1, 254])
        assert makeRaw(list(range(256))) == bytes(range(256))
        assert makeRaw(0x36) == bytes([0x36])
        assert makeRaw(54.9) == bytes([54])
        assert makeRaw(True) == bytes([1])
        assert makeRaw(False) == bytes([0])
        assert makeRaw([]) == b""
        assert makeRaw(()) == b""
        assert makeRaw(None) == b""

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        result = makeRaw([-1, 300, 1.9, 256, -1.9, float("nan"), float("inf"), float("-inf")])
    assert result == bytes([0, 0, 1, 0, 0, 0, 0, 0])
    assert len(caught) == 1
    assert str(caught[0].message) == _RAW_WARN


def test_integer_out_of_range_warns_once():
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        result = makeRaw(list(range(257)))
    assert result == bytes(range(256)) + b"\x00"
    assert len(caught) == 1
    assert str(caught[0].message) == _RAW_WARN
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        assert makeRaw([-5, 10, 10**20]) == bytes([0, 10, 0])
    assert len(caught) == 1
