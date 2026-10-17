"""Phonetic encoding from stringdist ``phonetic``."""

from __future__ import annotations

import warnings

from stringdist.stringdist import (
    _SOUNDEX_WARNING,
    _codes,
    _soundex,
    _soundex_code,
)

__all__ = ["phonetic"]

_PHONETIC_METHODS = ("soundex",)


def _match_phonetic_method(method):
    if method is None:
        return _PHONETIC_METHODS[0]
    if isinstance(method, (list, tuple)):
        if list(method) == list(_PHONETIC_METHODS):
            return _PHONETIC_METHODS[0]
        if len(method) != 1:
            raise ValueError("'method' must be of length 1")
        method = method[0]
    if not isinstance(method, str):
        raise ValueError("'method' must be NULL or a character vector")
    if method in _PHONETIC_METHODS:
        return method
    hits = [choice for choice in _PHONETIC_METHODS if choice.startswith(method)]
    if len(hits) == 1:
        return hits[0]
    shown = ", ".join(repr(choice) for choice in _PHONETIC_METHODS)
    if not hits:
        raise ValueError(f"'{method}' should be one of {shown}")
    raise ValueError(f"'{method}' matches more than one of {shown}")


def _as_character(value):
    if isinstance(value, str):
        return [value]
    if value is None:
        return [None]
    try:
        items = list(value)
    except TypeError:
        return [str(value)]
    out = []
    for item in items:
        if item is None:
            out.append(None)
        elif isinstance(item, str):
            out.append(item)
        else:
            out.append(str(item))
    return out


def _soundex_failures(text, use_bytes):
    total = 0
    for code in _codes(text, use_bytes):
        if _soundex_code(code) == 63:
            total += 1
    return total


def _encode_soundex(text, use_bytes):
    codes = _soundex(_codes(text, use_bytes))
    return "".join(chr(item) for item in codes)


def phonetic(x, method=None, useBytes=False):
    """Return phonetic codes for each string in ``x`` (soundex only)."""
    strings = _as_character(x)
    method = _match_phonetic_method(method)
    if not isinstance(useBytes, bool):
        raise ValueError("is.logical(useBytes) is not TRUE")
    if method != "soundex":
        raise ValueError(f"unsupported phonetic method {method!r}")
    nfail = 0
    out = []
    for text in strings:
        if text is None:
            out.append(None)
            continue
        nfail += _soundex_failures(text, useBytes)
        out.append(_encode_soundex(text, useBytes))
    if nfail > 0:
        warnings.warn(_SOUNDEX_WARNING, stacklevel=2)
    return out
