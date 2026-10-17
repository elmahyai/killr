"""Control-aware substr, from fansi src/substr.c, src/write.c, and R/substr2.R.

Opening and closing SGR and OSC sequences are written here. The compare and
state-to-string logic follows src/state.c. Tabs expand with the src/tabs.c rules.
"""

from __future__ import annotations

import re
import warnings

from fansi._args import FansiError, option, prepare
from fansi._const import (
    BRD_ENCIRC,
    BRD_FRAMED,
    BRD_OVERLN,
    CLR_256,
    CLR_8,
    CLR_BRIGHT,
    CLR_TRU,
    COUNT_WIDTH,
    CTL_ALL,
    FONT_ALL,
    FONT_START,
    IDG_MASK,
    IDG_OVERL,
    IDG_OVERL2,
    IDG_STRESS,
    IDG_UNDERL,
    IDG_UNDERL2,
    RND_BOTH,
    RND_START,
    RND_STOP,
    STAT_SPECIAL,
    STAT_WARNED,
    STL_BLINK1,
    STL_BLINK2,
    STL_BLUR,
    STL_BOLD,
    STL_CONCEAL,
    STL_CROSSOUT,
    STL_FRAKTUR,
    STL_INVERT,
    STL_ITALIC,
    STL_PROPSPC,
    STL_UNDER,
    STL_UNDER2,
    WARN_MASK,
)
from fansi._read import (
    coerce_texts,
    read_all,
    read_next,
    read_until,
    resolve_warn,
)
from fansi._state import INT_MAX, Sgr, reset_state, reset_width, state_init_full, state_reinit
from fansi.simple import dflt_term_cap

_MISSING = object()
_NA_INTEGER = -2147483648
_CLR_MASK = 240
_FONT_MASK = FONT_ALL << FONT_START
_NUMBER = re.compile(
    r"[ \t]*([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)[ \t]*$"
)


def _emit_coerce(message):
    warnings.warn(message, UserWarning, stacklevel=3)


def _string_integer(item):
    if item == "NA":
        return None, None
    match = _NUMBER.match(item)
    if match is None:
        return None, "coerce"
    try:
        number = float(match.group(1))
    except ValueError:
        return None, "coerce"
    if number != number or number == float("inf") or number == float("-inf"):
        return None, "coerce"
    if number <= -2147483648 or number >= 2147483648:
        return None, "range"
    return int(number), None


def _one_integer_fixed(item):
    if item is None:
        return None, None
    if isinstance(item, bool):
        return int(item), None
    if isinstance(item, int):
        if item < -2147483647 or item > 2147483647:
            return None, "range"
        return item, None
    if isinstance(item, float):
        if item != item or item == float("inf") or item == float("-inf"):
            return None, "coerce"
        if item <= -2147483648 or item >= 2147483648:
            return None, "range"
        return int(item), None
    if isinstance(item, str):
        return _string_integer(item)
    raise FansiError("not an integer")


def as_integer_vector(value, name):
    """R as.integer. Out-of-range values become missing and warn once."""
    if isinstance(value, (list, tuple)):
        items = list(value)
    else:
        items = [value]
    if not items:
        raise FansiError(f"Argument `{name}` must be interpretable as an integer.")
    out = []
    saw_coerce = False
    saw_range = False
    for item in items:
        try:
            converted, kind = _one_integer_fixed(item)
        except FansiError:
            raise FansiError(
                f"Argument `{name}` must be interpretable as an integer."
            ) from None
        if kind == "coerce" and not saw_coerce:
            _emit_coerce("NAs introduced by coercion")
            saw_coerce = True
        elif kind == "range" and not saw_range:
            _emit_coerce("NAs introduced by coercion to integer range")
            saw_range = True
        out.append(converted)
    return out


def _decode(buff):
    return bytes(buff).decode("utf-8", "surrogateescape")


def _bytes_of(text):
    if text is None:
        return b""
    if isinstance(text, str):
        return text.encode("utf-8", "surrogateescape")
    return bytes(text)


def _offset_bytes(url, offset):
    data = _bytes_of(url.string)
    return data[offset.start:offset.start + offset.len]


def sgr_active(sgr):
    return bool(sgr.style or sgr.color.x or sgr.bgcol.x)


