"""getVDigest against digest 0.6.39 and the vectors in man/vdigest.Rd."""

import inspect
import os
import stat

import pytest

from digest import NA, character, digest, factor, integer, logical, raw, real, rlist
from digest.hashing import ALGOS, DigestError
from digest.vdigest import getVDigest

LETTERS = list("abcdefghijklmnopqrstuvwxyz")
SHA1_LETTERS = [
    "1f9928593251410322823fefea8c3ef79b4d0254",
    "ee6e7fdb03a0d35b3a6f499d0f8f610686551d51",
    "8e7f9fe32c49050c5ca146150fc58b93fbeea245",
    "e59165f73b7dc7e0d6ae94ec9aac9e8e95fd8a2c",
    "7f608bde8f0e308aa8866d737ddebbfae9674163",
    "86e99e22d003547538a5f446165488f7861fa2c3",
    "ce27dce0e84ad90d3e90e9b571a73720d0fb4890",
    "221799200137b7d72dfc4a618465bec71333a58b",
    "13b5c7533cccc95d2f7cd18df78ea78ed9111c02",
    "88b7c7c5f6921ec9e914488067552829a17a42a4",
    "6127e4cdbf02f18898554c037f0d4acb95c608ab",
    "984ca0fd9ed47ac08a31aeb88f9c9a5f905aeaa2",
    "954da0ea9a5d0aa42516beebc5542c638161934c",
    "7d1e34387808d9f726efbb1c8eb0819a115afb52",
    "2e21764867596d832896d9d28d6e6489a0b27249",
    "666881f1f74c498e0292ccf3d9d26089ee79dae7",
    "966dbbe6cf1c43ac784a8257b57896db9fd3f357",
    "4ab40e0c23010553e9e4c058ef58f50088f9e87c",
    "bfa0e51b33ebd3b9a823368b7e4c357b2b98790b",
    "fc1ba0a4718421f0050cc5e159703838f733aa59",
    "25cce9eca8abedab78a765b49e74fba77f4463d4",
    "9d453f3128cb2fd55684b979a11d47c97f12dc87",
    "d612108f47c8accbeffd2d9d54c1fa7f74fb432d",
    "ef60fa66262167e7a31398b16fa762151c6d1b28",
    "a235e3cc7109def777a99e660b9829cea48ce9a4",
    "d19d82f849bad81a39da932d3087a60c78de82c1",
]
MD5_INPUT = [
    "",
    "a",
    "abc",
    "message digest",
    "abcdefghijklmnopqrstuvwxyz",
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789",
    "1234567890" * 8,
]
MD5_OUTPUT = [
    "d41d8cd98f00b204e9800998ecf8427e",
    "0cc175b9c0f1b6a831c399e269772661",
    "900150983cd24fb0d6963f7d28e17f72",
    "f96b697d7cb7938d525a2f31aaf161d0",
    "c3fcd3d76192e4007dfb496cca67e13b",
    "d174ab98d277d9f5a5611c2c9f419d9f",
    "57edf4a22be3c955ac49da2e2107b67a",
]
SHA512_EMPTY = (
    "cf83e1357eefb8bdf1542850d66d8007d620e4050b5715dc83f4a921d36ce9ce"
    "47d0d13c5d85f2b0ff8318d2877eec2f63b931bd47417a81a538327af927da3e"
)
SHA512_FOX = (
    "91ea1245f20d46ae9a037a989f54f1f790f0a47607eeb8a14d12890cea77a1bb"
    "c6c7ed9cf205e67b7f2b8fd4c7dfd3a7a8617e45f3c463d481c7e586c39ac1ed"
)
INTEGER_1_TO_5 = [
    "4b5630ee914e848e8d07221556b0a2fb",
    "c01f179e4b57ab8bd9de309e6d576c48",
    "11946e7a3ed5e1776e81c0f0ecd383d0",
    "234a2a5581872457b9fe1187d1616b13",
    "dd4ad37ee474732a009111e3456e7ed7",
]


def test_sha1_letters_matches_r():
    sha1 = getVDigest(algo="sha1")
    assert sha1(LETTERS) == SHA1_LETTERS
    assert sha1(LETTERS)[0] == digest("a", algo="sha1")


def test_md5_manual_vectors_without_serialization():
    assert getVDigest()(MD5_INPUT, serialize=False) == MD5_OUTPUT


