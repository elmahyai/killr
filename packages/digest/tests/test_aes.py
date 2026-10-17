"""AES against the FIPS-197 and SP 800-38A examples in digest 0.6.39."""

import warnings

import pytest

from digest.aes import AES


def hx(text: str) -> bytes:
    return bytes.fromhex(text)


FIPS_PLAIN = hx("00112233445566778899aabbccddeeff")
FIPS_128 = hx("000102030405060708090a0b0c0d0e0f")
FIPS_192 = hx("000102030405060708090a0b0c0d0e0f1011121314151617")
FIPS_256 = hx("000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f")

SP_PLAIN = hx(
    "6bc1bee22e409f96e93d7e117393172a"
    "ae2d8a571e03ac9c9eb76fac45af8e51"
    "30c81c46a35ce411e5fbc1191a0a52ef"
    "f69f2445df4f9b17ad2b417be66c3710"
)
SP_KEY = hx("2b7e151628aed2a6abf7158809cf4f3c")
SP_IV = hx("000102030405060708090a0b0c0d0e0f")
CTR_IV = hx("f0f1f2f3f4f5f6f7f8f9fafbfcfdfeff")


def test_fips197_ecb():
    cases = (
        (FIPS_128, "69c4e0d86a7b0430d8cdb78070b4c55a"),
        (FIPS_192, "dda97ca4864cdfe06eaf70a0ec0d7191"),
        (FIPS_256, "8ea2b7ca516745bfeafc49904b496089"),
    )
    for key, expected_hex in cases:
        aes = AES(key)
        ciphertext = aes.encrypt(FIPS_PLAIN)
        assert ciphertext == hx(expected_hex)
        assert aes.decrypt(ciphertext, raw=True) == FIPS_PLAIN
        assert aes.block_size() == 16
        assert aes.key_size() == len(key)
        assert aes.mode() == "ECB"


def test_sp800_38a():
    ecb = hx(
        "3ad77bb40d7a3660a89ecaf32466ef97"
        "f5d3d58503b9699de785895a96fdbaaf"
        "43b1cd7f598ece23881b00e3ed030688"
        "7b0c785e27e8ad3f8223207104725dd4"
    )
    cbc = hx(
        "7649abac8119b246cee98e9b12e9197d"
        "5086cb9b507219ee95db113a917678b2"
        "73bed6b8e3c1743b7116e69e22229516"
        "3ff1caa1681fac09120eca307586e1a7"
    )
    cfb = hx(
        "3b3fd92eb72dad20333449f8e83cfb4a"
        "c8a64537a0b3a93fcde3cdad9f1ce58b"
        "26751f67a3cbb140b1808cf187a4f4df"
        "c04b05357c5d1c0eeac4c66f9ff7f2e6"
    )
    ctr = hx(
        "874d6191b620e3261bef6864990db6ce"
        "9806f66b7970fdff8617187bb9fffdff"
        "5ae4df3edbd5d35e5b4f09020db03eab"
        "1e031dda2fbe03d1792170a0f3009cee"
    )
    aes = AES(SP_KEY)
    assert aes.encrypt(SP_PLAIN) == ecb
    assert aes.decrypt(ecb, raw=True) == SP_PLAIN

    aes = AES(SP_KEY, mode="CBC", IV=SP_IV)
    assert aes.encrypt(SP_PLAIN) == cbc
    aes = AES(SP_KEY, mode="CBC", IV=SP_IV)
    assert aes.decrypt(cbc, raw=True) == SP_PLAIN

    aes = AES(SP_KEY, mode="CFB", IV=SP_IV)
    assert aes.encrypt(SP_PLAIN) == cfb
    aes = AES(SP_KEY, mode="CFB", IV=SP_IV)
    assert aes.decrypt(cfb, raw=True) == SP_PLAIN

    aes = AES(SP_KEY, mode="CTR", IV=CTR_IV)
    assert aes.encrypt(SP_PLAIN) == ctr
    aes = AES(SP_KEY, mode="CTR", IV=CTR_IV)
    assert aes.decrypt(ctr, raw=True) == SP_PLAIN


def test_mode_prefix_and_rejection():
    key = bytes(range(1, 17))
    assert AES(key, mode="E").mode() == "ECB"
    assert AES(key, mode="CB").mode() == "CBC"
    assert AES(key, mode="CF").mode() == "CFB"
    assert AES(key, mode="CT").mode() == "CTR"
    assert AES(key, mode=None).mode() == "ECB"
    quoted = "\u201cECB\u201d, \u201cCBC\u201d, \u201cCFB\u201d, \u201cCTR\u201d"
    for mode in ("C", "PGP", "OFB", "OPENPGP", "ecb", ""):
        with pytest.raises(ValueError, match="should be one of " + quoted):
            AES(key, mode=mode)
    with pytest.raises(ValueError, match="must be of length 1"):
        AES(key, mode=["ECB", "CBC"])
    with pytest.raises(ValueError, match="must be NULL or a character vector"):
        AES(key, mode=1)