def url_active(url):
    return url.url.len > 0


def _sgr_comp_color(target, current):
    tclr = target.x
    cclr = current.x
    c256 = tclr & (CLR_256 | CLR_TRU)
    ctru = tclr & CLR_TRU
    return (
        tclr != cclr
        or (c256 and target.extra[0] != current.extra[0])
        or (ctru and target.extra[1] != current.extra[1])
        or (ctru and target.extra[2] != current.extra[2])
    )


def sgr_comp_color(target, current):
    """True when foreground or background differs. Matches FANSI_sgr_comp_color."""
    return _sgr_comp_color(target.color, current.color) or _sgr_comp_color(
        target.bgcol, current.bgcol
    )


def sgr_setdiff(old, new, mode):
    """Styles in `old` that `new` does not keep. `mode` 0 closes overrides."""
    res = Sgr()
    if (not mode and _sgr_comp_color(old.color, new.color)) or (
        mode and old.color.x and not new.color.x
    ):
        res.color = old.color.copy()
    if (not mode and _sgr_comp_color(old.bgcol, new.bgcol)) or (
        mode and old.bgcol.x and not new.bgcol.x
    ):
        res.bgcol = old.bgcol.copy()
    font_old = old.style & _FONT_MASK
    font_new = new.style & _FONT_MASK
    if (not mode and font_old != font_new) or (mode and font_old and not font_new):
        res.style = (res.style & ~_FONT_MASK) | font_old
    style_old = old.style & ~_FONT_MASK
    style_new = new.style & ~_FONT_MASK
    res.style |= style_old & ~style_new
    return res


def sgr_intersect(old, new):
    """Styles present in both. Font bits follow the C intersect, which clears them."""
    res = Sgr()
    if old.color.x == new.color.x:
        res.color = new.color.copy()
    if old.bgcol.x == new.bgcol.x:
        res.bgcol = new.bgcol.copy()
    font_old = old.style & _FONT_MASK
    font_new = new.style & _FONT_MASK
    if font_old == font_new:
        res.style &= font_new | ~_FONT_MASK
    style_old = old.style & ~_FONT_MASK
    style_new = new.style & ~_FONT_MASK
    res.style |= style_old & style_new
    return res


def url_comp(target, current):
    """1 when the URL or id differs, 0 when both match. Empty ids do not compare."""
    t_url = _offset_bytes(target, target.url)
    c_url = _offset_bytes(current, current.url)
    t_id = _offset_bytes(target, target.id)
    c_id = _offset_bytes(current, current.id)
    url_eq = len(t_url) == len(c_url) and (not t_url or t_url == c_url)
    id_eq = len(t_id) == len(c_id) and (
        (not t_url and not t_id) or (bool(t_id) and t_id == c_id)
    )
    return 0 if url_eq and id_eq else 1


def _make_token(val, normalize):
    if len(val) > 2:
        raise FansiError("Internal error: token maker limited to 2 chars max.")
    if not normalize:
        return (val + ";").encode("ascii")
    return b"\033[" + val.encode("ascii") + b"m"


def _color_token(color, mode, normalize):
    if mode not in (3, 4):
        raise FansiError("Internal Error: color mode must be 3 or 4")
    parts = []
    if normalize:
        parts.append(b"\033[")
    clrval = color.x & ~_CLR_MASK
    if (color.x & _CLR_MASK) == CLR_BRIGHT:
        if mode == 3:
            parts.append(bytes((ord("9"), ord("0") + clrval)))
        else:
            parts.append(bytes((ord("1"), ord("0"), ord("0") + clrval)))
    else:
        parts.append(bytes((ord("0") + mode, ord("0") + clrval)))
        if color.x & (CLR_256 | CLR_TRU):
            if color.x & CLR_TRU:
                extra = f"2;{color.extra[0]};{color.extra[1]};{color.extra[2]}"
            else:
                extra = f"5;{color.extra[0]}"
            parts.append(b";" + extra.encode("ascii"))
        elif not (color.x & CLR_8):
            raise FansiError("Internal Error: unexpected color mode.")
    parts.append(b"m" if normalize else b";")
    token = b"".join(parts)
    if len(token) >= 19:
        raise FansiError(
            f"Internal Error: exceeded color buffer ({len(token)} vs 20)."
        )
    return token


