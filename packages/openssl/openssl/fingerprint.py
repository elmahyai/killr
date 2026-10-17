"""OpenSSH fingerprint from R/openssl openssh.R."""

from __future__ import annotations

from typing import Callable

import opensshfp

from openssl import sha256 as _default_sha256
from openssl import _Key, _Pubkey


def _fpdata_bytes(pubkey: _Pubkey) -> bytes:
    if pubkey.kind == "ed25519":
        return opensshfp.fpdata_ed25519(pubkey.raw)
    if pubkey.kind == "x25519":
        return opensshfp.fpdata_x25519(pubkey.raw)
    raise TypeError(f"unsupported pubkey kind: {pubkey.kind}")


def _resolve_pubkey(key):
    if isinstance(key, _Key):
        return key.pubkey
    if isinstance(key, _Pubkey):
        return key
    if isinstance(key, (bytes, bytearray)):
        return bytes(key)
    raise TypeError("key must be an openssl key, pubkey, or raw DER")


def fingerprint(key, hashfun: Callable | None = None):
    """OpenSSH fingerprint of a public or private key (default SHA-256 hex digest)."""
    if hashfun is None:
        hashfun = _default_sha256
    target = _resolve_pubkey(key)
    if isinstance(target, _Pubkey):
        data = _fpdata_bytes(target)
    else:
        data = opensshfp.fpdata_key(target)
    return hashfun(data)
