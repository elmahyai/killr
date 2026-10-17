"""Unhandled control sequences, from R/unhandled.R and src/unhandled.c.

Error numbers are the values `unhandled.c` stores. R labels them, in order:

1 unknown-substr, 2 invalid-substr, 3 exceed-term-cap,
4 non-SGR/hyperlink, 5 CSI/OSC-bad-substr, 6 malformed-CSI/OSC,
7 non-CSI/OSC, 8 malformed-ESC, 9 C0, 10 malformed-UTF8, 11 non-ASCII.
"""

from __future__ import annotations

from fansi._args import FansiError, option, prepare
from fansi._const import (
    CTL_ALL,
    SET_ESCONE,
    STAT_ERR_ALL,
    STAT_ERR_START,
    get_range,
)
from fansi._read import _emit_warning, coerce_texts, read_next
from fansi._state import INT_MAX, state_init_full, state_reinit
from fansi.simple import dflt_term_cap

_MISSING = object()

# Installed labels. The Rd name "CSI/OSC" is "non-SGR/hyperlink" in R/unhandled.R.
ERROR_LABELS = (
    "unknown-substr",
    "invalid-substr",
    "exceed-term-cap",
    "non-SGR/hyperlink",
    "CSI/OSC-bad-substr",
    "malformed-CSI/OSC",
    "non-CSI/OSC",
    "malformed-ESC",
    "C0",
    "malformed-UTF8",
    "non-ASCII",
)


def _term_cap(value):
    if value is _MISSING:
        value = option("fansi.term.cap", None)
        if value is None:
            value = dflt_term_cap()
    return value


def _err(status):
    return get_range(status, STAT_ERR_START, STAT_ERR_ALL)


def unhandled_ctl(x, term_cap=_MISSING):
    """Sequences a terminal would mishandle.

    Returns the six columns of the R data frame. `error` is the label for the
    integer code. `translated` is false. None in `x` is a missing string and
    is skipped. A Python str is one element.
    """
    term_cap = _term_cap(term_cap)
    texts = coerce_texts(x)
    checked = prepare(x=texts, term_cap=term_cap, coerce_x=False)
    if len(texts) >= INT_MAX:
        raise FansiError(
            "This function does not support vectors of length INT_MAX or longer."
        )
    columns = {
        "index": [],
        "start": [],
        "stop": [],
        "error": [],
        "translated": [],
        "esc": [],
    }
    state = None
    err_count = 0
    break_early = False
    for index, text in enumerate(texts):
        if state is None:
            # ctl 0 flips to every control. Width mode 1 counts display width.
            # warn 0 records sequences without warning.
            state = state_init_full(
                texts, 0, checked["term_cap_int"], True, True, 1, [0], index
            )
            state.settings |= SET_ESCONE
        else:
            state_reinit(state, texts, index)
        if text is None or not state.string:
            continue
        data = state.string
        ctl_bytes_all = 0
        while state.at(state.pos_x):
            esc_start = state.pos_w + ctl_bytes_all
            esc_start_byte = state.pos_x
            read_next(state, index, "x")
            if state.status & CTL_ALL:
                ctl_bytes_all += state.pos_x - esc_start_byte
            err = _err(state.status)
            if not err:
                continue
            if err_count == INT_MAX:
                _emit_warning(
                    "There are more than INT_MAX unhandled sequences, returning "
                    "first INT_MAX errors."
                )
                break_early = True
                break
            byte_end = state.pos_x - 1
            if (
                esc_start_byte < 0
                or byte_end < 0
                or esc_start_byte >= len(data)
                or byte_end >= len(data)
            ):
                raise RuntimeError(
                    "Internal Error: illegal byte offsets for extracting "
                    "unhandled seq; contact maintainer."
                )
            chunk = data[esc_start_byte:byte_end + 1]
            columns["index"].append(index + 1)
            columns["start"].append(esc_start + 1)
            columns["stop"].append(state.pos_w + ctl_bytes_all)
            columns["error"].append(ERROR_LABELS[err - 1])
            columns["translated"].append(False)
            columns["esc"].append(chunk.decode("utf-8", "surrogateescape"))
            err_count += 1
        if break_early:
            break
    return columns