def _seal(buff):
    if buff:
        buff[-1] = ord("m")


def w_sgr(buff, sgr, normalize, enclose, index):
    """Write an SGR state. Token order matches FANSI_W_sgr."""
    del index
    if not sgr_active(sgr):
        return
    if not normalize and enclose:
        buff.extend(b"\033[")
    style = sgr.style
    if style & STL_BOLD:
        buff.extend(_make_token("1", normalize))
    if style & STL_BLUR:
        buff.extend(_make_token("2", normalize))
    if style & STL_ITALIC:
        buff.extend(_make_token("3", normalize))
    if style & STL_UNDER:
        buff.extend(_make_token("4", normalize))
    if style & STL_BLINK1:
        buff.extend(_make_token("5", normalize))
    if style & STL_BLINK2:
        buff.extend(_make_token("6", normalize))
    if style & STL_INVERT:
        buff.extend(_make_token("7", normalize))
    if style & STL_CONCEAL:
        buff.extend(_make_token("8", normalize))
    if style & STL_CROSSOUT:
        buff.extend(_make_token("9", normalize))
    if style & STL_FRAKTUR:
        buff.extend(_make_token("20", normalize))
    if style & STL_UNDER2:
        buff.extend(_make_token("21", normalize))
    if style & STL_PROPSPC:
        buff.extend(_make_token("26", normalize))
    if sgr.color.x:
        buff.extend(_color_token(sgr.color, 3, normalize))
    if sgr.bgcol.x:
        buff.extend(_color_token(sgr.bgcol, 4, normalize))
    if style & BRD_FRAMED:
        buff.extend(_make_token("51", normalize))
    if style & BRD_ENCIRC:
        buff.extend(_make_token("52", normalize))
    if style & BRD_OVERLN:
        buff.extend(_make_token("53", normalize))
    if style & IDG_UNDERL:
        buff.extend(_make_token("60", normalize))
    if style & IDG_UNDERL2:
        buff.extend(_make_token("61", normalize))
    if style & IDG_OVERL:
        buff.extend(_make_token("62", normalize))
    if style & IDG_OVERL2:
        buff.extend(_make_token("63", normalize))
    if style & IDG_STRESS:
        buff.extend(_make_token("64", normalize))
    font = (style >> FONT_START) & FONT_ALL
    if font:
        tok = "1" + chr(ord("0") + (font % 10))
        buff.extend(_make_token(tok, normalize))
    if enclose:
        _seal(buff)


def w_url(buff, url, index):
    """Write an OSC 8 hyperlink when one is active."""
    del index
    if not url_active(url):
        return
    buff.extend(b"\033]8;")
    if url.id.len:
        buff.extend(b"id=")
        buff.extend(_offset_bytes(url, url.id))
    buff.extend(b";")
    buff.extend(_offset_bytes(url, url.url))
    buff.extend(b"\033\\")


def w_sgr_close(buff, sgr, normalize, index):
    """Close active SGR. Normalize closes each class; otherwise one reset."""
    del index
    if not sgr_active(sgr):
        return
    if not normalize:
        buff.extend(b"\033[0m")
        return
    style = sgr.style
    if style & _FONT_MASK:
        buff.extend(b"\033[10m")
    if style & (STL_BOLD | STL_BLUR):
        buff.extend(b"\033[22m")
    if style & (STL_ITALIC | STL_FRAKTUR):
        buff.extend(b"\033[23m")
    if style & (STL_UNDER | STL_UNDER2):
        buff.extend(b"\033[24m")
    if style & (STL_BLINK1 | STL_BLINK2):
        buff.extend(b"\033[25m")
    if style & STL_INVERT:
        buff.extend(b"\033[27m")
    if style & STL_CONCEAL:
        buff.extend(b"\033[28m")
    if style & STL_CROSSOUT:
        buff.extend(b"\033[29m")
    if sgr.color.x:
        buff.extend(b"\033[39m")
    if sgr.bgcol.x:
        buff.extend(b"\033[49m")
    if style & STL_PROPSPC:
        buff.extend(b"\033[50m")
    if style & (BRD_FRAMED | BRD_ENCIRC):
        buff.extend(b"\033[54m")
    if style & BRD_OVERLN:
        buff.extend(b"\033[55m")
    if style & IDG_MASK:
        buff.extend(b"\033[65m")


