"""The httr2 slice of the R package openssl.

SHA-256 uses hashlib. Base64 uses the standard library. AES-CTR, RSA key
generation, and random bytes go through the Rust crate opensslport, which
calls the same libssl the R package links.
"""

from __future__ import annotations

import base64
import hashlib

import opensslport


def _bytes(value) -> bytes:
    if isinstance(value, str):
        return value.encode("utf-8")
    if isinstance(value, (bytes, bytearray)):
        return bytes(value)
    raise TypeError("expected a string or raw vector")


_ALGOS = {
    "md5": hashlib.md5,
    "sha1": hashlib.sha1,
    "sha224": hashlib.sha224,
    "sha256": hashlib.sha256,
    "sha384": hashlib.sha384,
    "sha512": hashlib.sha512,
}


def _digest(name, x, key=None) -> str:
    if isinstance(x, (list, tuple)) and all(isinstance(item, str) for item in x) and key is None:
        return [_digest(name, item) for item in x]
    data = _bytes(x if not isinstance(x, (list, tuple)) else "".join(x))
    algo = _ALGOS[name]
    if key is None:
        return algo(data).hexdigest()
    import hmac
    return hmac.new(_bytes(key), data, algo).hexdigest()


def md5(x, key=None) -> str:
    return _digest("md5", x, key)


def sha1(x, key=None) -> str:
    return _digest("sha1", x, key)


def sha224(x, key=None) -> str:
    return _digest("sha224", x, key)


def sha256(x, key=None) -> str:
    return _digest("sha256", x, key)


def sha384(x, key=None) -> str:
    return _digest("sha384", x, key)


def sha512(x, key=None) -> str:
    return _digest("sha512", x, key)


def sha2(x, size=256, key=None) -> str:
    return _digest(f"sha{int(size)}", x, key)


def sha3(x, size=256, key=None) -> str:
    algo = getattr(hashlib, f"sha3_{int(size)}")
    return algo(_bytes(x)).hexdigest()


def blake2b(x, key=None) -> str:
    return hashlib.blake2b(_bytes(x)).hexdigest()


def blake2s(x, key=None) -> str:
    return hashlib.blake2s(_bytes(x)).hexdigest()


def ripemd160(x, key=None) -> str:
    return hashlib.new("ripemd160", _bytes(x)).hexdigest()


def keccak(x, size=256, key=None) -> str:
    return opensslport.digest_hex_ssl(f"keccak-{int(size)}", _bytes(x))


def md4(x, key=None) -> str:
    return opensslport.digest_hex_ssl("md4", _bytes(x))


def base64_encode(bin, linebreaks=False) -> str:
    if isinstance(bin, str):
        raw = bin.encode("utf-8")
    elif isinstance(bin, (list, tuple)) and bin and isinstance(bin[0], str):
        raw = "".join(bin).encode("utf-8")
    else:
        raw = bytes(bin)
    text = base64.b64encode(raw).decode("ascii")
    if linebreaks:
        chunks = [text[i:i + 64] for i in range(0, len(text), 64)]
        return "\n".join(chunks) + ("\n" if text else "")
    return text


def base64_decode(text) -> bytes:
    if isinstance(text, (bytes, bytearray)):
        text = bytes(text).decode("ascii")
    if text is None:
        return b""
    if isinstance(text, (list, tuple)):
        text = "".join(text)
    text = text.replace("\r", "").replace("\n", "")
    return base64.b64decode(text)


def rand_bytes(n=1) -> bytes:
    if not isinstance(n, (int, float)):
        raise RuntimeError("Please provide a numeric value for n")
    return opensslport.rand_bytes_ssl(int(n))


def aes_ctr_encrypt(data, key, iv=None) -> bytes:
    if iv is None:
        iv = rand_bytes(16)
    out = opensslport.aes_ctr_crypt(_bytes(data), bytes(key), bytes(iv), True)
    return out


def aes_ctr_decrypt(data, key, iv) -> bytes:
    return opensslport.aes_ctr_crypt(bytes(data), bytes(key), bytes(iv), False)


def aes_cbc_encrypt(data, key, iv=None) -> bytes:
    if iv is None:
        iv = rand_bytes(16)
    return opensslport.aes_cbc_crypt(_bytes(data), bytes(key), bytes(iv), True)


def aes_cbc_decrypt(data, key, iv) -> bytes:
    return opensslport.aes_cbc_crypt(bytes(data), bytes(key), bytes(iv), False)


def aes_gcm_encrypt(data, key, iv=None) -> bytes:
    if iv is None:
        iv = rand_bytes(12)
    return opensslport.aes_gcm_crypt(_bytes(data), bytes(key), bytes(iv), True)


def aes_gcm_decrypt(data, key, iv) -> bytes:
    return opensslport.aes_gcm_crypt(bytes(data), bytes(key), bytes(iv), False)


