"""sha1, sha1_attr_digest, and sha1_digest against digest 0.6.39."""

import math
import warnings
from pathlib import Path

import pytest

from digest import character, data_frame, digest, integer_matrix
from digest.hashing import DigestError, get_option, set_option
from digest.serialize import (
    NA,
    Obj,
    character as r_character,
    factor,
    integer,
    integer_matrix as r_integer_matrix,
    logical,
    raw,
    real,
    real_matrix,
    rlist,
    symbol,
)
from digest.sha1 import num2hex, sha1, sha1_attr_digest, sha1_digest

_OUTPUT = Path(__file__).resolve().parents[1] / "docs" / "output"
_HASH = '[1] "fe50fd4ad46d4410a866d82ffcc8686c763dc2f8"\n'
_ATTR = '[1] "6bf849396360d9f2152fde6cdaab2d9f192cb9b6"\n'
_NULL = '[1] "8d9c05ec7ae28b219c4c56edbce6a721bd68af82"\n'


def test_num2hex_matches_r_sprintf_layout():
    values = [
        1,
        2,
        3,
        0,
        -1,
        NA,
        math.inf,
        -math.inf,
        1e-10,
        math.pi,
        2**-10,
        1.5,
        0.1,
        -0.0,
    ]
    assert num2hex(values) == [
        " 0",
        " 1",
        "8 1",
        "0",
        "- 0",
        NA,
        "Inf",
        "-Inf",
        "0",
        "921fb54442d1 1",
        " -10",
        "8 0",
        "999999999999 -4",
        "0",
    ]
    assert num2hex([math.pi], digits=4) == ["921f 1"]
    assert num2hex([1e-7]) == ["ad7f29abcaf4 -24"]


def test_numeric_integer_character_logical():
    assert sha1(real([1, 2, 3])) == "fe50fd4ad46d4410a866d82ffcc8686c763dc2f8"
    assert sha1(integer([1, 2, 3])) == "555f6bea49e58a2c2541060a21c2d4f9078c3086"
    assert sha1(r_character(["a", "b"])) == "590958de263d35341c79e9a2c8e52b7ee3061f33"
    assert sha1(logical([True, False, NA])) == "71743fa208c50b0ae0d768ecfd6bf46e9fe267e0"


def test_list_data_frame_and_matrix():
    assert sha1(rlist([1, "x"], names=["a", "b"])) == (
        "8f1e8a0a3d02e63e4229a0edf386ef891d6f63ce"
    )
    assert sha1(data_frame(a=integer([1, 2]), b=r_character(["x", "y"]))) == (
        "7e065f96e67c2f61993769487f58390abba9f059"
    )
    assert sha1(real_matrix([1, 2, 3, 4], ncol=2, nrow=2)) == (
        "dca646117b26b07dcd931e964deeaffb85bf29f7"
    )
    assert sha1(r_integer_matrix([1, 2, 3, 4], ncol=2, nrow=2)) == (
        "e5250b713a88f58ec0a42a6eed49cecbcf9adc6a"
    )


def test_attr_digest_and_null_digest():
    assert sha1_attr_digest("hello") == "6bf849396360d9f2152fde6cdaab2d9f192cb9b6"
    assert sha1("hello") == "6bf849396360d9f2152fde6cdaab2d9f192cb9b6"
    assert sha1_digest(None) == "8d9c05ec7ae28b219c4c56edbce6a721bd68af82"
    assert sha1(None) == "8d9c05ec7ae28b219c4c56edbce6a721bd68af82"
    assert sha1(symbol("foo")) == "c140c659ba168108aa1b0d14898d4246f7114224"