def w_url_close(buff, url, index):
    del index
    if url_active(url):
        buff.extend(b"\033]8;;\033\\")


def w_close(buff, fmt, normalize, index):
    w_sgr_close(buff, fmt.sgr, normalize, index)
    w_url_close(buff, fmt.url, index)


def w_bridge(buff, end, restart, normalize, index):
    """Sequences that take `end`'s active state to `restart`'s."""
    mode = 0 if normalize else 1
    to_close = sgr_setdiff(end.fmt.sgr, restart.fmt.sgr, mode)
    to_open = sgr_setdiff(restart.fmt.sgr, end.fmt.sgr, mode)
    if not normalize:
        renew = sgr_intersect(end.fmt.sgr, restart.fmt.sgr)
        active_open = sgr_active(to_open)
        active_close = sgr_active(to_close)
        if active_open and active_close:
            buff.extend(b"\033[0;")
            w_sgr(buff, renew, normalize, 0, index)
            w_sgr(buff, to_open, normalize, 0, index)
            _seal(buff)
        elif active_close:
            buff.extend(b"\033[0;")
            w_sgr(buff, renew, normalize, 0, index)
            _seal(buff)
        else:
            w_sgr(
                buff,
                sgr_setdiff(restart.fmt.sgr, end.fmt.sgr, 0),
                normalize,
                1,
                index,
            )
    else:
        w_sgr_close(buff, to_close, normalize, index)
        w_sgr(buff, to_open, normalize, 1, index)
    if url_comp(end.fmt.url, restart.fmt.url):
        if not url_active(restart.fmt.url):
            w_url_close(buff, end.fmt.url, index)
        w_url(buff, restart.fmt.url, index)


def state_as_chr(state, normalize, index):
    """Active SGR and URL at `state`, the way FANSI_state_as_chr writes them."""
    buff = bytearray()
    w_sgr(buff, state.fmt.sgr, normalize, 1, index)
    w_url(buff, state.fmt.url, index)
    return _decode(buff)


def w_normalize(buff, state, stop, index, arg):
    """Rewrite specials between the current byte and `stop`. True if any changed."""
    data = state.ensure_bytes()
    cursor = state.pos_x
    last = cursor
    any_to_exp = False
    while True:
        found = data.find(b"\x1b", cursor)
        if found < 0:
            found = len(data)
        state.pos_x = found
        if state.pos_x >= stop:
            if any_to_exp:
                buff.extend(data[last:stop])
            break
        if found < len(data) and data[found] == 0x1B:
            state_prev = state.copy()
            read_next(state, index, arg)
            if state.status & STAT_SPECIAL:
                any_to_exp = True
                buff.extend(data[last:found])
                w_bridge(buff, state_prev, state, 1, index)
                last = state.pos_x
            cursor = state.pos_x
            if cursor == found:
                raise FansiError("Internal Error: normalize logic error.")
        elif found >= len(data):
            raise FansiError("Internal Error: unexpected `stop` value for normalize.")
        else:
            raise FansiError("Internal Error: normalize logic error.")
    return any_to_exp


def w_normalize_or_copy(buff, state, norm_i, stop, index, arg):
    start = state.pos_x
    expanded = False
    if norm_i:
        expanded = w_normalize(buff, state.copy(), stop, index, arg)
    if not expanded:
        data = state.ensure_bytes()
        if stop < start:
            stop = start
        buff.extend(data[start:stop])


def _tab_width(state, tab_stops, acc):
    if state.at(state.pos_x) != 9:
        raise FansiError("Internal Error: computing tab width on not a tab")
    stops = len(tab_stops)
    while state.pos_w >= acc[1]:
        stop_size = tab_stops[acc[0]]
        if stop_size < 1:
            raise FansiError("Internal Error: stop size less than 1.")
        if acc[1] > INT_MAX - stop_size:
            raise FansiError("Integer overflow when attempting to compute tab width.")
        acc[1] += stop_size
        if acc[0] < stops - 1:
            acc[0] += 1
    return acc[1] - state.pos_w


