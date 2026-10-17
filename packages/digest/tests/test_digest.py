"""Checks for digest() against the vectors published in the digest manual."""

import pytest

from digest import character, data_frame, digest, integer, integer_matrix
from digest.hashing import DigestError


def test_md5_abc():
    assert digest("abc", serialize=False) == "900150983cd24fb0d6963f7d28e17f72"


def test_empty_md5():
    assert digest("", serialize=False) == "d41d8cd98f00b204e9800998ecf8427e"


def test_list_example():
    value = digest([
        character(list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")),
        data_frame(
            a=character(list("abcde")),
            b=integer_matrix(list(range(1, 11)), ncol=2),
        ),
    ])
    assert value == "a3bd4d45da8cc4b923bd40cbb98af657"


def test_double_and_integer():
    assert digest(1) == "6717f2823d3202449301145073ab8719"
    assert digest(integer([1])) == "4b5630ee914e848e8d07221556b0a2fb"


def test_length_and_skip():
    assert digest("abc", serialize=False, length=2) == "187ef4436122d1cc2f40dc2b92f0eba0"
    assert digest("abc", serialize=False, skip=1) == "5360af35bde9ebd8f01f492dc059593c"


def test_spooky_skips_header():
    assert digest("abc", algo="spookyhash", skip=30) == "67c93775f715ab8ab01178caf86713c6"


def test_xxh3_128_message():
    assert digest("message digest", algo="xxh3_128", serialize=False) == (
        "34ab715d95e3b6490abfabecb8e3a424"
    )


def test_ambiguous_prefix():
    with pytest.raises(DigestError):
        digest("abc", algo="sha", serialize=False)


def test_ascii_matches_r():
    assert digest(1, ascii=True) == "834c18784a1634b9e3b6ed60c8158010"
    assert digest(integer([1]), ascii=True) == "ce047904e9c4a0704686bb8f753e3acd"
    assert digest("héllo", ascii=True) == "7e6f377fbf423fcd3e4332fe063720e5"
    assert digest("a\t\r\b\f\v\a\\'\"?", ascii=True) == "8003a4ac2ea1f133fd6b628088284771"
    assert digest([
        character(list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")),
        data_frame(
            a=character(list("abcde")),
            b=integer_matrix(list(range(1, 11)), ncol=2),
        ),
    ], ascii=True) == "807af8c89fdef921df2b84276a4ced6e"
