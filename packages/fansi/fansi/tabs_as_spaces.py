"""Replace tabs with spaces, from fansi src/tabs.c and R/misc.R."""

from __future__ import annotations

from fansi._args import FansiError, option, prepare, warn_mask_worst
from fansi._const import WARN_MASK
from fansi._read import coerce_texts, read_next, resolve_warn
from fansi._state import INT_MAX, reset_width, state_init_full, state_reinit

_MISSING = object()


def _at(data, index):
    if data is None or index < 0 or index >= len(data):
        return 0
    return data[index]


def _decode(data):
    return data.decode("utf-8", "surrogateescape")


def _tab_spaces(pos_w, stops, stop_idx, accumulated):
    """Spaces to the next stop. `stop_idx` stays on the last stop and repeats it."""
    while pos_w >= accumulated:
        size = stops[stop_idx]
        if size < 1:
            raise FansiError("Internal Error: stop size less than 1.")
        if accumulated > INT_MAX - size:
            raise FansiError("Integer overflow when attempting to compute tab width.")
        accumulated += size
        if stop_idx < len(stops) - 1:
            stop_idx += 1
    return accumulated - pos_w, stop_idx, accumulated


def expand_tabs(texts, tab_stops, warn_int, term_cap_int, ctl_int):
    """Expand tabs in each string. `ctl` selects which sequences have zero width."""
    if not tab_stops:
        raise FansiError("Internal Error: must have at least one tab stop")
    if len(tab_stops) > INT_MAX:
        raise FansiError("Internal Error: can have at most INT_MAX tab stops")
    max_stop = 1
    for stop in tab_stops:
        if stop > max_stop:
            max_stop = stop
        if stop < 1:
            raise FansiError("Internal Error: stop size less than 1.")
    out = list(texts)
    state = None
    for index, text in enumerate(texts):
        if text is None:
            continue
        if state is None:
            state = state_init_full(
                texts, warn_int, term_cap_int, True, True, 1, ctl_int, index
            )
        else:
            state_reinit(state, texts, index)
        data = state.string
        if b"\t" not in data:
            continue
        tab_count = data.count(b"\t")
        extra = max_stop - 1
        new_size = len(data)
        for _ in range(tab_count):
            if new_size > INT_MAX - extra:
                raise FansiError(
                    "Converting tabs to spaces will cause string to be longer than "
                    "allowed INT_MAX."
                )
            new_size += extra
        parts = []
        last = state.pos_x
        settings = state.settings
        stop_idx = 0
        accumulated = 0
        while True:
            current = _at(state.string, state.pos_x)
            extra_spaces = 0
            if current == 0x09:
                extra_spaces, stop_idx, accumulated = _tab_spaces(
                    state.pos_w, tab_stops, stop_idx, accumulated
                )
            elif current == 0x0A:
                reset_width(state)
                stop_idx = 0
                accumulated = 0
            if current == 0x09 or current == 0:
                parts.append(state.string[last:state.pos_x])
                state.settings &= ~WARN_MASK
                read_next(state, index, "x")
                state.settings = settings
                current = _at(state.string, state.pos_x)
                if extra_spaces < 0:
                    raise FansiError("Internal Error: inc may not be negative.")
                if state.pos_w > INT_MAX - extra_spaces:
                    raise FansiError(
                        "Expanding tabs will cause string to exceed INT_MAX at index "
                        f"[{index + 1}]."
                    )
                state.pos_w += extra_spaces
                if extra_spaces:
                    parts.append(b" " * extra_spaces)
                last = state.pos_x
            else:
                read_next(state, index, "x")
            if current == 0:
                break
        out[index] = _decode(b"".join(parts))
    return out


def tabs_as_spaces(x, tab_stops=_MISSING, warn=_MISSING, ctl="all"):
    """Replace each tab with the spaces that reach the next tab stop.

    The default stop is every 8 columns. `ctl` decides which sequences have
    zero width. Tabs are converted either way.
    """
    if tab_stops is _MISSING:
        tab_stops = option("fansi.tab.stops", 8)
    warn = resolve_warn(warn, _MISSING)
    texts = coerce_texts(x)
    checked = prepare(
        x=texts,
        warn=warn,
        ctl=ctl,
        tab_stops=tab_stops,
        warn_mask=warn_mask_worst(),
        coerce_x=False,
    )
    # The installed function assumes every terminal capability.
    return expand_tabs(texts, checked["tab_stops"], checked["warn_int"], [1], checked["ctl_int"])