def _expand_one_tab_string(state, tab_stops, index):
    """Replace tabs in the string `state` already points at. Width mode is set."""
    out = bytearray()
    last = state.pos_x
    acc = [0, 0]
    while True:
        cur = state.at(state.pos_x)
        extra = 0
        if cur == 9:
            extra = _tab_width(state, tab_stops, acc)
        elif cur == 10:
            reset_width(state)
            acc[0] = 0
            acc[1] = 0
        if cur == 9 or cur == 0:
            out.extend(state.string[last:state.pos_x])
            saved = state.settings
            state.settings &= ~WARN_MASK
            read_next(state, index, "x")
            state.settings = saved
            if extra and state.pos_w > INT_MAX - extra:
                raise FansiError(
                    "Expanding tabs will cause string to exceed INT_MAX "
                    f"at index [{index + 1}]."
                )
            state.pos_w += extra
            last = state.pos_x
            if extra:
                out.extend(b" " * extra)
            cur = state.at(state.pos_x)
        else:
            read_next(state, index, "x")
        if cur == 0:
            break
    return _decode(out)


def tabs_as_spaces(texts, tab_stops, term_cap_int, ctl_int):
    """Expand tabs using display width. Warnings stay off, as the C call does."""
    if not texts:
        return []
    out = list(texts)
    state = None
    for index, text in enumerate(texts):
        if state is None:
            state = state_init_full(
                texts, 0, term_cap_int, True, True, COUNT_WIDTH, ctl_int, index
            )
        else:
            state_reinit(state, texts, index)
        if text is None or "\t" not in text:
            continue
        out[index] = _expand_one_tab_string(state, tab_stops, index)
    return out


def substr_range(state_start, state_stop, index, start, stop, rnd_i, term_i, arg):
    """Read the byte range for one substring. Returns the width it covers."""
    state_stop.become(state_start)
    start0 = start - 1
    overshoot = not (rnd_i == RND_START or rnd_i == RND_BOTH)
    if start0 < 0 and stop > 0:
        state_tmp = state_start.copy()
        read_next(state_tmp, index, arg)
        if state_tmp.status & STAT_SPECIAL:
            state_start.become(state_tmp)
        state_start.status |= state_tmp.status & STAT_WARNED
    else:
        read_until(state_start, start0, overshoot, term_i, 0, index, arg)
    state_stop.become(state_start)
    overshoot = rnd_i == RND_STOP or rnd_i == RND_BOTH
    read_until(state_stop, stop, overshoot, term_i, 1, index, arg)
    if state_start.pos_x > state_stop.pos_x:
        raise FansiError("Internal Error: bad `stop` state 2.")
    return state_stop.pos_w - state_start.pos_w


def substr_one(state, ref, index, start, stop, rnd_i, norm_i, term_i):
    """One extracted substring. `state` becomes the stop position."""
    state_start = state.copy()
    state_stop = state.copy()
    if term_i:
        reset_state(state)
    else:
        state.fmt = ref.fmt.copy()
    substr_range(state_start, state_stop, index, start, stop, rnd_i, term_i, "x")
    empty = state_stop.pos_x == state_start.pos_x
    if (not (empty and term_i)) and stop > 0 and stop >= start:
        buff = bytearray()
        w_bridge(buff, state, state_start, norm_i, index)
        w_normalize_or_copy(buff, state_start, norm_i, state_stop.pos_x, index, "x")
        if term_i:
            w_close(buff, state_stop.fmt, norm_i, index)
        result = _decode(buff)
    else:
        result = ""
    state.become(state_stop)
    return result


def _c_int(value):
    if value is None:
        return _NA_INTEGER
    return value


