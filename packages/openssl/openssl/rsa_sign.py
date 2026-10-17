"""RSA legacy PKCS#1 v1.5 signing from R/openssl rsa.R."""

from __future__ import annotations

import ctypes
import os
from ctypes import (
    CFUNCTYPE,
    c_char_p,
    c_int,
    c_long,
    c_uint,
    c_void_p,
    POINTER,
    byref,
    create_string_buffer,
)

_LIB: ctypes.CDLL | None = None

_HASH_NIDS = {
    16: b"MD5",
    20: b"SHA1",
    32: b"SHA256",
}


def _lib() -> ctypes.CDLL:
    global _LIB
    if _LIB is None:
        _LIB = ctypes.CDLL("libcrypto.so.3")
    return _LIB


def _bytes(value, name: str = "hash") -> bytes:
    if isinstance(value, str):
        return value.encode("utf-8")
    if isinstance(value, (bytes, bytearray)):
        return bytes(value)
    raise TypeError(f"{name} must be a string or raw vector")


def _read_input(file) -> bytes:
    if isinstance(file, (bytes, bytearray)):
        return bytes(file)
    if isinstance(file, str):
        if len(file) == 1 and "\n" not in file:
            path = os.path.normpath(os.path.expanduser(file))
            with open(path, "rb") as handle:
                return handle.read()
        return _bytes(file, "file")
    raise TypeError("file must be connection, raw vector or file path")


def _password_cb(_buf, size, _rwflag, password_obj):
    if password_obj is None:
        return 0
    if callable(password_obj):
        text = password_obj()
    else:
        text = password_obj
    if text is None:
        return 0
    if isinstance(text, bytes):
        data = text
    else:
        data = str(text).encode("utf-8")
    if len(data) >= size:
        return 0
    ctypes.memmove(_buf, data, len(data))
    return len(data)


def _parse_der_key(buf: bytes) -> bytes:
    lib = _lib()
    bio = lib.BIO_new_mem_buf(buf, len(buf))
    if not bio:
        raise RuntimeError("Failed to parse private key")
    pkey = lib.d2i_PrivateKey_bio(bio, None)
    lib.BIO_free(bio)
    if not pkey:
        raise RuntimeError("Failed to parse private key")
    out_ptr = c_char_p()
    length = lib.i2d_PrivateKey(pkey, byref(out_ptr))
    lib.EVP_PKEY_free(pkey)
    if length <= 0 or not out_ptr.value:
        raise RuntimeError("Failed to parse private key")
    try:
        return ctypes.string_at(out_ptr, length)
    finally:
        lib.CRYPTO_free(out_ptr)


def _parse_pem_key(buf: bytes, password) -> bytes:
    lib = _lib()
    bio = lib.BIO_new_mem_buf(buf, len(buf))
    if not bio:
        raise RuntimeError("Failed to parse private key PEM file")

    @CFUNCTYPE(c_int, c_char_p, c_int, c_int, c_void_p)
    def cb(buf_ptr, size, _rwflag, _userdata):
        return _password_cb(buf_ptr, size, _rwflag, password)

    pkey = lib.PEM_read_bio_PrivateKey(bio, None, cb, None)
    lib.BIO_free(bio)
    if not pkey:
        raise RuntimeError("Failed to parse private key PEM file")
    out_ptr = c_char_p()
    length = lib.i2d_PrivateKey(pkey, byref(out_ptr))
    lib.EVP_PKEY_free(pkey)
    if length <= 0 or not out_ptr.value:
        raise RuntimeError("Failed to parse private key PEM file")
    try:
        return ctypes.string_at(out_ptr, length)
    finally:
        lib.CRYPTO_free(out_ptr)


def _parse_legacy_pem_key(buf: bytes, password) -> bytes:
    try:
        lib = _lib()
        bio = lib.BIO_new_mem_buf(buf, len(buf))

        @CFUNCTYPE(c_int, c_char_p, c_int, c_int, c_void_p)
        def cb(buf_ptr, size, _rwflag, _userdata):
            return _password_cb(buf_ptr, size, _rwflag, password)

        rsa = lib.PEM_read_bio_RSAPrivateKey(bio, None, cb, None)
        lib.BIO_free(bio)
        if not rsa:
            raise RuntimeError("legacy")
        out_ptr = c_char_p()
        length = lib.i2d_RSAPrivateKey(rsa, byref(out_ptr))
        lib.RSA_free(rsa)
        if length <= 0 or not out_ptr.value:
            raise RuntimeError("legacy")
        try:
            return ctypes.string_at(out_ptr, length)
        finally:
            lib.CRYPTO_free(out_ptr)
    except RuntimeError:
        return _parse_pem_key(buf, password)