def test_sha512_manual_vectors_without_serialization():
    fox = "The quick brown fox jumps over the lazy dog."
    assert getVDigest(algo="sha512")(["", fox], serialize=False) == [SHA512_EMPTY, SHA512_FOX]


def test_integer_vector_matches_digest_of_each_integer():
    result = getVDigest()(integer([1, 2, 3, 4, 5]))
    assert result == INTEGER_1_TO_5
    assert result == [digest(integer([value])) for value in range(1, 6)]
    assert result[0] == digest(integer([1]))
    assert result[0] != digest(1)


def test_python_ints_are_doubles_and_a_string_list_is_character():
    assert getVDigest()([1, 2, 3]) == [digest(1), digest(2), digest(3)]
    assert getVDigest()([1])[0] == digest(1)
    assert getVDigest()(["abc"]) == [digest("abc")]
    assert getVDigest()([["abc"]]) == [digest(["abc"])]
    assert getVDigest()(["abc"]) != getVDigest()([["abc"]])


def test_returned_function_has_digest_arguments_except_raw():
    fn = getVDigest()
    assert list(inspect.signature(fn).parameters) == [
        "object",
        "serialize",
        "file",
        "length",
        "skip",
        "ascii",
        "seed",
        "serializeVersion",
    ]


def test_unique_prefix_selects_the_algorithm():
    assert getVDigest("sha2")("a", serialize=False) == [digest("a", algo="sha256", serialize=False)]
    assert getVDigest("sp")(integer([1])) == [digest(integer([1]), algo="spookyhash")]
    assert getVDigest("xxh3_1")("a", serialize=False) == [digest("a", algo="xxh3_128", serialize=False)]
    assert getVDigest("crc32")("abc", serialize=False) == [digest("abc", algo="crc32", serialize=False)]
    assert getVDigest(list(ALGOS))("a", serialize=False) == [digest("a", serialize=False)]
    with pytest.raises(DigestError):
        getVDigest("sha")
    with pytest.raises(DigestError):
        getVDigest("xx")
    with pytest.raises(DigestError):
        getVDigest("nope")


def test_raw_vector_is_one_hash_without_serialization_and_one_per_byte_with_it():
    blob = bytes([1, 2, 3, 4])
    assert getVDigest()(blob, serialize=False) == ["08d6c05a21512a79a1dfeb9d2a8f262f"]
    assert getVDigest()(raw(blob), serialize=False) == [digest(raw(blob), serialize=False)]
    assert getVDigest()(blob) == [
        "b49a88311202fa4b5557848680328202",
        "2381102fb929ca1fa5e6fb33a32fd97b",
        "f29c3b68f78da72f19ab5685eab911d0",
        "bf30eea83c08143b1d32ece64a10d2f9",
    ]
    assert getVDigest()(blob) == [digest(raw(bytes([byte]))) for byte in blob]


def test_empty_objects_and_null():
    assert getVDigest()(integer([])) == ["3e2e4a08c44d0224de5b7e668c75ace3"]
    assert getVDigest()(character([])) == ["5152ac13bdd09110d9ee9c169a3d9237"]
    assert getVDigest()(character([]), serialize=False) == ["d4cd0dabcf4caa22ad92fab40844c786"]
    assert getVDigest()(raw(b"")) == ["0bab3c984e04f3150b65ccaf2c83535a"]
    assert getVDigest()(b"", serialize=False) == ["d41d8cd98f00b204e9800998ecf8427e"]
    assert getVDigest()(None) == ["f9e884084b84794d762a535f3facec85"]
    assert getVDigest()([]) == ["db41907f4f43686fe19edc3d7eb61082"]
    assert getVDigest(algo="spookyhash")(None) == []
    assert getVDigest(algo="spookyhash")(integer([])) == []
    assert getVDigest(algo="spookyhash")(raw(b"")) == []


def test_character_na_logical_factor_and_real_na():
    assert getVDigest()(["a", NA], serialize=False) == [
        digest("a", serialize=False),
        "d4cd0dabcf4caa22ad92fab40844c786",
    ]
    assert getVDigest()(logical([True, False, NA])) == [
        digest(True),
        digest(False),
        digest(NA),
    ]
    assert getVDigest()(real([1.5, NA])) == [digest(real([1.5])), digest(real([NA]))]
    assert getVDigest()(factor(["b", "a", "b"])) == [
        "f2f13db8cbdec936859b28d8de935912",
        "c9302088d980264a7878811e3e564bbb",
        "f2f13db8cbdec936859b28d8de935912",
    ]


