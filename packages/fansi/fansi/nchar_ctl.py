"""Control-aware nchar and nzchar, from fansi src/nchar.c and R/nchar.R."""

from __future__ import annotations

import sys

from fansi._args import FansiError, prepare
from fansi._const import (
    COUNT_GRAPH,
    COUNT_WIDTH,
    ERR_BAD_UTF8,
    SET_ALLOWNA,
    STAT_ERR_ALL,
    STAT_ERR_START,
    VALID_TYPES,
    WARN_MANGLED,
    WARN_UTF8,
    get_range,
)
from fansi._read import coerce_texts, read_all, read_until, resolve_warn
from fansi._state import state_init_full, state_reinit

_MISSING = object()


def _missing_result(keep_na, type_int, zero):
    """What nchar/nzchar return for a missing string. None is R's NA."""
    if keep_na is True or (
        keep_na is None and type_int not in (COUNT_WIDTH, COUNT_GRAPH) and not zero
    ):
        return None
    return True if zero else 2


def _count(texts, type_int, allow_na, keep_na, ctl_int, warn_int, zero):
    out = []
    state = None
    for index, text in enumerate(texts):
        if state is None:
            state = state_init_full(
                texts, warn_int, [1], allow_na, keep_na, type_int, ctl_int, index
            )
        else:
            state_reinit(state, texts, index)
        if text is None:
            out.append(_missing_result(keep_na, type_int, zero))
            continue
        if zero:
            read_until(state, 1, 0, 0, 1, index, "x")
            out.append(state.pos_w > 0)
            continue
        read_all(state, index, "x")
        err = get_range(state.status, STAT_ERR_START, STAT_ERR_ALL)
        if err == ERR_BAD_UTF8:
            if state.settings & SET_ALLOWNA:
                out.append(None)
            else:
                raise FansiError("Internal Error: invalid encoding unhandled.")
        else:
            out.append(state.pos_w)
    return out


def nchar_ctl(
    x,
    type="chars",
    allowNA=False,
    keepNA=None,
    ctl="all",
    warn=_MISSING,
    strip=_MISSING,
):
    """Count characters, width, graphemes, or bytes, skipping selected controls."""
    if strip is not _MISSING:
        sys.stderr.write("Parameter `strip` has been deprecated; use `ctl` instead.\n")
        ctl = strip
    warn = resolve_warn(warn, _MISSING)
    if allowNA is None:
        allowNA = False
    warn_mask = WARN_MANGLED if allowNA is True else (WARN_MANGLED | WARN_UTF8)
    texts = coerce_texts(x)
    checked = prepare(
        x=texts,
        ctl=ctl,
        warn=warn,
        type_=type,
        allow_na=allowNA,
        keep_na=keepNA,
        valid_types=VALID_TYPES,
        warn_mask=warn_mask,
        coerce_x=False,
    )
    return _count(
        texts,
        checked["type_int"],
        checked["allow_na"],
        checked.get("keep_na", None),
        checked["ctl_int"],
        checked["warn_int"],
        False,
    )


def nzchar_ctl(x, keepNA=False, ctl="all", warn=_MISSING):
    """TRUE when any counted character remains after selected controls are ignored."""
    warn = resolve_warn(warn, _MISSING)
    texts = coerce_texts(x)
    checked = prepare(
        x=texts,
        ctl=ctl,
        warn=warn,
        type_="chars",
        keep_na=keepNA,
        valid_types=("chars", "width", "bytes"),
        warn_mask=WARN_MANGLED,
        coerce_x=False,
    )
    return _count(
        texts,
        checked["type_int"],
        True,
        checked.get("keep_na", None),
        checked["ctl_int"],
        checked["warn_int"],
        True,
    )


def nchar_sgr(x, type="chars", allowNA=False, keepNA=None, warn=_MISSING):
    """nchar_ctl with SGR sequences treated as zero width."""
    kwargs = {"type": type, "allowNA": allowNA, "keepNA": keepNA, "ctl": "sgr"}
    if warn is not _MISSING:
        kwargs["warn"] = warn
    return nchar_ctl(x, **kwargs)


def nzchar_sgr(x, keepNA=None, warn=_MISSING):
    """nzchar_ctl with SGR sequences ignored."""
    if warn is _MISSING:
        return nzchar_ctl(x, keepNA=keepNA, ctl="sgr")
    return nzchar_ctl(x, keepNA=keepNA, warn=warn, ctl="sgr")
