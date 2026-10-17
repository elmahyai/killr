"""Parse public keys from PEM, DER, SSH, and OpenSSH formats (R/openssl read.R)."""

from __future__ import annotations

import os
import re

import base64

import readpubkey

from openssl import _Key, _Pubkey, askpass, base64_decode
import opensslport


_SSH_PUBKEY_RE = re.compile(rb"^(ssh|ecdsa)-[a-z0-9-]+\s+", re.IGNORECASE)
_OPENSSH_PUBKEY_RE = re.compile(
    rb"^(ssh-dss|ssh-rsa|ssh-ed25519|ecdsa-sha2-nistp\d+)\s+",
    re.IGNORECASE,
)


def _is_pubkey_str(value) -> bool:
    if isinstance(value, str):
        data = value.encode("utf-8")
    elif isinstance(value, (bytes, bytearray)):
        data = bytes(value)
    else:
        return False
    return _SSH_PUBKEY_RE.search(data) is not None


def _pem_blocks(buf: bytes) -> list[tuple[str, bytes]]:
    text = buf.decode("latin-1")
    pattern = re.compile(
        r"-----BEGIN ([^-]+)-----(.*?)-----END \1-----",
        flags=re.DOTALL,
    )
    blocks: list[tuple[str, bytes]] = []
    for match in pattern.finditer(text):
        name = match.group(1).strip()
        body = match.group(2)
        lines = []
        for line in body.splitlines():
            line = line.strip()
            if not line or line.startswith("Proc-Type") or line.startswith("DEK-Info"):
                continue
            lines.append(line)
        data = base64.b64decode("".join(lines))
        blocks.append((name, data))
    return blocks


def _pem_names(buf: bytes) -> list[str]:
    return [name for name, _ in _pem_blocks(buf)]


def _first_pem_data(buf: bytes) -> bytes:
    blocks = _pem_blocks(buf)
    if not blocks:
        raise RuntimeError("Failed to parse pubkey PEM file")
    return blocks[0][1]


def _read_input(file) -> bytes:
    if isinstance(file, (bytes, bytearray)):
        return bytes(file)
    if isinstance(file, str):
        if len(file) == 1 and "\n" not in file and not _is_pubkey_str(file):
            if re.match(r"^https?://", file):
                raise NotImplementedError("URL connections are not supported")
            path = os.path.normpath(os.path.expanduser(file))
            with open(path, "rb") as handle:
                return handle.read()
        return file.encode("utf-8") if isinstance(file, str) else bytes(file)
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


def _pubkey_from_der(der: bytes) -> _Pubkey:
    kind = readpubkey.pubkey_type_py(der)
    return _Pubkey(kind, der)


def _derive_from_key(key: _Key) -> _Pubkey:
    if key.kind == "ed25519":
        raw = opensslport.ed25519_public_ssl(key.raw)
        der = readpubkey.ed25519_pubkey_der_py(raw)
        return _Pubkey("ed25519", der)
    if key.kind == "x25519":
        raw = opensslport.x25519_public_ssl(key.raw)
        der = readpubkey.x25519_pubkey_der_py(raw)
        return _Pubkey("x25519", der)
    der = readpubkey.derive_pubkey_py(key.raw)
    return _pubkey_from_der(der)


def _parse_ssh_pem(buf: bytes) -> bytes:
    text = buf.decode("utf-8", errors="replace")
    match = re.search(
        r"([-]+ BEGIN SSH2 PUBLIC KEY [-]+)(.*?)([-]+ END SSH2 PUBLIC KEY [-]+)",
        text,
        flags=re.DOTALL,
    )
    if not match:
        raise RuntimeError("Failed to find SSH2 public key header/footer")
    body = match.group(2)
    body = re.sub(r"Comment.*?\n", "", body, flags=re.DOTALL)
    b64 = "".join(line.strip() for line in body.splitlines() if line.strip())
    return readpubkey.ssh_build_pubkey_py(base64_decode(b64))


def _parse_openssh(buf: bytes) -> bytes:
    text = buf.decode("utf-8", errors="replace").strip()
    if _OPENSSH_PUBKEY_RE.match(buf.strip()) is None and _OPENSSH_PUBKEY_RE.match(
        text.encode("utf-8")
    ) is None:
        raise RuntimeError(f"Unsupported ssh key id format: {text[:15]}")
    rest = re.sub(r"^\S+\s+", "", text, count=1)
    token = re.match(r"^\S*", rest).group(0)
    return readpubkey.ssh_build_pubkey_py(base64_decode(token))


def _parse_pem_branch(buf: bytes, password) -> bytes:
    names = _pem_names(buf)
    if not names or not any(names):
        raise RuntimeError("Failed to parse pubkey PEM file")
    joined = " ".join(names)
    if any("RSA PUBLIC KEY" in name for name in names):
        return readpubkey.parse_legacy_pubkey_py(buf)
    if any("PUBLIC" in name for name in names):
        return readpubkey.parse_pem_pubkey_py(buf)
    if any(re.search(r"PRIVATE|PARAMETERS", name) for name in names):
        priv = readpubkey.parse_pem_key_py(buf, _password_str(password))
        return readpubkey.derive_pubkey_py(priv)
    if any("CERTIFICATE" in name for name in names):
        cert = readpubkey.parse_pem_cert_py(buf)
        return readpubkey.cert_pubkey_py(cert)
    raise RuntimeError(f"Invalid PEM type: {joined}")


def _password_str(password) -> str | None:
    if password is None:
        return None
    if callable(password):
        value = password("Please enter your private key passphrase")
    else:
        value = password
    if not isinstance(value, str):
        raise RuntimeError("Password is not a string or function")
    return value


def read_pubkey(file, der=None, password=askpass):
    """Read a public key from a path, connection, PEM/SSH text, or raw DER."""
    if isinstance(file, _Key):
        return _derive_from_key(file)
    if der is None:
        der = isinstance(file, (bytes, bytearray)) and not isinstance(file, memoryview)
    if _is_pubkey_str(file):
        buf = (
            file.encode("utf-8")
            if isinstance(file, str)
            else bytes(file)
        )
    else:
        buf = _read_input(file)
    if der is True:
        key = readpubkey.parse_der_pubkey_py(buf)
    elif b"BEGIN SSH2 PUBLIC KEY" in buf:
        key = _parse_ssh_pem(buf)
    elif b"BEGIN OPENSSH PRIVATE KEY" in buf:
        key = readpubkey.openssh_key_pubkey_py(_first_pem_data(buf))
    elif _is_pubkey_str(buf):
        key = _parse_openssh(buf)
    else:
        key = _parse_pem_branch(buf, password)
    return _pubkey_from_der(key)
