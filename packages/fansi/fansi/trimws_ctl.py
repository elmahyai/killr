"""Control-aware trimws, from fansi src/trimws.c and R/trimws.R."""

from __future__ import annotations

from fansi._args import FansiError, option, pmatch, prepare
from fansi._const import CTL_ALL, STAT_WARNED, WARN_MASK
from fansi._read import coerce_texts, read_next, resolve_warn
from fansi._state import state_init_full, state_reinit
from fansi.simple import dflt_term_cap
from fansi.strwrap_ctl import _MISSING, _Buff, _decode, _w_bridge, _w_normalize, _w_sgr, _w_url

_WHICH = ("both", "left", "right")
_SPACE = (0x20, 0x0A, 0x0D, 0x09)


def _printable(byte):
    return 0x20 <= byte < 0x7F


def _trim_one(state, which, normalize, index):
    data = state.string
    length = len(data)
    start = 0
    lead = state
    if which in (0, 1):
        while True:
            byte = state.at(state.pos_x)
            if byte in _SPACE:
                state.pos_x += 1
                continue
            if _printable(byte):
                break
            tmp = state.copy()
            read_next(tmp, index, "x")
            state.status |= tmp.status & STAT_WARNED
            if tmp.status & CTL_ALL:
                state = tmp
                continue
            break
        lead = state.copy()
        start = lead.pos_x
    end = -1
    trail = state.copy()
    last = state.copy()
    if which in (0, 2):
        while state.at(state.pos_x):
            byte = state.at(state.pos_x)
            if byte in _SPACE:
                if end < 0:
                    end = state.pos_x
                    trail = state.copy()
                state.pos_x += 1
                continue
            if _printable(byte):
                end = -1
                state.pos_x += 1
            else:
                tmp = state.copy()
                read_next(tmp, index, "x")
                state.status |= tmp.status & STAT_WARNED
                if tmp.status & CTL_ALL:
                    state = tmp
                    continue
                end = -1
                state.pos_x += 1
        last = state.copy()
    if end < 0:
        end = length
        trail = last.copy()
    if not start and end == length:
        return None
    buff = _Buff()
    if start:
        _w_sgr(buff, lead.fmt.sgr, normalize, True)
        _w_url(buff, lead.fmt.url)
    if normalize:
        body = lead.copy()
        wrote = _w_normalize(buff, body, end, index, "x")
        if not wrote:
            buff.mcopy(data[start:], end - start)
    else:
        buff.mcopy(data[start:], end - start)
    if end:
        _w_bridge(buff, trail, last, normalize)
    return _decode(buff.value())


def trimws_ctl(
    x,
    which="both",
    whitespace="[ \t\r\n]",
    warn=_MISSING,
    term_cap=_MISSING,
    ctl="all",
    normalize=_MISSING,
):
    """Drop leading and trailing whitespace, leaving control sequences in place."""
    if whitespace != "[ \t\r\n]":
        raise FansiError("Argument `whitespace` may only be set to \"[ \\t\\r\\n]\".")
    warn = resolve_warn(warn, _MISSING)
    if term_cap is _MISSING:
        term_cap = option("fansi.term.cap", dflt_term_cap())
    if normalize is _MISSING:
        normalize = option("fansi.normalize", False)
    texts = coerce_texts(x)
    checked = prepare(
        x=texts,
        warn=warn,
        term_cap=term_cap,
        ctl=ctl,
        normalize=normalize,
        warn_mask=WARN_MASK,
        coerce_x=False,
    )
    head = which[0] if isinstance(which, (list, tuple)) else which
    if not isinstance(head, str):
        raise FansiError(
            "Argument `which` must partial match one of "
            'c("both", "left", "right").'
        )
    matched = pmatch(head, _WHICH)
    if matched is None:
        raise FansiError(
            "Argument `which` must partial match one of "
            'c("both", "left", "right").'
        )
    which_i = matched
    out = list(texts)
    state = None
    norm = bool(checked["normalize"])
    for index, text in enumerate(texts):
        if text is None:
            continue
        if state is None:
            state = state_init_full(
                texts,
                checked["warn_int"],
                checked["term_cap_int"],
                False,
                False,
                0,
                checked["ctl_int"],
                index,
            )
        else:
            state_reinit(state, texts, index)
        trimmed = _trim_one(state, which_i, norm, index)
        if trimmed is not None:
            out[index] = trimmed
    return out
