"""digest2int against the values R 4.5 and digest 0.6.39 returned."""

import math
import warnings

import pytest

from digest.digest2int import digest2int

FOX = "The quick brown fox jumps over the lazy dog"
LETTERS = ["a", "b", "c", "d", "e"]


def test_manual_example_is_a_one_element_list():
    result = digest2int(FOX, 0)
    assert result == [1369346549]
    assert result[0] == 1369346549
    assert digest2int(FOX) == result
    assert digest2int(FOX, 0) == digest2int([FOX], 0)


def test_package_letter_vectors():
    assert digest2int(LETTERS) == [
        -902917054,
        14385563,
        -289776295,
        592496261,
        286663184,
    ]
    assert digest2int(LETTERS, 1) == [
        14385563,
        -289776295,
        592496261,
        286663184,
        1208324078,
    ]
    assert digest2int("cat sat on the mat") == [562079877]


def test_empty_string_and_na_character():
    assert digest2int("") == [0]
    assert digest2int("", 1) == [294921]
    assert digest2int("", -1) == [-1835000]
    na = digest2int([None])
    assert na == digest2int("NA")
    assert na == [-1112759537]
    assert digest2int(["a", "", None, FOX]) == [
        -902917054,
        0,
        -1112759537,
        1369346549,
    ]
    assert digest2int([]) == []
    assert digest2int(()) == []


def test_other_strings_and_a_high_bit_seed():
    assert digest2int(FOX, -1) == [1478279487]
    assert digest2int(FOX, 2147483647) == [559072408]
    assert digest2int(FOX, -2147483648) == [-1425095235]
    assert digest2int("a", -1) == [-595805986]
    assert digest2int("a", 2147483647) == [-1903232802]
    assert digest2int("a", None) == [2084623426]
    assert digest2int("\u00a5") == [1898621243]
    assert digest2int("caf\u00e9") == [-644058978]
    assert digest2int("caf\u00e9", -1) == [769113467]


def test_zero_byte_ends_the_string():
    assert digest2int("a\x00b") == digest2int("a")
    assert digest2int("a\x00b", -1) == digest2int("a", -1)


def test_seed_coercion_matches_as_integer():
    assert digest2int("a", 1.9) == digest2int("a", 1)
    assert digest2int("a", -1.9) == digest2int("a", -1)
    assert digest2int("a", True) == digest2int("a", 1)
    assert digest2int("a", False) == digest2int("a", 0)
    assert digest2int("a", "3") == [592496261]
    assert digest2int("a", "  -12  ") == digest2int("a", -12)
    assert digest2int("a", "1e2") == digest2int("a", 100)
    assert digest2int("a", "0x10") == digest2int("a", 16)
    assert digest2int("a", "0x1.8p1") == digest2int("a", 3)
    assert digest2int("a", [5, 9]) == [1208324078]
    assert digest2int("a", [1.9, 2.2]) == digest2int("a", 1)
    assert digest2int("a", b"\x03\x04") == digest2int("a", 3)
    assert digest2int("a", []) == digest2int("a", None)
    assert digest2int("a", float("nan")) == digest2int("a", None)
    assert digest2int("a", -0.0) == digest2int("a", 0)
    assert digest2int("a", 2 + 0j) == digest2int("a", 2)


def test_seed_warnings():
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        assert digest2int("a", "foo") == [2084623426]
    assert [str(item.message) for item in caught] == ["NAs introduced by coercion"]

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        assert digest2int("a", 3e9) == [2084623426]
    assert [str(item.message) for item in caught] == [
        "NAs introduced by coercion to integer range"
    ]

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        assert digest2int("a", float("inf")) == [2084623426]
    assert [str(item.message) for item in caught] == [
        "NAs introduced by coercion to integer range"
    ]

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        assert digest2int("a", "") == [2084623426]
    assert caught == []

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        assert digest2int("a", "NaN") == [2084623426]
    assert caught == []

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        digest2int("a", ["x", "1e99"])
    assert [str(item.message) for item in caught] == [
        "NAs introduced by coercion",
        "NAs introduced by coercion to integer range",
    ]

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        assert digest2int("a", 2 + 3j) == digest2int("a", 2)
    assert [str(item.message) for item in caught] == [
        "imaginary parts discarded in coercion"
    ]

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        digest2int("a", 2 + 0j)
    assert caught == []


def test_invalid_input():
    for value in (1, 1.0, None, b"a", True, {"a": "b"}, object()):
        with pytest.raises(ValueError, match="invalid input - should be character vector"):
            digest2int(value)
    with pytest.raises(ValueError, match="invalid input - should be character vector"):
        digest2int(["a", 1])
    with pytest.raises(ValueError, match="cannot coerce type 'dict' to vector of type 'integer'"):
        digest2int("a", {"seed": 1})


def test_strings_are_independent():
    together = digest2int(["a", FOX, ""], -1)
    apart = [digest2int(text, -1)[0] for text in ("a", FOX, "")]
    assert together == apart
    assert all(isinstance(item, int) and not isinstance(item, bool) for item in together)
    assert math.isfinite(together[0])