def rand_num(n=1):
    count = int(n)
    raw = rand_bytes(count * 8)
    values = []
    for index in range(count):
        chunk = raw[index * 8:(index + 1) * 8]
        values.append(sum(byte * 256 ** -(place + 1) for place, byte in enumerate(chunk)))
    return values[0] if count == 1 else values


def aes_keygen(length=16) -> bytes:
    return rand_bytes(int(length))


def fips_mode() -> bool:
    import ctypes
    lib = ctypes.CDLL("libcrypto.so.3")
    lib.EVP_default_properties_is_fips_enabled.argtypes = [ctypes.c_void_p]
    lib.EVP_default_properties_is_fips_enabled.restype = ctypes.c_int
    return bool(lib.EVP_default_properties_is_fips_enabled(None))


def multihash(x, algos=("md5", "sha1", "sha256", "sha384", "sha512")):
    return {name: _digest(name, x) for name in algos}


def askpass(prompt="Please enter your password: "):
    import askpass as ask
    return ask.askpass(prompt)


def rsa_keygen(bits=2048) -> bytes:
    return opensslport.rsa_keygen_der(int(bits))


class Bignum(int):
    """A positive integer. Printing it matches R's as.character.bignum."""


def bignum(x, hex=False):
    if isinstance(x, Bignum):
        return x
    if isinstance(x, bool) or not isinstance(x, (int, str, bytes, bytearray)):
        raise RuntimeError("Cannot convert to bignum: x must be positive integer, character or raw")
    if isinstance(x, int):
        if x < 0:
            raise RuntimeError("Cannot convert to bignum: x must be positive integer, character or raw")
        return Bignum(x)
    if isinstance(x, str):
        base = 16 if hex else 10
        return Bignum(int(x, base))
    return Bignum(int.from_bytes(bytes(x), "big"))


def bignum_mod_exp(a, b, m):
    return Bignum(pow(int(bignum(a)), int(bignum(b)), int(bignum(m))))


def bignum_mod_inv(a, m):
    return Bignum(pow(int(bignum(a)), -1, int(bignum(m))))


def openssl_config():
    import ctypes
    lib = ctypes.CDLL("libcrypto.so.3")
    lib.OpenSSL_version.argtypes = [ctypes.c_int]
    lib.OpenSSL_version.restype = ctypes.c_char_p
    version = lib.OpenSSL_version(0).decode()
    return {"version": version, "ec": True, "x25519": True, "fips": fips_mode()}


class _Key:
    def __init__(self, kind, raw, public):
        self.kind = kind
        self.raw = bytes(raw)
        self.pubkey = _Pubkey(kind, public)


class _Pubkey:
    def __init__(self, kind, raw):
        self.kind = kind
        self.raw = bytes(raw)


def _seed32(x):
    raw = bytes(x)
    if len(raw) == 64:
        raw = raw[:32]
    if len(raw) != 32:
        raise ValueError("key must have length 32")
    return raw


def read_ed25519_key(x):
    raw = _seed32(x)
    return _Key("ed25519", raw, opensslport.ed25519_public_ssl(raw))


def read_ed25519_pubkey(x):
    raw = bytes(x)
    if len(raw) != 32:
        raise ValueError("key must have length 32")
    return _Pubkey("ed25519", raw)


def read_x25519_key(x):
    raw = _seed32(x)
    return _Key("x25519", raw, opensslport.x25519_public_ssl(raw))


def read_x25519_pubkey(x):
    raw = bytes(x)
    if len(raw) != 32:
        raise ValueError("key must have length 32")
    return _Pubkey("x25519", raw)


def ed25519_keygen():
    return read_ed25519_key(rand_bytes(32))


def x25519_keygen():
    return read_x25519_key(rand_bytes(32))


def ed25519_sign(data, key):
    if not isinstance(key, _Key) or key.kind != "ed25519":
        raise TypeError("key must be an ed25519 key")
    return opensslport.ed25519_sign_ssl(key.raw, bytes(data))


def ed25519_verify(data, sig, pubkey):
    raw_sig = bytes(sig)
    if len(raw_sig) != 64:
        raise ValueError("Signature must have length 64")
    if isinstance(pubkey, _Key):
        pubkey = pubkey.pubkey
    return bool(opensslport.ed25519_verify_ssl(pubkey.raw, bytes(data), raw_sig))


def x25519_diffie_hellman(key, pubkey):
    if isinstance(pubkey, _Key):
        pubkey = pubkey.pubkey
    if not isinstance(key, _Key) or key.kind != "x25519":
        raise TypeError("key must be an x25519 key")
    return opensslport.x25519_shared_ssl(key.raw, pubkey.raw)


from openssl.bcrypt_pbkdf import bcrypt_pbkdf
from openssl.ec_dh import ec_dh
from openssl.fingerprint import fingerprint
from openssl.read_pubkey import read_pubkey
from openssl.rsa_sign import rsa_sign
from openssl.write_pem import write_pem
from openssl.read_p12 import read_p12
