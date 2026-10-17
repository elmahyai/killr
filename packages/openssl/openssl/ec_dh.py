"""EC Diffie-Hellman key agreement from R/openssl diffie.R."""

from __future__ import annotations

import ecdhdh
import opensslport

from openssl import _Key, _Pubkey, askpass

_ALLOWED = frozenset({"ecdsa", "x25519"})


def _bytes(value, name: str) -> bytes:
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
            import os

            path = os.path.expanduser(file)
            path = os.path.normpath(path)
            with open(path, "rb") as handle:
                return handle.read()
        return _bytes(file, "file")
    raise TypeError("file must be connection, raw vector or file path")


def _resolve_private(key, password):
    if isinstance(key, _Key):
        if key.kind not in _ALLOWED:
            raise TypeError("key must be an ecdsa or x25519 key")
        return key
    raw = _read_input(key)
    return raw


def _resolve_peer(peerkey):
    if isinstance(peerkey, _Key):
        return peerkey.pubkey
    if isinstance(peerkey, _Pubkey):
        if peerkey.kind not in _ALLOWED:
            raise TypeError("peerkey must be an ecdsa or x25519 public key")
        return peerkey
    return _read_input(peerkey)


def ec_dh(key=..., peerkey=..., password=askpass):
    """Derive a shared secret via ECDH (ECDSA or X25519 keys)."""
    if key is ...:
        raise TypeError("missing required argument: key")
    if peerkey is ...:
        raise TypeError("missing required argument: peerkey")
    _ = password  # read_key accepts protected PEM; not used for DER or _Key inputs yet
    private = _resolve_private(key, password)
    peer = _resolve_peer(peerkey)

    if isinstance(private, _Key):
        if not isinstance(peer, _Pubkey):
            raise TypeError("peerkey must be a public key for curve25519 keys")
        if private.kind != peer.kind:
            raise TypeError("private and public keys must use the same algorithm")
        if private.kind == "x25519":
            return opensslport.x25519_shared_ssl(private.raw, peer.raw)
        raise TypeError("key must be an ecdsa or x25519 key")

    if isinstance(peer, _Pubkey):
        peer_der = peer.raw
    else:
        peer_der = peer
    return ecdhdh.derive(private, peer_der)
