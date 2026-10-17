"""Active SGR at the end of a string, and the sequence that closes it.

From R/sgr.R, src/carry.c, and src/state.c. `state_at_end` reads with ctl
"sgr" only. `close_state` reads every sequence and has no carry.
"""

from __future__ import annotations

from fansi._args import FansiError, option, prepare
from fansi._const import WARN_MASK
from fansi._read import coerce_texts, read_all, resolve_warn
from fansi._state import reset_pos, state_init_full, state_reinit
from fansi._write import Buff, state_as_chr, write_close
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


def state_at_end(
    x,
    warn=_MISSING,
    term_cap=_MISSING,
    normalize=_MISSING,
    carry=_MISSING,
):
    """Active SGR at the end of each string. A str is one element. None is missing."""
    warn = resolve_warn(warn, _MISSING)
    term_cap = _term_cap(term_cap)
    if normalize is _MISSING:
        normalize = option("fansi.normalize", False)
    # The C entry point checks this argument under the name `norm`.
    if not isinstance(normalize, bool):
        raise FansiError("Argument `norm` must be TRUE or FALSE.")
    if carry is _MISSING:
        carry = option("fansi.carry", False)
    if carry is None:
        raise FansiError("Argument `carry` may not be NA.")
    texts = coerce_texts(x)
    checked = prepare(
        x=texts,
        ctl="sgr",
        warn=warn,
        term_cap=term_cap,
        carry=carry,
        warn_mask=WARN_MASK,
        coerce_x=False,
    )
    checked["normalize"] = normalize
    do_carry = checked["carry"] is not None
    carry_text = checked["carry"] if do_carry else ""
    state_prev = state_init_full(
        [carry_text],
        checked["warn_int"],
        checked["term_cap_int"],
        True,
        True,
        0,
        checked["ctl_int"],
        0,
    )
    read_all(state_prev, 0, "carry")
    reset_pos(state_prev)
    out = []
    any_na = False
    state = None
    normalize_flag = checked["normalize"]
    for index, text in enumerate(texts):
        if state is None:
            state = state_init_full(
                texts,
                checked["warn_int"],
                checked["term_cap_int"],
                True,
                True,
                0,
                checked["ctl_int"],
                index,
            )
        else:
            state_reinit(state, texts, index)
        if text is None or (any_na and do_carry):
            any_na = True
            out.append(None)
            continue
        if do_carry:
            state.fmt.sgr = state_prev.fmt.sgr.copy()
        read_all(state, index, "x")
        reset_pos(state)
        buff = Buff()
        state_as_chr(buff, state, normalize_flag, index)
        out.append(_decode(buff.data))
        state_prev = state.copy()
    return out


def close_state(x, warn=_MISSING, normalize=_MISSING):
    """Closing sequence for SGR and OSC URLs active at the end of each string.

    With `normalize` false, any active SGR closes as ESC[0m. A string with
    nothing to close, including a missing string, yields an empty string.
    """
    warn = resolve_warn(warn, _MISSING)
    if normalize is _MISSING:
        normalize = option("fansi.normalize", False)
    texts = coerce_texts(x)
    checked = prepare(
        x=texts,
        warn=warn,
        normalize=normalize,
        warn_mask=WARN_MASK,
        coerce_x=False,
    )
    out = [""] * len(texts)
    state = None
    normalize_flag = checked["normalize"]
    for index, text in enumerate(texts):
        if state is None:
            state = state_init_full(
                texts,
                checked["warn_int"],
                [1],
                True,
                True,
                0,
                [1],
                index,
            )
        else:
            state_reinit(state, texts, index)
        if text is None or text == "":
            continue
        read_all(state, index, "x")
        buff = Buff()
        write_close(buff, state.fmt, normalize_flag, index)
        if buff.data:
            out[index] = _decode(buff.data)
    return out