def test_factor_raw_complex_date_array_anova():
    assert sha1(factor(["b", "a", "b"])) == "d2dbf10bd01910825e1babc3e00ce691a9f939dc"
    assert sha1(raw([1, 2, 255])) == "83a49742046f388127e7cceb3da208ca721d73f9"
    assert sha1(Obj("complex", [(1.0, 2.0)])) == "7abb9556c5df84b73f9b49be67b556d59bbe5e42"
    date = Obj("real", [18263.0], [("class", r_character(["Date"]))], object_bit=True)
    assert sha1(date) == "fa6a74b43d1bba2cfd7d932740fa6ff736f7a1fd"
    array = Obj("real", [float(i) for i in range(1, 9)], [("dim", integer([2, 2, 2]))])
    assert sha1(array) == "0b74ac84a2c23688082708a513caf982d2498ae8"
    table = data_frame(Df=real([1.0, 2.0]), Sum=real([1.23456789, 2.5]))
    table.attributes = [
        ("names", r_character(["Df", "Sum.Sq"])),
        ("class", r_character(["anova", "data.frame"])),
        ("row.names", integer([NA, -2])),
    ]
    table.object_bit = True
    assert sha1(table) == "a0544dae1f429cc15b9d78ff0ce8ca504c5c87aa"


def test_srcref_is_dropped_and_old_version_skips_attributes():
    named = real([1.0, 2.0])
    named.attributes = [
        ("names", r_character(["a", "b"])),
        ("srcref", r_character(["dropme"])),
        ("foo", integer([3])),
    ]
    assert sha1(named) == "4eaea23f0400dda8ef042ea1cc93a1bd307acc11"
    previous = get_option("sha1PackageVersion")
    try:
        set_option("sha1PackageVersion", "0.6.22")
        plain = real([1.0, 2.0])
        plain.attributes.append(("names", r_character(["a", "b"])))
        assert sha1(plain) == "a08dc1d24fc2e6d74b771994626934162ce5b122"
    finally:
        set_option("sha1PackageVersion", previous)


def test_posixct_and_function_and_call():
    moment = Obj(
        "real",
        [1577934245.0],
        [
            ("class", r_character(["POSIXct", "POSIXt"])),
            ("tzone", r_character(["UTC"])),
        ],
        object_bit=True,
    )
    assert sha1(moment) == "f74e47409de7f2990a58cbdcaaace66d6c355f27"
    missing = Obj("missing")
    formals = Obj(
        "pairlist",
        [missing, real([1.0])],
        [("names", r_character(["x", "y"]))],
    )
    fn = Obj(
        "function",
        {
            "formals": formals,
            "body": r_character(["+", "x", "y"]),
            "environment": Obj("globalenv"),
        },
    )
    assert sha1(fn, environment=False) == "7a49424a6b4fe191a7403a2c59989c0e3caa66ae"
    call = Obj(
        "lang",
        None,
        car=symbol("foo"),
        cdr=Obj("pairlist", None, car=real([1.0]), cdr=Obj("null")),
    )
    assert sha1(call) == "95ccaf9c07f023ec15230cf2533e656d9e5c2bf5"


def test_unknown_class_warns_and_falls_back():
    obj = real([1.0, 2.0])
    obj.attributes.append(("class", r_character(["thing"])))
    obj.object_bit = True
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        value = sha1(obj)
    assert value == "db1c425a2fe4afed3e7a527369dc89216a340dd0"
    message = str(caught[0].message)
    assert message == (
        "sha1() has no method for the 'thing' class, so using fallback.\n"
        "Please read the note in ?digest::sha1on why this might be a problem."
    )


def test_bad_digits_are_rejected():
    with pytest.raises(DigestError, match="digits is not integer"):
        sha1(real([1.0]), digits=1.5)


def test_symbol_refs_do_not_change_the_digest_example():
    value = digest([
        character(list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")),
        data_frame(
            a=character(list("abcde")),
            b=integer_matrix(list(range(1, 11)), ncol=2),
        ),
    ])
    assert value == "a3bd4d45da8cc4b923bd40cbb98af657"


def test_captured_examples_match_r_print():
    assert (_OUTPUT / "sha1-r.txt").read_text(encoding="ascii") == _HASH
    assert (_OUTPUT / "sha1-python.txt").read_text(encoding="ascii") == _HASH
    assert (_OUTPUT / "sha1_attr_digest-r.txt").read_text(encoding="ascii") == _ATTR
    assert (_OUTPUT / "sha1_attr_digest-python.txt").read_text(encoding="ascii") == _ATTR
    assert (_OUTPUT / "sha1_digest-r.txt").read_text(encoding="ascii") == _NULL
    assert (_OUTPUT / "sha1_digest-python.txt").read_text(encoding="ascii") == _NULL
