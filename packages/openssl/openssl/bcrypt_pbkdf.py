"""bcrypt_pbkdf from R/openssl bcrypt.R."""

from __future__ import annotations

import bcryptpbkdf as _bcryptpbkdf


def _bytes(value, name: str) -> bytes:
    if isinstance(value, str):
        return value.encode("utf-8")
    if isinstance(value, (bytes, bytearray)):
        return bytes(value)
    raise TypeError(f"{name} must be a string or raw vector")


def bcrypt_pbkdf(password, salt, rounds=16, size=32) -> bytes:
    """Password-based key derivation with bcrypt (OpenSSH new-format keys)."""
    pass_bytes = _bytes(password, "password")
    salt_bytes = _bytes(salt, "salt")
    rounds_i = int(rounds)
    size_i = int(size)
    if rounds_i != rounds or size_i != size:
        raise TypeError("rounds and size must be integers")
    return _bcryptpbkdf.inner(pass_bytes, salt_bytes, rounds_i, size_i)