def substr_extract(texts, starts, stops, carry_text, state, rnd_i, norm_i, term_i):
    """Extract each range. A missing string or bound is None. Carry spreads NA."""
    carry_on = carry_text is not None
    state_carry = state.copy()
    if carry_on:
        state_carry.string = _bytes_of(carry_text)
        state_carry.pos_x = 0
        state_carry.pos_w = 0
        state_carry.utf8 = 0
        read_all(state_carry, 0, "carry")
    state_ref = state_carry.copy()
    any_na = False
    out = []
    for index, text in enumerate(texts):
        state_reinit(state, texts, index)
        start_ii = starts[index]
        stop_ii = stops[index]
        if text is None or start_ii is None or stop_ii is None or (any_na and carry_on):
            any_na = any_na or text is None
            out.append(None)
        else:
            if carry_on:
                state.fmt = state_carry.fmt.copy()
            out.append(
                substr_one(
                    state, state_ref, index, start_ii, stop_ii, rnd_i, norm_i, term_i
                )
            )
        if carry_on and text is not None:
            state_ref = state.copy()
            read_all(state, index, "x")
            state_carry.fmt = state.fmt.copy()
    return out


def substr_replace(
    texts, starts, stops, values, carry_text, state, rnd_i, norm_i, term_i
):
    """Splice `values` into `texts`. The result reads as an in-place edit."""
    carry_on = carry_text is not None
    st_x2 = state.copy()
    st_x1 = state.copy()
    st_xlast = state.copy()
    st_xref = state.copy()
    st_v0 = state.copy()
    st_v1 = state.copy()
    st_vlast = state.copy()
    st_vref = state.copy()
    write_md = False
    any_na = False
    out = [None] * len(texts)
    for index, text in enumerate(texts):
        if text is None or values[index] is None or (carry_on and any_na):
            any_na = True
            out[index] = None
            continue
        if not term_i and write_md:
            st_vref = st_v1.copy()
        st_x0 = st_x2.copy()
        state_reinit(st_x0, texts, index)
        state_reinit(st_v0, values, index)
        if carry_on:
            st_x0.fmt = st_xlast.fmt.copy()
            st_v0.fmt = st_vlast.fmt.copy()
        st_x1 = st_x0.copy()
        st_x2 = st_x0.copy()
        start_ii = _c_int(starts[index])
        stop_ii = _c_int(stops[index])
        stop_ld = 1 if start_ii < 1 else start_ii
        start_tr = stop_ii + 1
        start_v = 1
        stop_v = start_tr - stop_ld
        substr_range(st_x2, st_x0, index, 1, stop_ld - 1, rnd_i, term_i, "x")
        substr_range(st_x1, st_x2, index, start_tr, start_tr, rnd_i, term_i, "x")
        substr_range(st_v0, st_v1, index, start_v, stop_v, rnd_i, term_i, "value")
        size_x = st_x1.pos_w - st_x0.pos_w
        size_v = st_v1.pos_w - st_v0.pos_w
        if size_v > size_x:
            stop_v -= 1
            substr_range(st_v0, st_v1, index, start_v, stop_v, rnd_i, term_i, "value")
            size_v = st_v1.pos_w - st_v0.pos_w
            if size_v > size_x:
                st_v1.become(st_v0)
                size_v = 0
                stop_v = start_v - 1
        if size_v < size_x:
            st_x11 = st_x0.copy()
            st_x21 = st_x0.copy()
            start_tr2 = st_x1.pos_w - (size_x - size_v) + 1
            substr_range(
                st_x11, st_x21, index, start_tr2, start_tr, rnd_i, term_i, "x"
            )
            size_x1 = st_x11.pos_w - st_x0.pos_w
            if size_v <= size_x1:
                start_tr = start_tr2
                st_x1 = st_x11
        write_ld = start_ii > 0 and (
            st_x0.pos_w > 0 or not (st_x0.status & CTL_ALL) or not term_i
        )
        write_md = (stop_ii >= start_ii) and (
            st_v1.pos_x > st_v0.pos_x or not term_i
        )
        write_tr = (start_tr - 1) <= st_x2.pos_w
        if write_md:
            buff = bytearray()
            if write_ld:
                lead = st_x0.ensure_bytes()
                buff.extend(lead[: st_x0.pos_x])
                if term_i:
                    w_close(buff, st_x0.fmt, norm_i, index)
            w_bridge(buff, st_vref, st_v0, norm_i, index)
            w_normalize_or_copy(
                buff, st_v0, norm_i, st_v1.pos_x, index, "value"
            )
            if term_i:
                w_close(buff, st_v1.fmt, norm_i, index)
            if write_tr:
                if write_ld and not term_i:
                    st_xref = st_x0.copy()
                w_bridge(buff, st_xref, st_x1, norm_i, index)
                trail = st_x1.ensure_bytes()
                buff.extend(trail[st_x1.pos_x :])
            if carry_on:
                st_xlast.become(st_x1)
                read_all(st_xlast, index, "x")
                st_vlast.become(st_v1)
                read_all(st_vlast, index, "value")
            out[index] = _decode(buff)
        else:
            out[index] = text
    return out


