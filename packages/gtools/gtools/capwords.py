"""Capitalize words for titles (gtools 3.9.5 ``capwords``)."""

from __future__ import annotations

import re

_AP_NOCAP = (
    "a",
    "an",
    "and",
    "at",
    "but",
    "by",
    "for",
    "in",
    "nor",
    "of",
    "on",
    "or",
    "so",
    "the",
    "to",
    "up",
    "yet",
)

_MIXED_CASE = re.compile(r"[a-z][A-Z]")


def _cap(word: str, strict: bool) -> str:
    if not word:
        return word
    rest = word[1:]
    if strict:
        rest = rest.lower()
    return word[0].upper() + rest


def _is_mixed_case(word: str) -> bool:
    return _MIXED_CASE.search(word) is not None


def capwords(
    s: str,
    strict: bool = False,
    AP: bool = True,
    onlyfirst: bool = False,
    preserveMixed: bool = False,
    sep: str = " ",
) -> str:
    """Capitalize words in a character string for use in titles."""
    words = re.split(sep, s)
    mixed_case = [_is_mixed_case(word) for word in words]

    if not onlyfirst:
        new_words = [_cap(word, strict) for word in words]
        if preserveMixed:
            new_words = [
                words[index] if mixed_case[index] else new_words[index]
                for index in range(len(words))
            ]
        words = new_words

        if AP:
            for ap_word in _AP_NOCAP:
                pattern = re.compile(rf"^{re.escape(ap_word)}$", re.IGNORECASE)
                words = [ap_word if pattern.fullmatch(word) else word for word in words]

    if words and not mixed_case[0]:
        words[0] = _cap(words[0], strict)

    return sep.join(words)
