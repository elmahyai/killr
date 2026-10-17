"""hmac against the installed digest 0.6.39 and the manual's RFC 2104 vectors."""

import warnings
from pathlib import Path

import pytest

from digest.hashing import DigestError
from digest.hmac import hmac

_JEFE = "Jefe"
_NOTHING = "what do ya want for nothing?"
_MD5 = "750c783e6ab0b503eaa86e310a5db738"
_SHA1 = "effcdf6ae5eb2fa2d27416d5f184df9c259a7c79"
_SHA512 = (
    "164b7a7bfcf819e2e395fbe73b56e0a387bd64222e831fd610270cd7ea250554"
    "9758bf75c05a994a6d034f65f8f0e6fdcaeab1a34d4a6b4b636e070a38bce737"
)
_SHA5_BLOCK64 = (
    "d2766eca33fe852bd629253fe01c63519eb2459bdb0af254bd4341740b4d0ea7"
    "23c6a2a4dfc34252891c14f2658055237aa3f64962d4d4de2170ae18fd9160aa"
)


def test_manual_examples():
    assert hmac(_JEFE, _NOTHING, "md5") == _MD5
    assert hmac([0x0B] * 16, "Hi There", "md5") == "9294727a3638bb1c13f48ef8158bfc9d"
    assert hmac([0xAA] * 16, [0xDD] * 50, "md5") == "56be34521d144c88dbb8c733f0e8b3f6"
    assert hmac(_JEFE, _NOTHING, "sha1") == _SHA1
    assert hmac([0x0B] * 16, "Hi There", "sha1") == "675b0b3a1b4ddf4e124872da6c2f632bfed957e9"
    assert hmac([0xAA] * 16, [0xDD] * 50, "sha1") == "d730594d167e35d5956fd8003d0db3d3f46dc7bb"


def test_example_output_is_saved():
    root = Path(__file__).resolve().parents[1]
    r_text = (root / "docs" / "output" / "hmac-r.txt").read_text(encoding="ascii")
    py_text = (root / "docs" / "output" / "hmac-python.txt").read_text(encoding="ascii")
    assert r_text == f'[1] "{_MD5}"\n'
    assert py_text == f"{_MD5}\n"
    assert r_text.strip() != ""
    assert py_text.strip() != ""


def test_sha256_and_sha512_block_sizes():
    assert hmac("key", "The quick brown fox jumps over the lazy dog", "sha256") == (
        "f7bc83f430538424b13298e6aa6fb143ef4d59a14946175997479dbc2d1a3cd8"
    )
    assert hmac(_JEFE, _NOTHING, "sha512") == _SHA512
    assert hmac([1] * 127, "z", "sha512") == (
        "32032879bf54cc598d951be530641ca751b023bc80db19ad3d05c305a48a767e"
        "50bd18431ed8a1a0551ecc3e34e10a58cc3e4162e06ace82b413a8ccf3f76de5"
    )
    assert hmac([1] * 128, "z", "sha512") == (
        "723a124af321b2eda177304147b6ea3f2e393b55e7252f6ecbd4cafaa971677f"
        "5282d8893cac95105a63a6050c90203173ea2de68be675dcd06ecf940816bcff"
    )
    assert hmac([1] * 129, "z", "sha512") == (
        "791555ea44ec53e1191de873494e4527e946490d28eeba36c97b5d7cb25edaeb"
        "53619ee824b9cb5382682a94f2f79c574a62a85168a5f330f2bd28657e5236a0"
    )


def test_unique_prefix_is_resolved_by_digest():
    assert hmac(_JEFE, _NOTHING, "md") == _MD5
    assert hmac(_JEFE, _NOTHING, "sha1") == _SHA1
    assert hmac(_JEFE, _NOTHING, "sha2") == hmac(_JEFE, _NOTHING, "sha256")
    assert hmac(_JEFE, _NOTHING, "sha25") == hmac(_JEFE, _NOTHING, "sha256")
    # "sha5" matches sha512, but the block-size test is exact, so the block stays 64.
    assert hmac(_JEFE, _NOTHING, "sha5") == _SHA5_BLOCK64
    assert hmac(_JEFE, _NOTHING, "sha51") == _SHA5_BLOCK64
    assert hmac(_JEFE, _NOTHING, algo=["sha5"]) == _SHA5_BLOCK64
    assert hmac(_JEFE, _NOTHING, algo=["sha512"]) == _SHA512
    with pytest.raises(DigestError):
        hmac(_JEFE, _NOTHING, "sha")
    with pytest.raises(DigestError):
        hmac(_JEFE, "hi", "m")
    with pytest.raises(DigestError):
        hmac(_JEFE, "hi", "crc")