def _reject_carry_string(carry):
    probe = carry
    if isinstance(probe, (list, tuple)):
        if len(probe) == 1:
            probe = probe[0]
    if isinstance(probe, str):
        raise FansiError("Argument `carry` must be TRUE or FALSE in replacement mode.")


def _check_tab_stops(tab_stops):
    """Validate tab stops here. prepare() rebinds its stop argument in that loop."""
    stops = tab_stops if isinstance(tab_stops, (list, tuple)) else [tab_stops]
    if not stops:
        raise FansiError(
            "Argument `tab.stops` must be numeric, strictly positive, and "
            "representable as an integer."
        )
    converted = []
    for item in stops:
        if isinstance(item, bool) or not isinstance(item, (int, float)):
            raise FansiError(
                "Argument `tab.stops` must be numeric, strictly positive, and "
                "representable as an integer."
            )
        if isinstance(item, float) and item != item:
            raise FansiError(
                "Argument `tab.stops` must be numeric, strictly positive, and "
                "representable as an integer."
            )
        if item < 1:
            raise FansiError(
                "Argument `tab.stops` must be numeric, strictly positive, and "
                "representable as an integer."
            )
        converted.append(int(item))
    return converted


def _resolve_common(
    x,
    start,
    stop,
    type,
    round,
    tabs_as_spaces,
    tab_stops,
    warn,
    term_cap,
    ctl,
    normalize,
    carry,
    terminate,
):
    warn = resolve_warn(warn, _MISSING)
    if term_cap is _MISSING:
        term_cap = option("fansi.term.cap", dflt_term_cap())
    if normalize is _MISSING:
        normalize = option("fansi.normalize", False)
    if carry is _MISSING:
        carry = option("fansi.carry", False)
    if terminate is _MISSING:
        terminate = option("fansi.terminate", True)
    if tabs_as_spaces is _MISSING:
        tabs_as_spaces = option("fansi.tabs.as.spaces", False)
    if tab_stops is _MISSING:
        tab_stops = option("fansi.tab.stops", 8)
    texts = coerce_texts(x)
    start_i = as_integer_vector(start, "start")
    stop_i = as_integer_vector(stop, "stop")
    checked = prepare(
        x=texts,
        start=start_i,
        stop=stop_i,
        type_=type,
        round_=round,
        tabs_as_spaces=tabs_as_spaces,
        warn=warn,
        term_cap=term_cap,
        ctl=ctl,
        normalize=normalize,
        carry=carry,
        terminate=terminate,
        coerce_x=False,
    )
    checked["tab_stops"] = _check_tab_stops(tab_stops)
    return texts, checked


def _run_extract(texts, checked):
    if not texts:
        return []
    if checked["tabs_as_spaces"]:
        texts = tabs_as_spaces(
            texts, checked["tab_stops"], checked["term_cap_int"], checked["ctl_int"]
        )
    state = state_init_full(
        texts,
        checked["warn_int"],
        checked["term_cap_int"],
        False,
        False,
        checked["type_int"],
        checked["ctl_int"],
        0,
    )
    return substr_extract(
        texts,
        checked["start"],
        checked["stop"],
        checked["carry"],
        state,
        checked["round_int"],
        checked["normalize"],
        checked["terminate"],
    )


def _recycle_values(values, length):
    if length == 0:
        return []
    if not values:
        raise FansiError("invalid 'length.out' argument")
    return [values[i % len(values)] for i in range(length)]


