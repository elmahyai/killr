"""write_pem from R/openssl write.R."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pemwrite

from openssl import _Key, _Pubkey


class _Cert:
    __slots__ = ("raw",)

    def __init__(self, raw: bytes | bytearray):
        self.raw = bytes(raw)


class _Pkcs7:
    __slots__ = ("raw",)

    def __init__(self, raw: bytes | bytearray):
        self.raw = bytes(raw)


def _resolve_password(password: str | Callable | None) -> str | None:
    if password is None:
        return None
    if callable(password):
        from openssl import askpass

        return askpass("Enter new passphrase (or hit ENTER for no password): ")
    if not isinstance(password, str):
        raise TypeError("password must be a string, callback, or None")
    return password


def _private_der(x: Any) -> bytes:
    if isinstance(x, _Key):
        return pemwrite.private_der_from_raw(x.kind, x.raw)
    if isinstance(x, (bytes, bytearray)):
        return bytes(x)
    raise TypeError("x must be a private key object or raw DER")


def _pem_export_key(x: Any, password: str | Callable | None) -> str:
    pass_str = _resolve_password(password)
    if pass_str is not None and not isinstance(pass_str, str):
        raise TypeError("password callback must return a character string or NULL")
    der = _private_der(x)
    pem_bytes = pemwrite.write_key(der, pass_str)
    return pem_bytes.decode("ascii")


def _pem_export_pubkey(x: _Pubkey) -> str:
    der = pemwrite.public_der_from_raw(x.kind, x.raw)
    return pemwrite.write_pubkey(der).decode("ascii")


def _pem_export_cert(x: _Cert) -> str:
    return pemwrite.write_cert(x.raw).decode("ascii")


def _pem_export_pkcs7(x: _Pkcs7) -> str:
    return pemwrite.write_pkcs7(x.raw).decode("ascii")


def _pem_export(x: Any, password: str | Callable | None = None) -> str:
    if isinstance(x, _Key):
        return _pem_export_key(x, password)
    if isinstance(x, _Pubkey):
        return _pem_export_pubkey(x)
    if isinstance(x, _Cert):
        return _pem_export_cert(x)
    if isinstance(x, _Pkcs7):
        return _pem_export_pkcs7(x)
    if isinstance(x, (bytes, bytearray)):
        return _pem_export_key(x, password)
    raise TypeError("x must be a key, pubkey, certificate, or pkcs7 object")


def write_pem(x, path=None, password=None):
    """Export a key or certificate to PEM text, optionally writing a file."""
    text = _pem_export(x, password)
    if path is None:
        return text
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)
        if not text.endswith("\n"):
            handle.write("\n")
    return path
