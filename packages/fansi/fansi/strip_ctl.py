"""Strip control sequences, from fansi src/strip.c and R/sgr.R."""

from __future__ import annotations

import sys

from fansi._args import prepare
from fansi._const import CTL_ALL
from fansi._read import coerce_texts, find_ctl, resolve_warn
from fansi._state import state_init_ctl, state_reinit

_MISSING = object()


def strip_ctl(x, ctl="all", warn=_MISSING, strip=_MISSING):
    """Remove selected control sequences. An empty `ctl` removes nothing."""
    if strip is not _MISSING:
        sys.stderr.write("Parameter `strip` has been deprecated; use `ctl` instead.\n")
        ctl = strip
    warn = resolve_warn(warn, _MISSING)
    texts = coerce_texts(x)
    checked = prepare(x=texts, ctl=ctl, warn=warn, coerce_x=False)
    if not checked["ctl_int"]:
        return texts
    warn_int = checked["warn_int"]
    ctl_int = checked["ctl_int"]
    out = list(texts)
    state = None
    for index, text in enumerate(texts):
        if state is None:
            state = state_init_ctl(texts, warn_int, ctl_int, index)
        else:
            state_reinit(state, texts, index)
        if text is None:
            continue
        data = state.string
        stripped = bytearray()
        found = False
        origin = 0
        previous = 0
        while state.at(state.pos_x):
            pos = find_ctl(state, index, "x")
            if found or (state.status & CTL_ALL):
                found = True
                stripped += data[origin:origin + (pos - previous)]
                origin = state.pos_x
                previous = state.pos_x
        if found:
            out[index] = bytes(stripped).decode("utf-8", "surrogateescape")
    return out


def strip_sgr(x, warn=_MISSING):
    """Remove SGR and OSC hyperlink sequences."""
    if warn is _MISSING:
        return strip_ctl(x, ctl=["sgr", "url"])
    return strip_ctl(x, ctl=["sgr", "url"], warn=warn)
