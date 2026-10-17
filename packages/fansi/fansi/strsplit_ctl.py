"""Control-aware strsplit, from fansi R/strsplit.R.

Controls are removed, split positions are found on that text, and each piece
is cut with substr_ctl so active SGR and URLs are kept.
"""

from __future__ import annotations

import re

from fansi._args import FansiError, option, prepare
from fansi._read import coerce_texts, resolve_warn
from fansi.simple import dflt_term_cap
from fansi.strip_ctl import strip_ctl
from fansi.substr_ctl import substr_ctl

_MISSING = object()


def _scalar_logical(value, name):
    if isinstance(value, (list, tuple)):
        if len(value) != 1:
            raise FansiError(f"Argument `{name}` must be TRUE or FALSE.")
        value = value[0]
    if value is None or (isinstance(value, float) and value != value):
        raise FansiError(f"Argument `{name}` must be TRUE or FALSE.")
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value != 0
    if isinstance(value, str):
        if value in ("TRUE", "T"):
            return True
        if value in ("FALSE", "F"):
            return False
    raise FansiError(f"Argument `{name}` must be TRUE or FALSE.")


def _coerce_split(split):
    """Length zero becomes \"\". A missing string, including None, is an error."""
    if isinstance(split, (bytes, bytearray)):
        try:
            split.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise FansiError('Argument `split` may not be "bytes" encoded.') from exc
    values = coerce_texts(split)
    if not values:
        return [""]
    if any(item is None for item in values):
        raise FansiError("Argument `split` may not contain NAs.")
    for item in values:
        try:
            item.encode("utf-8")
        except UnicodeEncodeError as exc:
            raise FansiError('Argument `split` may not be "bytes" encoded.') from exc
    return values


def _find_fixed(hay, needle):
    if needle == "" or needle == b"":
        return None
    starts = []
    lengths = []
    pos = 0
    step = len(needle)
    while True:
        found = hay.find(needle, pos)
        if found < 0:
            break
        starts.append(found + 1)
        lengths.append(step)
        pos = found + step
    if not starts:
        return None
    return starts, lengths


def _find_regex(hay, needle):
    try:
        pattern = re.compile(needle)
    except re.error as exc:
        raise FansiError(f"invalid regular expression '{needle}': {exc}") from exc
    starts = []
    lengths = []
    for match in pattern.finditer(hay):
        starts.append(match.start() + 1)
        lengths.append(match.end() - match.start())
    if not starts:
        return None
    return starts, lengths


def _gregexpr(pattern, text, fixed, use_bytes):
    if use_bytes:
        hay = text.encode("utf-8", "surrogateescape")
        needle = pattern.encode("utf-8", "surrogateescape")
    else:
        hay = text
        needle = pattern
    if fixed:
        return _find_fixed(hay, needle)
    return _find_regex(hay, needle)


def _zero_width(count):
    if count <= 1:
        return None
    starts = list(range(2, count + 1))
    return starts, [0] * (count - 1)


def _pieces(text, chars, found, warn, term_cap, ctl, normalize, carry, terminate):
    starts_m, lengths = found
    starts = [1] + [pos + length for pos, length in zip(starts_m, lengths)]
    ends = [pos - 1 for pos in starts_m] + [chars]
    starts = [1 if pos < 1 else pos for pos in starts]
    kept_s = []
    kept_e = []
    for pos, end in zip(starts, ends):
        if pos > chars:
            continue
        kept_s.append(pos)
        kept_e.append(end)
    if not kept_s:
        return []
    return substr_ctl(
        [text] * len(kept_s),
        kept_s,
        kept_e,
        warn=warn,
        term_cap=term_cap,
        ctl=ctl,
        normalize=normalize,
        carry=carry,
        terminate=terminate,
    )


def strsplit_ctl(
    x,
    split,
    fixed=False,
    perl=False,
    useBytes=False,
    warn=_MISSING,
    term_cap=_MISSING,
    ctl="all",
    normalize=_MISSING,
    carry=_MISSING,
    terminate=_MISSING,
):
    """Split on the text that remains after controls are removed."""
    warn = resolve_warn(warn, _MISSING)
    if term_cap is _MISSING:
        term_cap = option("fansi.term.cap", dflt_term_cap())
    if normalize is _MISSING:
        normalize = option("fansi.normalize", False)
    if carry is _MISSING:
        carry = option("fansi.carry", False)
    if terminate is _MISSING:
        terminate = option("fansi.terminate", True)
    texts = coerce_texts(x)
    prepare(
        x=texts,
        warn=warn,
        term_cap=term_cap,
        ctl=ctl,
        normalize=normalize,
        carry=carry,
        terminate=terminate,
        round_="start",
        coerce_x=False,
    )
    patterns = _coerce_split(split)
    fixed = _scalar_logical(fixed, "fixed")
    perl = _scalar_logical(perl, "perl")
    use_bytes = _scalar_logical(useBytes, "useBytes")
    del perl
    stripped = strip_ctl(texts, warn=False, ctl=ctl)
    chars = [None if item is None else len(item) for item in stripped]
    split_for = []
    for index in range(len(texts)):
        if texts[index] is None:
            split_for.append(None)
        else:
            split_for.append(index % len(patterns))
    found = [None] * len(texts)
    for pattern_index, pattern in enumerate(patterns):
        targets = [
            index
            for index, which in enumerate(split_for)
            if which == pattern_index and chars[index]
        ]
        if not pattern:
            for index in targets:
                found[index] = _zero_width(chars[index])
            continue
        for index in targets:
            found[index] = _gregexpr(pattern, stripped[index], fixed, use_bytes)
    out = []
    for index, text in enumerate(texts):
        match = found[index]
        if match is not None and any(pos > 0 for pos in match[0]):
            out.append(
                _pieces(
                    text,
                    chars[index],
                    match,
                    warn,
                    term_cap,
                    ctl,
                    normalize,
                    carry,
                    terminate,
                )
            )
        else:
            out.append([text])
    for index, count in enumerate(chars):
        if count == 0:
            out[index] = []
    for index, text in enumerate(texts):
        if text is None:
            out[index] = [None]
    return out


def strsplit_sgr(
    x,
    split,
    fixed=False,
    perl=False,
    useBytes=False,
    warn=_MISSING,
    term_cap=_MISSING,
    normalize=_MISSING,
    carry=_MISSING,
    terminate=_MISSING,
):
    """strsplit_ctl that treats only SGR sequences as controls."""
    return strsplit_ctl(
        x,
        split,
        fixed=fixed,
        perl=perl,
        useBytes=useBytes,
        warn=warn,
        term_cap=term_cap,
        ctl="sgr",
        normalize=normalize,
        carry=carry,
        terminate=terminate,
    )
