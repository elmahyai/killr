"""Escape HTML special characters, from FANSI_esc_html in src/tohtml.c."""

from __future__ import annotations

from fansi._args import FansiError

_REPLACEMENTS = (
    ("&", "&amp;", 1),
    ('"', "&quot;", 2),
    ("'", "&#039;", 4),
    ("<", "&lt;", 8),
    (">", "&gt;", 16),
)


def _texts(value, name):
    if isinstance(value, str):
        return [value]
    if value is None:
        return [None]
    if isinstance(value, (list, tuple)):
        out = []
        for item in value:
            if item is None or isinstance(item, str):
                out.append(item)
            else:
                kind = "NULL" if item is None else type(item).__name__
                raise FansiError(f"Argument `{name}` must be character, is {kind}.")
        return out
    kind = "NULL" if value is None else type(value).__name__
    raise FansiError(f"Argument `{name}` must be character, is {kind}.")


def _what_mask(what):
    if isinstance(what, (list, tuple)):
        if len(what) != 1:
            raise FansiError("Argument `what` must be scalar character and not NA.")
        what = what[0]
    if what is None:
        raise FansiError("Argument `what` must be scalar character and not NA.")
    if not isinstance(what, str):
        kind = type(what).__name__
        raise FansiError(f"Argument `what` must be character, is {kind}.")
    mask = 0
    for char in what:
        found = False
        for source, _replacement, bit in _REPLACEMENTS:
            if char == source:
                mask |= bit
                found = True
                break
        if not found:
            raise FansiError(
                'Argument `what` may only contain ASCII characters '
                '"&", "<", ">", "\'", or "\\"."'
            )
    return what, mask


def html_esc(x, what="<>&'\""):
    """Replace the characters in `what` with HTML entities. Default is `<>&'\"`."""
    texts = _texts(x, "x")
    spec, mask = _what_mask(what)
    if not spec or not texts or not mask:
        return list(texts)
    out = []
    for text in texts:
        if text is None:
            out.append(None)
            continue
        pieces = []
        for char in text:
            replaced = False
            for source, replacement, bit in _REPLACEMENTS:
                if char == source and mask & bit:
                    pieces.append(replacement)
                    replaced = True
                    break
            if not replaced:
                pieces.append(char)
        out.append("".join(pieces))
    return out