def _is_rsa_private(key_der: bytes) -> bool:
    lib = _lib()
    d2i = lib.d2i_RSAPrivateKey
    d2i.argtypes = [c_void_p, POINTER(c_char_p), c_long]
    d2i.restype = c_void_p
    ptr = c_char_p(key_der)
    rsa = d2i(None, byref(ptr), len(key_der))
    if rsa:
        lib.RSA_free(rsa)
        return True
    return False


def _openssl_askpass(prompt="Please enter your password: "):
    import askpass as ask

    return ask.askpass(prompt)


def _is_rsa_key_obj(file) -> bool:
    return getattr(file, "kind", None) == "rsa" and hasattr(file, "raw")


def _read_key(file, password=_openssl_askpass, der=None) -> bytes:
    if _is_rsa_key_obj(file):
        return bytes(file.raw)
    buf = _read_input(file)
    if der is None:
        der = isinstance(file, (bytes, bytearray))
    if der:
        key = _parse_der_key(buf)
    elif b"BEGIN OPENSSH PRIVATE KEY" in buf:
        raise RuntimeError("OpenSSH private keys are not supported yet")
    elif b"BEGIN" in buf and b"PUBLIC" in buf:
        raise RuntimeError("Input is a public key. Use read_pubkey() to read")
    elif b"BEGIN" in buf:
        if b"RSA PRIVATE" in buf:
            key = _parse_legacy_pem_key(buf, password)
        else:
            key = _parse_pem_key(buf, password)
    else:
        raise RuntimeError("Failed to parse private key PEM file")
    if not _is_rsa_private(key):
        raise TypeError("key must be an rsa key")
    return key


def _my_key() -> bytes:
    path = os.environ.get("USER_KEY") or os.path.expanduser("~/.ssh/id_rsa")
    if not os.path.isfile(path):
        raise RuntimeError("No suitable user key found.")
    return _read_key(path, password=_openssl_askpass, der=False)


def _hash_nid(length: int) -> int:
    name = _HASH_NIDS.get(length)
    if name is None:
        raise ValueError("RSA hash must be length 16, 20, or 32")
    lib = _lib()
    lib.OBJ_sn2nid.argtypes = [c_char_p]
    lib.OBJ_sn2nid.restype = c_int
    nid = lib.OBJ_sn2nid(name)
    if nid <= 0:
        raise RuntimeError(f"unknown digest {name!r}")
    return nid


def _rsa_sign_raw(hash_bytes: bytes, key_der: bytes) -> bytes:
    lib = _lib()
    d2i = lib.d2i_RSAPrivateKey
    d2i.argtypes = [c_void_p, POINTER(c_char_p), c_long]
    d2i.restype = c_void_p
    ptr = c_char_p(key_der)
    rsa = d2i(None, byref(ptr), len(key_der))
    if not rsa:
        raise RuntimeError("Failed to load RSA private key")
    try:
        size = lib.RSA_size(rsa)
        sig = create_string_buffer(size)
        siglen = c_uint(0)
        nid = _hash_nid(len(hash_bytes))
        rc = lib.RSA_sign(
            nid,
            hash_bytes,
            len(hash_bytes),
            sig,
            byref(siglen),
            rsa,
        )
        if rc != 1:
            raise RuntimeError("RSA_sign failed")
        return sig.raw[: siglen.value]
    finally:
        lib.RSA_free(rsa)


def rsa_sign(hash, key=..., password=_openssl_askpass):
    """Legacy RSA signature over a raw MD5, SHA-1, or SHA-256 digest."""
    hash_bytes = _bytes(hash)
    if key is ...:
        sk = _my_key()
    else:
        sk = _read_key(key, password=password)
    return _rsa_sign_raw(hash_bytes, sk)
