"""PKCS#12 bundle reader from R/openssl pkcs12.R."""

from __future__ import annotations

import os
from dataclasses import dataclass
import pkcs12parse

from openssl import askpass


@dataclass
class _Cert:
    raw: bytes


@dataclass
class _Pubkey:
    raw: bytes


@dataclass
class _Key:
    raw: bytes
    pubkey: _Pubkey


def _bytes(value, name: str = "file") -> bytes:
    if isinstance(value, str):
        return value.encode("utf-8")
    if isinstance(value, (bytes, bytearray)):
        return bytes(value)
    raise TypeError(f"{name} must be a string or raw vector")


def _read_input(file) -> bytes:
    if isinstance(file, (bytes, bytearray)):
        return bytes(file)
    if isinstance(file, str):
        if "\n" not in file:
            path = os.path.normpath(os.path.expanduser(file))
            if os.path.isfile(path):
                with open(path, "rb") as handle:
                    return handle.read()
        return _bytes(file)
    if hasattr(file, "read"):
        if getattr(file, "mode", "").startswith("t"):
            return "\n".join(file.read().splitlines()).encode("utf-8")
        chunks = []
        while True:
            chunk = file.read(1_000_000)
            if not chunk:
                break
            chunks.append(chunk)
        return b"".join(chunks)
    raise TypeError("file must be connection, raw vector or file path")


def _resolve_password(password) -> str | None:
    if password is None:
        return None
    if isinstance(password, str):
        return password
    if callable(password):
        value = password("Please enter private key passphrase: ")
        if not isinstance(value, str):
            raise RuntimeError("Password callback did not return a string value")
        return value
    raise RuntimeError("Callback must be string or function")


def _read_cert_der(buf: bytes) -> _Cert:
    return _Cert(pkcs12parse.parse_der_cert(buf))


def _read_key_der(buf: bytes) -> _Key:
    raw = pkcs12parse.parse_der_key(buf)
    pub = pkcs12parse.derive_pubkey(raw)
    return _Key(raw=raw, pubkey=_Pubkey(pub))


def parse_pkcs12(buf: bytes, password=askpass):
    """Parse PKCS#12 bytes; returns (cert, key, ca, name) like R ``parse_pkcs12``."""
    if isinstance(password, str):
        pass_arg = password
    elif password is None:
        pass_arg = None
    elif callable(password):
        pass_arg = _resolve_password(password)
    else:
        raise RuntimeError("Callback must be string or function")
    cert_raw, key_raw, ca_raw, name = pkcs12parse.parse_pkcs12(buf, pass_arg)
    return cert_raw, key_raw, list(ca_raw), name


def read_p12(file, password=askpass):
    """Read a PKCS#12 file or raw vector into cert, key, ca chain, and friendly name."""
    buf = _read_input(file)
    cert_raw, key_raw, ca_raw, name = parse_pkcs12(buf, password)
    out = {"name": name, "cert": None, "key": None, "ca": None}
    if cert_raw is not None and len(cert_raw):
        out["cert"] = _read_cert_der(cert_raw)
    if key_raw is not None and len(key_raw):
        out["key"] = _read_key_der(key_raw)
    if ca_raw:
        out["ca"] = [_read_cert_der(item) for item in ca_raw if item]
    return out