def test_default_algo_is_md5_and_a_long_vector_is_rejected():
    assert hmac(_JEFE, "hi") == hmac(_JEFE, "hi", "md5")
    with pytest.raises(ValueError, match="length > 1"):
        hmac(_JEFE, "hi", algo=["md5", "sha1", "crc32", "sha256", "sha512"])
    with pytest.raises(ValueError, match="length zero"):
        hmac(_JEFE, "hi", algo=[])


def test_crc32_short_key_and_long_key_substring():
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        assert hmac(_JEFE, _NOTHING, "crc32") == "ae2cebcc"
        assert hmac([1, 2, 3], "Hi", "crc32") == "3365e7e4"
        assert hmac(bytes([1, 2, 3, 4]), "Hi", "crc32") == "bd58ea0c"
        assert hmac([1] * 3, "z", "crc32") == "46ae8718"
        assert hmac([1] * 4, "z", "crc32") == "812a8c98"
    with pytest.warns(UserWarning, match="out-of-range values treated as 0"):
        assert hmac([0x0B] * 16, "Hi There", "crc32") == "930083ba"
    with pytest.warns(UserWarning, match="out-of-range values treated as 0"):
        assert hmac([1, 2, 3, 4, 5], "Hi", "crc32") == "211dafe3"
    with pytest.warns(UserWarning, match="out-of-range values treated as 0"):
        assert hmac([0xAB] * 80, "x", "crc32") == "a6319dca"
    with pytest.warns(UserWarning, match="out-of-range values treated as 0"):
        assert hmac([1] * 5, "z", "crc32") == "a1f4bcd9"
    with pytest.warns(UserWarning, match="out-of-range values treated as 0"):
        assert hmac([1] * 8, "z", "crc32") == "aad802d3"


def test_key_padded_or_hashed_to_the_block():
    assert hmac([0x11] * 63, "x", "md5") == "65742927a10e02d754ec46e67233f80d"
    assert hmac([0x11] * 64, "x", "md5") == "a9fa4e995e332b45266eabd6115ec15a"
    assert hmac([0x11] * 65, "x", "md5") == "f235ad8014b465d2ae78e271055d59c2"
    assert hmac([0xAB] * 80, "x", "md5") == "143717866e49de88ac14d7bc4a330ebf"
    assert hmac(b"", "abc", "md5") == "dd2701993d29fdd0b032c233cec63403"
    assert hmac("", "abc", "md5") == "dd2701993d29fdd0b032c233cec63403"
    assert hmac([1, 2, 3], "abc", "md5") == "80b71311ae0e9ab92f4e0b63f2f99149"
    assert hmac(1, "abc", "md5") == "d7eccb467dfe39431bc0eff7f900e210"


def test_raw_object_matches_its_bytes_and_raw_result_is_bytes():
    assert hmac(_JEFE, _NOTHING.encode("ascii"), "md5") == _MD5
    assert hmac(_JEFE.encode("ascii"), "abc", "md5") == "0c23dc19a0f341f59659378f4621bb4b"
    assert hmac(_JEFE, b"abc", "sha256") == (
        "7cf4ec4f741f51cb0d887013c46251d6f4175643c4f422906a1aaec688cc13e8"
    )
    assert hmac(_JEFE, _NOTHING, "md5", raw=True) == bytes.fromhex(_MD5)
    assert hmac(_JEFE, "hi", "md5", raw=0) == "a03c6b902ea92845ddc3dccd2beb12a6"
    assert hmac(_JEFE, "hi", "md5", raw=1) == bytes.fromhex("a03c6b902ea92845ddc3dccd2beb12a6")
    with pytest.raises(ValueError, match="length > 1"):
        hmac(_JEFE, "hi", "md5", raw=[True, False])


def test_serialize_and_extra_keywords_go_to_digest():
    assert hmac(_JEFE, _NOTHING, "md5", serialize=True) == "98881bd65f4b951b808b4442d02fe56c"
    assert hmac(_JEFE, _NOTHING, "sha1", serialize=True) == "3413e2c5dc4b7afca091ad93e9808252cb86bc32"
    assert hmac(_JEFE, bytes(3), "sha1", serialize=True) == "b9fac9463961a7d7462b05da816c62949d457f9d"
    assert hmac(_JEFE, _NOTHING, "md5", length=4) == "a130655eebff2e276386a132304d93f1"
    assert hmac(_JEFE, _NOTHING, "md5", skip=2) == "8892efa7edaa5afd7e8fc272c0b1f01b"
    # length truncates the message hashes. The key hash stays serialize=FALSE and raw.
    assert hmac([0xAB] * 80, "x", "md5", length=4) == "cdaa904ad2deaebab13376e43513d83c"
    with pytest.raises(DigestError, match="file=TRUE"):
        hmac(_JEFE, "hi", "md5", file=True)