def _run_replace(texts, values, checked):
    if not texts:
        return []
    values = coerce_texts(values)
    if checked["tabs_as_spaces"]:
        values = tabs_as_spaces(
            values, checked["tab_stops"], checked["term_cap_int"], checked["ctl_int"]
        )
    values = _recycle_values(values, len(texts))
    state = state_init_full(
        texts,
        checked["warn_int"],
        checked["term_cap_int"],
        False,
        False,
        checked["type_int"],
        checked["ctl_int"],
        0,
    )
    return substr_replace(
        texts,
        checked["start"],
        checked["stop"],
        values,
        checked["carry"],
        state,
        checked["round_int"],
        checked["normalize"],
        checked["terminate"],
    )


def substr2_ctl(
    x,
    start,
    stop,
    type="chars",
    round="start",
    tabs_as_spaces=_MISSING,
    tab_stops=_MISSING,
    warn=_MISSING,
    term_cap=_MISSING,
    ctl="all",
    normalize=_MISSING,
    carry=_MISSING,
    terminate=_MISSING,
):
    """Substring by characters, display width, or graphemes, keeping active state."""
    texts, checked = _resolve_common(
        x,
        start,
        stop,
        type,
        round,
        tabs_as_spaces,
        tab_stops,
        warn,
        term_cap,
        ctl,
        normalize,
        carry,
        terminate,
    )
    return _run_extract(texts, checked)


def substr_ctl(
    x,
    start,
    stop,
    warn=_MISSING,
    term_cap=_MISSING,
    ctl="all",
    normalize=_MISSING,
    carry=_MISSING,
    terminate=_MISSING,
):
    """Substring by character position. Active SGR and URLs are re-opened."""
    return substr2_ctl(
        x,
        start,
        stop,
        type="chars",
        round="start",
        warn=warn,
        term_cap=term_cap,
        ctl=ctl,
        normalize=normalize,
        carry=carry,
        terminate=terminate,
    )


def substr2_sgr(
    x,
    start,
    stop,
    type="chars",
    round="start",
    tabs_as_spaces=_MISSING,
    tab_stops=_MISSING,
    warn=_MISSING,
    term_cap=_MISSING,
    normalize=_MISSING,
    carry=_MISSING,
    terminate=_MISSING,
):
    """substr2_ctl that treats SGR and OSC hyperlinks as the special controls."""
    return substr2_ctl(
        x,
        start,
        stop,
        type=type,
        round=round,
        tabs_as_spaces=tabs_as_spaces,
        tab_stops=tab_stops,
        warn=warn,
        term_cap=term_cap,
        ctl=["sgr", "url"],
        normalize=normalize,
        carry=carry,
        terminate=terminate,
    )


def substr_sgr(
    x,
    start,
    stop,
    warn=_MISSING,
    term_cap=_MISSING,
    normalize=_MISSING,
    carry=_MISSING,
    terminate=_MISSING,
):
    """substr_ctl that treats only SGR sequences as special."""
    return substr2_ctl(
        x,
        start,
        stop,
        warn=warn,
        term_cap=term_cap,
        ctl="sgr",
        normalize=normalize,
        carry=carry,
        terminate=terminate,
    )


def substr2_ctl_replace(
    x,
    start,
    stop,
    value,
    type="chars",
    round="start",
    tabs_as_spaces=_MISSING,
    tab_stops=_MISSING,
    warn=_MISSING,
    term_cap=_MISSING,
    ctl="all",
    normalize=_MISSING,
    carry=_MISSING,
    terminate=_MISSING,
):
    """Replace the substring. `terminate` only affects the splice boundaries."""
    if carry is not _MISSING:
        _reject_carry_string(carry)
    texts, checked = _resolve_common(
        x,
        start,
        stop,
        type,
        round,
        tabs_as_spaces,
        tab_stops,
        warn,
        term_cap,
        ctl,
        normalize,
        carry,
        terminate,
    )
    return _run_replace(texts, value, checked)


def substr_ctl_replace(
    x,
    start,
    stop,
    value,
    warn=_MISSING,
    term_cap=_MISSING,
    ctl="all",
    normalize=_MISSING,
    carry=_MISSING,
    terminate=_MISSING,
):
    """Replace a character range. The result reads as x edited between the bounds."""
    return substr2_ctl_replace(
        x,
        start,
        stop,
        value,
        warn=warn,
        term_cap=term_cap,
        ctl=ctl,
        normalize=normalize,
        carry=carry,
        terminate=terminate,
    )
