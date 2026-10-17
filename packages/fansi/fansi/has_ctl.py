"""Presence of control sequences, from fansi src/has.c and R/sgr.R."""

from __future__ import annotations

import sys

from fansi._args import prepare
from fansi._const import CTL_ALL, WARN_MANGLED
from fansi._read import coerce_texts, find_ctl, resolve_warn, seek_ctl
from fansi._state import state_init_ctl, state_reinit

_MISSING = object()


def has_ctl(x, ctl="all", warn=_MISSING, which=_MISSING):
    """TRUE where a string contains a selected control sequence."""
    if which is not _MISSING:
        sys.stderr.write("Parameter `which` has been deprecated; use `ctl` instead.\n")
        ctl = which
    warn = resolve_warn(warn, _MISSING)
    texts = coerce_texts(x)
    checked = prepare(
        x=texts, ctl=ctl, warn=warn, warn_mask=WARN_MANGLED, coerce_x=False
    )
    ctl_int = checked["ctl_int"]
    if not ctl_int:
        return [False] * len(texts)
    warn_int = checked["warn_int"]
    out = []
    state = None
    for index, text in enumerate(texts):
        if state is None:
            state = state_init_ctl(texts, warn_int, ctl_int, index)
        else:
            state_reinit(state, texts, index)
        if text is None:
            out.append(None)
            continue
        data = state.string
        offset = seek_ctl(data, 0)
        if offset < len(data) and data[offset]:
            state.pos_x = offset
            find_ctl(state, index, "x")
            out.append(bool(state.status & CTL_ALL))
        else:
            out.append(False)
    return out


def has_sgr(x, warn=_MISSING):
    """TRUE where a string contains an SGR or OSC hyperlink sequence."""
    if warn is _MISSING:
        return has_ctl(x, ctl=["sgr", "url"])
    return has_ctl(x, ctl=["sgr", "url"], warn=warn)