def test_r_list_serializes_each_element_and_refuses_plain_bytes():
    assert getVDigest()(rlist(["a", "b"])) == [digest("a"), digest("b")]
    with pytest.raises(DigestError, match="character or raw"):
        getVDigest()(rlist(["a", "b"]), serialize=False)
    with pytest.raises(DigestError, match="character or raw"):
        getVDigest()(integer([1]), serialize=False)


def test_errormode_warn_returns_na_and_silent_returns_none():
    with pytest.warns(UserWarning, match="character or raw"):
        assert getVDigest(errormode="warn")(integer([1]), serialize=False) is NA
    assert getVDigest(errormode="silent")(1, serialize=False) is None
    with pytest.warns(UserWarning, match="not available without serialization"):
        warned = getVDigest(algo="spookyhash", errormode="warn")(integer([1]), serialize=False)
    assert warned == [digest(integer([1]), algo="spookyhash", skip=0)]
    assert getVDigest(algo="spookyhash", errormode="silent")(integer([1]), serialize=False) == warned
    with pytest.raises(DigestError, match="not available without serialization"):
        getVDigest(algo="spookyhash")(integer([1]), serialize=False)
    with pytest.raises(DigestError, match="can not be used with files"):
        getVDigest(algo="spookyhash")("plain", file=True)
    with pytest.warns(UserWarning, match="can not be used with files"):
        assert getVDigest(algo="spookyhash", errormode="warn")("plain", file=True) is NA
    assert getVDigest(algo="spookyhash", errormode="silent")("plain", file=True) is None


def test_skip_prefix_length_and_seed():
    md5 = getVDigest()
    assert md5(integer([1]), skip="a") == md5(integer([1]))
    assert md5(integer([1]), skip="nope") == md5(integer([1]), skip=0)
    assert md5(integer([1]), skip=0) != md5(integer([1]))
    assert md5(["abcd", "efgh"], serialize=False, skip=1, length=2) == [
        digest("abcd", serialize=False, skip=1, length=2),
        digest("efgh", serialize=False, skip=1, length=2),
    ]
    xx = getVDigest("xxhash64")
    assert xx(integer([1, 2]), seed=5) == [
        digest(integer([1]), algo="xxhash64", seed=5),
        digest(integer([2]), algo="xxhash64", seed=5),
    ]
    assert xx(["ab", "cd"], serialize=False, seed=-1) == [
        digest("ab", algo="xxhash64", serialize=False, seed=-1),
        digest("cd", algo="xxhash64", serialize=False, seed=-1),
    ]


def test_file_hash_and_errors(tmp_path):
    path = tmp_path / "abc.bin"
    path.write_bytes(b"abc")
    assert getVDigest()(str(path), file=True) == [digest(str(path), file=True)]
    assert getVDigest()(file=str(path)) == [digest(str(path), file=True)]
    missing = str(tmp_path / "missing.bin")
    with pytest.raises(DigestError, match="does not exist"):
        getVDigest()(missing, file=True)
    with pytest.warns(UserWarning, match="does not exist"):
        with pytest.raises(DigestError, match="Cannot open input file"):
            getVDigest(errormode="warn")(missing, file=True)
    with pytest.raises(DigestError, match="length > 1"):
        getVDigest()([str(path), str(path)], file=True)
    with pytest.raises(DigestError, match="length zero"):
        getVDigest()(character([]), file=True)
    with pytest.raises(DigestError, match="not a file"):
        getVDigest()(str(tmp_path), file=True)
    locked = tmp_path / "locked.bin"
    locked.write_bytes(b"abc")
    os.chmod(locked, 0)
    try:
        if not os.access(locked, os.R_OK):
            with pytest.raises(DigestError, match="not readable"):
                getVDigest()(str(locked), file=True)
    finally:
        os.chmod(locked, stat.S_IRUSR | stat.S_IWUSR)


def test_ascii_skip_errors_on_a_list_of_serializations():
    assert getVDigest()(real([]), ascii=True) == ["fe77a1ac9a460b3cb57eae22cffa4bf0"]
    with pytest.raises(DigestError, match="cannot be coerced to type 'raw'"):
        getVDigest()(1, ascii=True)
