"""Normalize SGR and OSC URL sequences, from R/normalize.R and src/normalize.c."""

from __future__ import annotations

from fansi._args import FansiError, option, prepare
from fansi._const import WARN_MASK
from fansi._read import coerce_texts, read_all, resolve_warn
from fansi._state import reset_pos, state_init, state_init_full, state_reinit
from fansi._write import Buff, write_normalize
from fansi.simple import dflt_term_cap

_MISSING = object()


def _term_cap(value):
    if value is _MISSING:
        value = option("fansi.term.cap", None)
        if value is None:
            value = dflt_term_cap()
    return value


def _decode(raw):
    return bytes(raw).decode("utf-8", "surrogateescape")


def normalize_state(x, warn=_MISSING, term_cap=_MISSING, carry=_MISSING):
    """Rewrite SGR and OSC URLs into one decomposed form.

    A missing string is None. A Python str is one element. The result is a list.
    """
    warn = resolve_warn(warn, _MISSING)
    term_cap = _term_cap(term_cap)
    if carry is _MISSING:
        carry = option("fansi.carry", False)
    if carry is None:
        raise FansiError("Argument `carry` may not be NA.")
    texts = coerce_texts(x)
    checked = prepare(
        x=texts,
        warn=warn,
        term_cap=term_cap,
        carry=carry,
        warn_mask=WARN_MASK,
        coerce_x=False,
    )
    do_carry = checked["carry"] is not None
    carry_text = checked["carry"] if do_carry else ""
    state_carry = state_init_full(
        [carry_text],
        checked["warn_int"],
        checked["term_cap_int"],
        True,
        True,
        0,
        [1],
        0,
    )
    read_all(state_carry, 0, "carry")
    reset_pos(state_carry)
    out = list(texts)
    any_na = False
    state = None
    err_msg = "Normalizing state"
    for index, text in enumerate(texts):
        if state is None:
            state = state_init(texts, checked["warn_int"], checked["term_cap_int"], index)
        else:
            state_reinit(state, texts, index)
        if text is None or (any_na and do_carry):
            any_na = True
            out[index] = None
            continue
        if do_carry:
            state.fmt.sgr = state_carry.fmt.sgr.copy()
            state.fmt.url = state_carry.fmt.url.copy()
        buff = Buff()
        written = write_normalize(buff, state, len(state.string), index, err_msg, "x")
        state_carry.fmt.sgr = state.fmt.sgr.copy()
        state_carry.fmt.url = state.fmt.url.copy()
        if written < 0:
            continue
        out[index] = _decode(buff.data)
    return out