def test_padding_only_for_cbc_and_key_length():
    key = bytes(range(1, 17))
    with pytest.raises(ValueError, match="Only CBC mode supports padding"):
        AES(key, mode="ECB", padding=True)
    with pytest.raises(ValueError, match="Only CBC mode supports padding"):
        AES(key, mode="CTR", IV=key, padding=True)
    with pytest.raises(ValueError, match="16, 24 and 32 byte keys"):
        AES(b"")
    with pytest.raises(ValueError, match="16, 24 and 32 byte keys"):
        AES(bytes(15))
    assert AES(bytes(24)).key_size() == 24
    assert AES(bytes(32)).key_size() == 32
    with pytest.raises(ValueError, match="16, 24 and 32 byte keys"):
        AES(None)


def test_null_iv_and_print():
    aes = AES(bytes(range(1, 17)))
    assert aes.IV() == b""
    assert str(aes) == "AES cipher object; mode ECB key size 16 "
    assert f"{aes}\n" == "AES cipher object; mode ECB key size 16 \n"


def test_character_and_raw_encrypt_match():
    key = hx("2b7e151628aed2a6abf7158809cf4f3c")
    text = "0123456789ABCDEF"
    assert AES(key).encrypt(text) == AES(key).encrypt(text.encode("ascii"))
    aes = AES(key)
    ciphertext = aes.encrypt(text)
    aes = AES(key)
    assert aes.decrypt(ciphertext) == text
    assert aes.decrypt(ciphertext, raw=True) == text.encode("ascii")


def test_cbc_padding_examples():
    raw_text = b"0123456789ABCDEF"
    plain = AES(raw_text, "CBC", raw_text).encrypt(raw_text)
    padded = AES(raw_text, "CBC", raw_text, padding=True).encrypt(raw_text)
    assert len(plain) == 16
    assert len(padded) == 32
    assert plain == padded[:16]
    assert padded.hex() == "9d2cda901b682d3359709a5ab24196242125333bdf540132179ac0de79e1837a"
    assert AES(raw_text, "CBC", raw_text).decrypt(plain) == raw_text.decode()
    assert AES(raw_text, "CBC", raw_text, padding=True).decrypt(padded) == raw_text.decode()

    with pytest.raises(ValueError, match=r"multiple of 16 bytes, or use `padding=TRUE`"):
        AES(raw_text, "CBC", raw_text).encrypt("testing")
    testing = AES(raw_text, "CBC", raw_text, padding=True).encrypt("testing")
    assert testing.hex() == "4017d340b6eafbb66c3dfceb10808cff"
    assert (
        AES(raw_text, "CBC", raw_text, padding=True).decrypt(
            AES(raw_text, "CBC", raw_text, padding=True).encrypt("testing")
        )
        == "testing"
    )
    longer = "testingalongerstring"
    assert (
        AES(raw_text, "CBC", raw_text, padding=True).encrypt(longer).hex()
        == "2d870ada654f4bdff182497a88e08013a232bfb5701c12a4d3b29f4f66e74ecd"
    )
    assert (
        AES(raw_text, "CBC", raw_text, padding=True).decrypt(
            AES(raw_text, "CBC", raw_text, padding=True).encrypt(longer)
        )
        == longer
    )


def test_cfb_short_string_and_iv_length():
    key = hx("2b7e151628aed2a6abf7158809cf4f3c")
    iv = hx("000102030405060708090a0b0c0d0e0f")
    text = "This is very secret string"
    expected = hx("04960ebfb9044196ac6c4590bbdc8903e1259a479e199af94518")
    aes = AES(key, mode="CFB", IV=iv)
    ciphertext = aes.encrypt(text)
    assert ciphertext == expected
    assert len(aes.IV()) == 10
    aes = AES(key, mode="CFB", IV=iv)
    assert aes.decrypt(ciphertext) == text
    aes = AES(key, mode="CFB", IV=b"")
    with pytest.raises(ValueError, match="IV length must equal block size"):
        aes.encrypt(SP_PLAIN)
    with pytest.raises(ValueError, match="IV length must equal block size"):
        AES(key, mode="CFB", IV=bytes(15)).decrypt(SP_PLAIN)


def test_iv_is_updated_and_streaming_matches_one_shot():
    key = bytes(range(1, 17))
    iv = bytes(range(16))
    msg = bytes(list(range(1, 17)) * 2)
    for mode in ("CBC", "CFB", "CTR"):
        whole = AES(key, mode=mode, IV=iv).encrypt(msg)
        aes = AES(key, mode=mode, IV=iv)
        parts = aes.encrypt(msg[:16]) + aes.encrypt(msg[16:])
        assert parts == whole
        fresh = AES(key, mode=mode, IV=iv)
        assert fresh.decrypt(whole, raw=True) == msg
        continued = AES(key, mode=mode, IV=iv)
        continued.encrypt(msg)
        assert continued.decrypt(whole, raw=True) != msg


def test_ecb_length_and_empty():
    key = bytes(range(1, 17))
    aes = AES(key)
    assert aes.encrypt(b"") == b""
    assert aes.decrypt(b"", raw=True) == b""
    assert aes.decrypt(b"") == ""
    with pytest.raises(ValueError, match="Text length must be a multiple of 16 bytes"):
        aes.encrypt(bytes(15))
    with pytest.raises(ValueError, match="Ciphertext length must be a multiple of 16 bytes"):
        aes.decrypt(bytes(15))
    with pytest.raises(ValueError, match="Text must be a raw vector"):
        aes.encrypt([1, 2, 3])
    with pytest.raises(ValueError, match="Ciphertext must be a raw vector"):
        aes.decrypt("0123456789ABCDEF")


def test_pkcs_drop_uses_the_last_byte_only():
    key = bytes(range(1, 17))
    iv = bytes(range(16))
    block = bytes(range(1, 16)) + bytes([3])
    ciphertext = AES(key, "CBC", iv).encrypt(block)
    opened = AES(key, "CBC", iv, padding=True).decrypt(ciphertext, raw=True)
    assert opened == bytes(range(1, 14))
    zero = AES(key, "CBC", iv).encrypt(bytes(range(1, 16)) + bytes([0]))
    assert AES(key, "CBC", iv, padding=True).decrypt(zero, raw=True) == b""
    with pytest.raises(ValueError, match="invalid 'n'"):
        AES(key, "CBC", iv, padding=True).decrypt(b"", raw=True)


def test_ctr_counter_wrap_and_empty():
    key = bytes(range(1, 17))
    iv = bytes([255] * 16)
    aes = AES(key, mode="CTR", IV=iv)
    aes.encrypt(bytes(16))
    assert aes.IV() == bytes(16)
    aes = AES(key, mode="CTR", IV=iv)
    aes.encrypt(bytes(32))
    assert aes.IV() == bytes(15) + bytes([1])
    aes = AES(key, mode="CTR", IV=bytes(range(16)))
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        assert aes.encrypt(b"") == b""
    assert aes.IV() == bytes(range(15)) + bytes([0x11])
    assert any(
        "number of items to replace is not a multiple of replacement length" in str(item.message)
        for item in caught
    )


def test_trailing_nul_and_embedded_nul():
    key = bytes(range(1, 17))
    trailing = b"AB" + bytes(1)
    ciphertext = AES(key).encrypt(trailing + bytes(13))
    assert AES(key).decrypt(ciphertext) == "AB"
    embedded = bytes([65, 0, 66]) + bytes(13)
    ciphertext = AES(key).encrypt(embedded)
    with pytest.raises(ValueError, match=r"embedded nul in string: 'A\\0B"):
        AES(key).decrypt(ciphertext)
    high = bytes([65, 255, 66]) + bytes([1]) * 13
    ciphertext = AES(key).encrypt(high)
    assert AES(key).decrypt(ciphertext).encode("latin-1") == high


def test_cbc_final_iv_is_last_ciphertext_block():
    aes = AES(SP_KEY, mode="CBC", IV=SP_IV)
    ciphertext = aes.encrypt(SP_PLAIN)
    assert aes.IV() == ciphertext[-16:]
    aes = AES(SP_KEY, mode="CFB", IV=SP_IV)
    ciphertext = aes.encrypt(SP_PLAIN)
    assert aes.IV() == ciphertext[-16:]
    aes = AES(SP_KEY, mode="CTR", IV=CTR_IV)
    aes.encrypt(SP_PLAIN)
    assert aes.IV() == hx("f0f1f2f3f4f5f6f7f8f9fafbfcfdff03")
    aes = AES(SP_KEY, mode="ECB", IV=SP_IV)
    aes.encrypt(SP_PLAIN)
    assert aes.IV() == SP_IV
