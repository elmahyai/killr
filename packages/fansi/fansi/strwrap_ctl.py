"""Control-aware strwrap, from fansi src/wrap.c, src/write.c, and R/strwrap.R.

strtrim calls the same wrap routine with a hard cut and the first line only.
SGR and URL bytes written here follow src/write.c. Normalization, when asked
for, is a second pass, the way the R wrappers call normalize_state.
"""

from __future__ import annotations

from fansi._args import FansiError, option, prepare
from fansi._const import (
    BRD_ENCIRC,
    BRD_FRAMED,
    BRD_OVERLN,
    CLR_256,
    CLR_8,
    CLR_BRIGHT,
    CLR_TRU,
    CTL_ALL,
    FONT_ALL,
    FONT_START,
    IDG_MASK,
    IDG_OVERL,
    IDG_OVERL2,
    IDG_STRESS,
    IDG_UNDERL,
    IDG_UNDERL2,
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
    WARN_ERROR,
    WARN_MASK,
    get_range,
)
from fansi._read import coerce_texts, read_all, read_next, resolve_warn
from fansi._state import (
    INT_MAX,
    Format,
    Sgr,
    reset_state,
    state_init_full,
    state_reinit,
)
from fansi.simple import dflt_term_cap
from fansi.tabs_as_spaces import expand_tabs

_MISSING = object()
FONT_MASK = FONT_ALL << FONT_START
CLR_MASK = 240


class _Buff:
    """Bytes written by the measure/write helpers. One pass is enough here."""

    def __init__(self):
        self.chunks = []

    def copy(self, text):
        data = text.encode("ascii") if isinstance(text, str) else bytes(text)
        if data:
            self.chunks.append(data)

    def mcopy(self, data, count):
        if count:
            self.chunks.append(bytes(data[:count]))

    def fill(self, byte, times):
        if times > 0:
            self.chunks.append(bytes([byte]) * times)

    def replace_last(self, byte):
        for index in range(len(self.chunks) - 1, -1, -1):
            chunk = self.chunks[index]
            if chunk:
                last = bytearray(chunk)
                last[-1] = byte
                self.chunks[index] = bytes(last)
                return

    def value(self):
        return b"".join(self.chunks)


class _Prefix:
    def __init__(self, string, width, nbytes, indent, utf8):
        self.string = string
        self.width = width
        self.bytes = nbytes
        self.indent = indent
        self.utf8 = utf8

    def copy(self):
        return _Prefix(self.string, self.width, self.bytes, self.indent, self.utf8)


def _decode(data):
    return bytes(data).decode("utf-8", "surrogateescape")


def _at(data, index):
    if data is None or index < 0 or index >= len(data):
        return 0
    return data[index]


def _sgr_active(sgr):
    return bool(sgr.style or sgr.color.x or sgr.bgcol.x)


def _url_len(url):
    return url.url.len if url is not None else 0


def _id_len(url):
    return url.id.len if url is not None else 0


def _slice(url, offset):
    if url.string is None or offset.len <= 0:
        return b""
    return bytes(url.string[offset.start:offset.start + offset.len])


def _url_active(url):
    return _url_len(url) > 0


def _color_diff(target, current):
    tclr = target.x
    c256 = tclr & (CLR_256 | CLR_TRU)
    ctru = tclr & CLR_TRU
    return (
        tclr != current.x
        or (c256 and target.extra[0] != current.extra[0])
        or (ctru and target.extra[1] != current.extra[1])
        or (ctru and target.extra[2] != current.extra[2])
    )


def _sgr_setdiff(old, new, mode):
    """Styles in `old` that `new` does not already have."""
    res = Sgr()
    if (not mode and _color_diff(old.color, new.color)) or (
        mode and old.color.x and not new.color.x
    ):
        res.color.x = old.color.x
        res.color.extra = list(old.color.extra)
    if (not mode and _color_diff(old.bgcol, new.bgcol)) or (
        mode and old.bgcol.x and not new.bgcol.x
    ):
        res.bgcol.x = old.bgcol.x
        res.bgcol.extra = list(old.bgcol.extra)
    font_old = old.style & FONT_MASK
    font_new = new.style & FONT_MASK
    if (not mode and font_old != font_new) or (mode and font_old and not font_new):
        res.style = font_old
    style_old = old.style & ~FONT_MASK
    style_new = new.style & ~FONT_MASK
    res.style |= style_old & ~style_new
    return res


def _sgr_intersect(old, new):
    """Styles present in both. Font bits stay clear, as in src/state.c."""
    res = Sgr()
    if old.color.x == new.color.x:
        res.color.x = new.color.x
        res.color.extra = list(new.color.extra)
    if old.bgcol.x == new.bgcol.x:
        res.bgcol.x = new.bgcol.x
        res.bgcol.extra = list(new.bgcol.extra)
    style_old = old.style & ~FONT_MASK
    style_new = new.style & ~FONT_MASK
    res.style |= style_old & style_new
    return res


def _url_diff(target, current):
    target_url = _slice(target, target.url)
    current_url = _slice(current, current.url)
    target_id = _slice(target, target.id)
    current_id = _slice(current, current.id)
    url_eq = len(target_url) == len(current_url) and (not target_url or target_url == current_url)
    id_eq = len(target_id) == len(current_id) and (
        (not target_url and not target_id) or (target_id and target_id == current_id)
    )
    return not (url_eq and id_eq)


def _token(value, normalize):
    if normalize:
        return f"\033[{value}m".encode("ascii")
    return f"{value};".encode("ascii")


def _color_token(color, mode, normalize):
    pieces = []
    if normalize:
        pieces.append(b"\033[")
    clrval = color.x & ~CLR_MASK
    if (color.x & CLR_MASK) == CLR_BRIGHT:
        if mode == 3:
            pieces.append(b"9")
        else:
            pieces.append(b"10")
        pieces.append(bytes([ord("0") + clrval]))
    else:
        pieces.append(bytes([ord("0") + mode, ord("0") + clrval]))
        if color.x & (CLR_256 | CLR_TRU):
            if color.x & CLR_TRU:
                body = f"2;{color.extra[0]};{color.extra[1]};{color.extra[2]}"
            else:
                body = f"5;{color.extra[0]}"
            pieces.append(b";" + body.encode("ascii"))
        elif not (color.x & CLR_8):
            raise FansiError("Internal Error: unexpected color mode.")
    pieces.append(b"m" if normalize else b";")
    return b"".join(pieces)


def _w_sgr(buff, sgr, normalize, enclose):
    """Write one SGR state. Order matches FANSI_W_sgr."""
    if not _sgr_active(sgr):
        return
    if not normalize and enclose:
        buff.copy(b"\033[")
    style = sgr.style
    if style & STL_BOLD:
        buff.copy(_token("1", normalize))
    if style & STL_BLUR:
        buff.copy(_token("2", normalize))
    if style & STL_ITALIC:
        buff.copy(_token("3", normalize))
    if style & STL_UNDER:
        buff.copy(_token("4", normalize))
    if style & STL_BLINK1:
        buff.copy(_token("5", normalize))
    if style & STL_BLINK2:
        buff.copy(_token("6", normalize))
    if style & STL_INVERT:
        buff.copy(_token("7", normalize))
    if style & STL_CONCEAL:
        buff.copy(_token("8", normalize))
    if style & STL_CROSSOUT:
        buff.copy(_token("9", normalize))
    if style & STL_FRAKTUR:
        buff.copy(_token("20", normalize))
    if style & STL_UNDER2:
        buff.copy(_token("21", normalize))
    if style & STL_PROPSPC:
        buff.copy(_token("26", normalize))
    if sgr.color.x:
        buff.copy(_color_token(sgr.color, 3, normalize))
    if sgr.bgcol.x:
        buff.copy(_color_token(sgr.bgcol, 4, normalize))
    if style & BRD_FRAMED:
        buff.copy(_token("51", normalize))
    if style & BRD_ENCIRC:
        buff.copy(_token("52", normalize))
    if style & BRD_OVERLN:
        buff.copy(_token("53", normalize))
    if style & IDG_UNDERL:
        buff.copy(_token("60", normalize))
    if style & IDG_UNDERL2:
        buff.copy(_token("61", normalize))
    if style & IDG_OVERL:
        buff.copy(_token("62", normalize))
    if style & IDG_OVERL2:
        buff.copy(_token("63", normalize))
    if style & IDG_STRESS:
        buff.copy(_token("64", normalize))
    font = get_range(style, FONT_START, FONT_ALL)
    if font:
        tok = bytearray(b"10")
        tok[1] = ord("0") + (font % 10)
        buff.copy(_token(tok.decode("ascii"), normalize))
    if enclose:
        buff.replace_last(ord("m"))


def _w_sgr_close(buff, sgr, normalize):
    if not _sgr_active(sgr):
        return
    if not normalize:
        buff.copy(b"\033[0m")
        return
    style = sgr.style
    if style & FONT_MASK:
        style &= ~FONT_MASK
        buff.copy(b"\033[10m")
    groups = (
        (STL_BOLD | STL_BLUR, b"\033[22m"),
        (STL_ITALIC | STL_FRAKTUR, b"\033[23m"),
        (STL_UNDER | STL_UNDER2, b"\033[24m"),
        (STL_BLINK1 | STL_BLINK2, b"\033[25m"),
        (STL_INVERT, b"\033[27m"),
        (STL_CONCEAL, b"\033[28m"),
        (STL_CROSSOUT, b"\033[29m"),
    )
    for mask, code in groups:
        if style & mask:
            style &= ~mask
            buff.copy(code)
    if sgr.color.x:
        buff.copy(b"\033[39m")
    if sgr.bgcol.x:
        buff.copy(b"\033[49m")
    if style & STL_PROPSPC:
        style &= ~STL_PROPSPC
        buff.copy(b"\033[50m")
    if style & (BRD_FRAMED | BRD_ENCIRC):
        style &= ~(BRD_FRAMED | BRD_ENCIRC)
        buff.copy(b"\033[54m")
    if style & BRD_OVERLN:
        style &= ~BRD_OVERLN
        buff.copy(b"\033[55m")
    if style & IDG_MASK:
        buff.copy(b"\033[65m")


def _w_url(buff, url):
    if not _url_active(url):
        return
    buff.copy(b"\033]8;")
    if _id_len(url):
        buff.copy(b"id=")
        buff.copy(_slice(url, url.id))
    buff.copy(b";")
    buff.copy(_slice(url, url.url))
    buff.copy(b"\033\\")


def _w_url_close(buff, url):
    if _url_active(url):
        buff.copy(b"\033]8;;\033\\")


def _w_close(buff, fmt, normalize):
    _w_sgr_close(buff, fmt.sgr, normalize)
    _w_url_close(buff, fmt.url)


def _w_bridge(buff, end, restart, normalize):
    """Sequences that take `end` to `restart`."""
    to_close = _sgr_setdiff(end.fmt.sgr, restart.fmt.sgr, not normalize)
    to_open = _sgr_setdiff(restart.fmt.sgr, end.fmt.sgr, not normalize)
    if not normalize:
        renew = _sgr_intersect(end.fmt.sgr, restart.fmt.sgr)
        active_open = _sgr_active(to_open)
        active_close = _sgr_active(to_close)
        if active_open and active_close:
            buff.copy(b"\033[0;")
            _w_sgr(buff, renew, normalize, False)
            _w_sgr(buff, to_open, normalize, False)
            buff.replace_last(ord("m"))
        elif active_close:
            buff.copy(b"\033[0;")
            _w_sgr(buff, renew, normalize, False)
            buff.replace_last(ord("m"))
        else:
            opened = _sgr_setdiff(restart.fmt.sgr, end.fmt.sgr, 0)
            _w_sgr(buff, opened, normalize, True)
    else:
        _w_sgr_close(buff, to_close, normalize)
        _w_sgr(buff, to_open, normalize, True)
    if _url_diff(end.fmt.url, restart.fmt.url):
        if not _url_active(restart.fmt.url):
            _w_url_close(buff, end.fmt.url)
        _w_url(buff, restart.fmt.url)


def _w_normalize(buff, state, stop, index, arg):
    """Rewrite specials between here and `stop`. Return whether any were rewritten."""
    state_int = state.copy()
    string_last = state_int.pos_x
    any_to_exp = False
    data = state_int.string
    while True:
        found = data.find(b"\x1b", state_int.pos_x)
        if found < 0 or found >= stop:
            if any_to_exp:
                buff.mcopy(data[string_last:], stop - string_last)
            break
        state_prev = state_int.copy()
        state_int.pos_x = found
        read_next(state_int, index, arg)
        if state_int.status & STAT_SPECIAL:
            any_to_exp = True
            buff.mcopy(data[string_last:], found - string_last)
            _w_bridge(buff, state_prev, state_int, True)
            string_last = state_int.pos_x
        if state_int.pos_x < found:
            break
    state.become(state_int)
    return any_to_exp


def _normalize_vector(texts, warn_int, term_cap_int, carry):
    """normalize_state on one character vector. Missing strings stay missing."""
    do_carry, carry_state = _carry_init(carry, warn_int, term_cap_int, [1])
    out = list(texts)
    any_na = False
    state = None
    for index, text in enumerate(texts):
        if text is None or (any_na and do_carry):
            any_na = True
            out[index] = None
            continue
        if state is None:
            state = state_init_full(
                texts, warn_int, term_cap_int, True, False, 0, [1], index
            )
        else:
            state_reinit(state, texts, index)
        if do_carry:
            state.fmt.sgr = carry_state.fmt.sgr.copy()
            state.fmt.url = carry_state.fmt.url.copy()
        start = state.copy()
        buff = _Buff()
        changed = _w_normalize(buff, state, len(start.string), index, "x")
        carry_state.fmt.sgr = state.fmt.sgr.copy()
        carry_state.fmt.url = state.fmt.url.copy()
        if changed:
            out[index] = _decode(buff.value())
    return out


def _carry_init(carry, warn_int, term_cap_int, ctl_int):
    """Read a carry string. None means carry is off."""
    if carry is None:
        blank = state_init_full([""], warn_int, term_cap_int, True, True, 0, ctl_int, 0)
        return False, blank
    text = "" if carry is True else carry
    state = state_init_full([text], warn_int, term_cap_int, True, True, 0, ctl_int, 0)
    read_all(state, 0, "carry")
    return True, state


def _is_special_byte(byte):
    return byte not in (0x09, 0x0A) and 0 < byte < 0x20


def _process_spaces(texts, term_cap_int, ctl_int):
    """Collapse whitespace the way base::strwrap does, keeping controls."""
    out = list(texts)
    state = None
    for index, text in enumerate(texts):
        if text is None:
            continue
        if state is None:
            state = state_init_full(
                texts, 0, term_cap_int, True, True, 0, ctl_int, index
            )
        else:
            state_reinit(state, texts, index)
        data = state.string
        length = len(data)
        buff = bytearray()
        strip_this = False
        to_strip = 0
        to_strip_nl = 0
        punct_prev = 0
        punct_prev_prev = 0
        space_prev = 0
        space_start = 0
        newlines = 0
        newlines_start = 0
        has_tab_or_nl = 0
        leading_spaces = 1
        para_start = 1
        string_start = 0
        j_last = 0
        j = 0
        while j <= length:
            byte = _at(data, j)
            newline = byte == 0x0A
            tab = byte == 0x09
            has_tab_or_nl += int(newline) + int(tab)
            if newline:
                if not newlines:
                    newlines_start = j
                    to_strip_nl = to_strip
                newlines += 1
            space = byte in (0x20, 0x09, 0x0A)
            line_end = byte == 0
            if space and not para_start:
                if not space_prev:
                    space_start = 1
                elif punct_prev_prev:
                    space_start = 2
            special = _is_special_byte(byte)
            special_len = 0
            if special:
                pos_prev = j
                state.pos_x = j
                read_next(state, index, "x")
                if state.status & CTL_ALL:
                    special_len = state.pos_x - pos_prev
                else:
                    special = False
                    special_len = 0
            transcribe = (
                not space
                and not special
                and (
                    (to_strip and leading_spaces)
                    or (to_strip > 1 and not punct_prev)
                    or to_strip > 2
                    or has_tab_or_nl
                )
            ) or (line_end and (strip_this or space_start))
            reset = 0
            if transcribe:
                if not strip_this:
                    strip_this = True
                copy_to = j
                to_strip0 = to_strip
                spc = b" "
                if newlines > 1:
                    copy_to = newlines_start
                    space_start = 2
                    to_strip = to_strip_nl
                    spc = b"\n"
                copy_bytes = copy_to - j_last - to_strip
                if copy_bytes:
                    buff.extend(data[string_start:string_start + copy_bytes])
                if not line_end:
                    if space_start:
                        buff.extend(spc)
                    if space_start > 1:
                        buff.extend(spc)
                copy_end = j_last + copy_bytes
                k = copy_end
                limit = copy_end + to_strip0
                while k < limit:
                    if _is_special_byte(_at(data, k)):
                        state.pos_x = k
                        read_next(state, index, "x")
                        nbytes = state.pos_x - k
                        buff.extend(data[k:k + nbytes])
                        k += nbytes - 1
                    k += 1
                string_start = j
                j_last = j
                reset = 1
            elif space:
                to_strip += 1
            elif special:
                if space_prev:
                    to_strip += special_len
                    space = 1
                j += special_len - 1
            else:
                reset = 1
            if reset:
                to_strip = 0
                space_start = 0
                newlines = 0
                has_tab_or_nl = 0
                leading_spaces = 0
            para_start = newlines > 1
            space_prev = space
            punct_prev_prev = punct_prev or (special and punct_prev_prev)
            punct_prev = byte in (ord("."), ord("!"), ord("?")) or (
                punct_prev and byte in (ord('"'), ord("'"), ord(")"))
            )
            j += 1
        if strip_this:
            out[index] = _decode(buff)
    return out


def _make_pre(text, warn_int, term_cap_int, ctl_int, arg):
    state = state_init_full([text], warn_int, term_cap_int, False, True, 1, ctl_int, 0)
    read_all(state, 0, arg)
    return _Prefix(state.string, state.pos_w, state.pos_x, 0, state.utf8)


def _pad_pre(dat, spaces):
    body = dat.string[:dat.bytes] + b" " * spaces
    return _Prefix(
        body,
        dat.width + spaces,
        dat.bytes + spaces,
        dat.indent + spaces,
        dat.utf8,
    )


def _drop_indent(dat):
    other = dat.copy()
    other.bytes -= other.indent
    other.width -= other.indent
    other.indent = 0
    if other.bytes < 0:
        raise FansiError(
            "Internal Error: cannot drop indent when there is none; contact maintainer."
        )
    return other


def _writeline(state_bound, state_start, state_last, pre, tar_width, pad_byte, terminate):
    normalize = 0
    line_width = state_bound.pos_w - state_start.pos_w
    if tar_width < 0:
        tar_width = 0
    target_pad = 0
    if line_width <= tar_width and pad_byte:
        target_pad = tar_width - line_width
    if state_bound.pos_x == state_start.pos_x:
        pre = _drop_indent(pre)
        if not target_pad and terminate:
            state_start = state_start.copy()
            state_bound = state_bound.copy()
            state_start.fmt = Format()
            state_bound.fmt = Format()
    if state_bound.pos_x < state_start.pos_x or state_bound.pos_w < state_start.pos_w:
        raise FansiError("Internal Error: boundary leading position; contact maintainer.")
    buff = _Buff()
    _w_bridge(buff, state_last, state_start, normalize)
    if pre.bytes:
        buff.mcopy(pre.string, pre.bytes)
    buff.mcopy(state_start.string[state_start.pos_x:], state_bound.pos_x - state_start.pos_x)
    if pad_byte and target_pad:
        buff.fill(pad_byte, target_pad)
    if terminate:
        _w_close(buff, state_bound.fmt, normalize)
    return _decode(buff.value())


def _wrap_element(
    state,
    width,
    pre_first,
    pre_next,
    wrap_always,
    pad_byte,
    strip_spaces,
    first_only,
    index,
    do_carry,
    carry_state,
    terminate,
):
    width_1 = width - pre_first.width
    width_2 = width - pre_next.width
    width_tar = width_1
    if width < 1 and wrap_always:
        raise FansiError("Internal Error: invalid width.")
    if wrap_always and (width_1 < 0 or width_2 < 0):
        raise FansiError("Internal Error: incompatible width/indent/prefix.")
    lines = []
    prev_boundary = 0
    has_boundary = 0
    para_start = 1
    first_line = 1
    last_start = 0
    new_line = 1
    if do_carry:
        state.fmt.sgr = carry_state.fmt.sgr.copy()
        state.fmt.url = carry_state.fmt.url.copy()
    state_start = state.copy()
    state_last = state.copy()
    if terminate:
        reset_state(state_last)
    state_tmp = state.copy()
    read_next(state_tmp, index, "x")
    if state_tmp.status & STAT_SPECIAL:
        state_start = state_tmp
    else:
        state_start.status |= state_tmp.status & STAT_WARNED
    state_bound = state_start.copy()
    state_prev = state_start.copy()
    state = state_start.copy()
    while True:
        if new_line:
            new_line = 0
            while (state_bound.at(state_bound.pos_x) == 0x20 and strip_spaces) or (
                state_bound.at(state_bound.pos_x) == 0x1B
            ):
                state_tmp = state_bound.copy()
                read_next(state_tmp, index, "x")
                if state_bound.at(state_bound.pos_x) == 0x1B and not (
                    state_tmp.status & STAT_SPECIAL
                ):
                    state_bound.status |= state_tmp.status & STAT_WARNED
                    break
                state_bound = state_tmp
            has_boundary = 0
            state_bound.pos_w = 0
            state = state_bound.copy()
            state_prev = state_bound.copy()
            state_start = state_bound.copy()
        end = state.at(state.pos_x) == 0
        state_next = state.copy()
        if not end:
            read_next(state_next, index, "x")
        if state_next.status & STAT_WARNED:
            state.status |= STAT_WARNED
            state_bound.status |= STAT_WARNED
        strip_trail = (
            bool(state.status & STAT_SPECIAL)
            and (not end or terminate)
            and not (pad_byte and state.pos_w < width_tar)
        )
        current = state.at(state.pos_x)
        if current in (0x20, 0x09, 0x0A):
            if strip_spaces and not prev_boundary:
                state_bound = state_prev.copy() if strip_trail else state.copy()
            elif not strip_spaces:
                state_bound = state.copy()
            has_boundary = 1
            prev_boundary = 1
        else:
            if (not has_boundary) and state.pos_w == width_tar and strip_trail:
                state_bound = state_prev.copy()
            prev_boundary = 0
        overshoot = state.pos_w > width_tar or (
            state.pos_w == width_tar and state_next.pos_w > state.pos_w
        )
        if (
            end
            or (current == 0x0A and not first_only)
            or (overshoot and (has_boundary or wrap_always))
        ):
            if end or (wrap_always and not has_boundary) or first_only:
                if wrap_always and not has_boundary:
                    if state.pos_w > width_tar:
                        state = state_prev.copy()
                        end = False
                    elif state.pos_w == width_tar and strip_trail:
                        state = state_prev.copy()
                elif end and strip_trail:
                    state = state_prev.copy()
                state_bound = state.copy()
            if not first_line and last_start >= state_start.pos_x:
                raise FansiError(
                    "Wrap error: trying to wrap to width narrower than "
                    "character width; set `wrap.always=FALSE` to resolve."
                )
            if (
                not strip_spaces
                and has_boundary
                and state_bound.at(state_bound.pos_x) in (0x20, 0x09)
                and state_bound.pos_x < state.pos_x
            ):
                read_next(state_bound, index, "x")
            lines.append(
                _writeline(
                    state_bound,
                    state_start,
                    state_last,
                    pre_first if para_start else pre_next,
                    width_tar,
                    pad_byte,
                    terminate,
                )
            )
            first_line = 0
            last_start = state_start.pos_x
            if not terminate:
                state_last = state_bound.copy()
            if first_only:
                if do_carry:
                    read_all(state, index, "x")
                break
            if end:
                break
            para_start = state.at(state.pos_x) == 0x0A
            width_tar = width_1 if para_start else width_2
            if has_boundary and para_start:
                while True:
                    read_next(state_bound, index, "x")
                    if not (state_bound.status & STAT_SPECIAL):
                        break
            elif not has_boundary:
                state_bound = state.copy()
            new_line = 1
        else:
            state_prev = state.copy()
            state = state_next
    carry_state.fmt.sgr = state.fmt.sgr.copy()
    carry_state.fmt.url = state.fmt.url.copy()
    if first_only:
        return lines[0] if lines else ""
    return lines


def strwrap_csi(
    texts,
    width,
    indent,
    exdent,
    prefix,
    initial,
    wrap_always,
    pad_end,
    strip_spaces,
    use_tabs,
    tab_stops,
    warn_int,
    term_cap_int,
    first_only,
    ctl_int,
    normalize,
    carry,
    terminate,
):
    """FANSI_strwrap_csi. `width` is already the integer the C routine receives."""
    if pad_end and (pad_end[0] < 0x20 or pad_end[0] > 0x7E):
        raise FansiError(
            "Argument `pad.end` must be an empty string or a single "
            "printable ASCII character."
        )
    pre_raw = _make_pre(prefix, warn_int, term_cap_int, ctl_int, "prefix")
    if initial != prefix:
        ini_raw = _make_pre(initial, warn_int, term_cap_int, ctl_int, "initial")
    else:
        ini_raw = pre_raw
    ini_first = _pad_pre(ini_raw, indent)
    if initial != prefix:
        pre_first = _pad_pre(pre_raw, indent)
    else:
        pre_first = ini_first
    if indent != exdent:
        pre_next = _pad_pre(pre_raw, exdent)
    else:
        pre_next = pre_first
    work = list(texts)
    if strip_spaces:
        work = _process_spaces(work, term_cap_int, ctl_int)
    if use_tabs:
        work = expand_tabs(work, tab_stops, warn_int, term_cap_int, ctl_int)
    if wrap_always and (
        ini_first.width >= width or pre_first.width >= width or pre_next.width >= width
    ):
        raise FansiError(
            "Width error: sum of `indent` and `initial` width or sum of `exdent` "
            "and `prefix` width must be less than `width - 1` when in `wrap.always`."
        )
    do_carry, carry_state = _carry_init(carry, warn_int, term_cap_int, ctl_int)
    # A carried state is read with character width. The wrap itself measures display width.
    carry_state_wrap = carry_state
    any_na = False
    result = []
    state = None
    pad_byte = pad_end[0] if pad_end else 0
    for index, text in enumerate(work):
        if first_only and (text is None or (do_carry and any_na)):
            any_na = True
            result.append(None)
            continue
        element = "NA" if text is None else text
        vector = work
        if text is None:
            vector = list(work)
            vector[index] = "NA"
        if state is None or text is None:
            state = state_init_full(
                vector, warn_int, term_cap_int, True, True, 1, ctl_int, index
            )
        else:
            state_reinit(state, vector, index)
        piece = _wrap_element(
            state,
            width,
            ini_first if index == 0 else pre_first,
            pre_next,
            wrap_always,
            pad_byte,
            strip_spaces,
            first_only,
            index,
            do_carry,
            carry_state_wrap,
            terminate,
        )
        result.append(piece)
    return result


def _logical_flag(value, name):
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if isinstance(value, float) and value != value:
            return None
        if value == 0:
            return False
        if value == 1:
            return True
        return None
    if isinstance(value, str) and value in ("TRUE", "FALSE"):
        return value == "TRUE"
    if value is None:
        return None
    raise FansiError(f"Argument `{name}` must be TRUE or FALSE.")


def _require_flag(value, name):
    flag = _logical_flag(value, name)
    if flag is None:
        raise FansiError(f"Argument `{name}` must be TRUE or FALSE.")
    return flag


def _numeric_values(value):
    if isinstance(value, bool) or isinstance(value, (int, float)):
        return [value]
    if isinstance(value, (list, tuple)) and value and not isinstance(value, str):
        return list(value)
    return None


def _wrap_width(value):
    values = _numeric_values(value)
    if values is None:
        raise FansiError("Argument `width` must be numeric.")
    numbers = []
    for item in values:
        if isinstance(item, bool) or not isinstance(item, (int, float)):
            raise FansiError("Argument `width` must be numeric.")
        if isinstance(item, float) and (item != item or abs(item) == float("inf")):
            raise FansiError(
                "Argument `width` must be a positive scalar numeric representable as integer."
            )
        numbers.append(item)
    smallest = min(numbers)
    adjusted = int(min(max(smallest, 2), INT_MAX))
    if adjusted <= 0:
        raise FansiError(
            "Argument `width` must be a positive scalar numeric representable as integer."
        )
    return adjusted - 1


def _nonneg_int(value, name):
    values = _numeric_values(value)
    if values is None or len(values) != 1:
        raise FansiError(
            f"Argument `{name}` must be a positive scalar numeric representable as integer."
        )
    item = values[0]
    if isinstance(item, bool):
        item = int(item)
    if not isinstance(item, (int, float)) or (
        isinstance(item, float) and (item != item or abs(item) == float("inf"))
    ):
        raise FansiError(
            f"Argument `{name}` must be a positive scalar numeric representable as integer."
        )
    item = int(item)
    if item < 0 or item > INT_MAX:
        raise FansiError(
            f"Argument `{name}` must be a positive scalar numeric representable as integer."
        )
    return item


def _scalar_text(value, name):
    """One character. A missing string is the bytes of NA, as CHAR(NA_STRING) is."""
    if isinstance(value, bytes):
        value = value.decode("utf-8", "surrogateescape")
    if isinstance(value, str):
        return value
    if isinstance(value, (list, tuple)):
        if len(value) != 1:
            raise FansiError(f"Argument `{name}` must be a scalar character.")
        value = value[0]
        if isinstance(value, bytes):
            value = value.decode("utf-8", "surrogateescape")
        if isinstance(value, str):
            return value
        if value is None:
            return "NA"
    if value is None:
        return "NA"
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    if isinstance(value, float):
        if value != value:
            return "NA"
        return str(int(value)) if value.is_integer() else str(value)
    raise FansiError(f"Argument `{name}` must be a scalar character.")


def _pad_byte(value):
    text = _scalar_text(value, "pad.end")
    raw = text.encode("utf-8", "surrogateescape")
    if len(raw) > 1:
        raise FansiError("Argument `pad.end` must be at most one byte long.")
    return raw


def _option_flag(value, missing, key, default):
    if value is missing:
        value = option(key, default)
    return value


def _prepare_common(texts, warn, term_cap, ctl, normalize, carry, terminate, extra):
    checked = prepare(
        x=texts,
        warn=warn,
        term_cap=term_cap,
        ctl=ctl,
        normalize=normalize,
        carry=carry,
        terminate=terminate,
        warn_mask=WARN_MASK,
        coerce_x=False,
        **extra,
    )
    return checked


def _after_wrap(pieces, simplify, normalize, term_cap, carry, term_cap_int):
    if simplify:
        flat = []
        for piece in pieces:
            if isinstance(piece, list):
                flat.extend(piece)
            else:
                flat.append(piece)
        if normalize:
            # The flat call does not receive the wrap carry. warn is forced off.
            off = WARN_MASK & WARN_ERROR
            return _normalize_vector(flat, off, term_cap_int, None)
        return flat
    if normalize:
        out = []
        for piece in pieces:
            if isinstance(piece, list):
                out.append(_normalize_vector(piece, 0, term_cap_int, carry))
            else:
                out.append(piece)
        return out
    return pieces


def _run_wrap(
    x,
    width,
    indent,
    exdent,
    prefix,
    initial,
    simplify,
    wrap_always,
    pad_end,
    strip_spaces,
    use_tabs,
    tab_stops,
    warn,
    term_cap,
    ctl,
    normalize,
    carry,
    terminate,
    subtract_width,
):
    texts = coerce_texts(x)
    extra = {}
    if use_tabs is not None:
        extra["tabs_as_spaces"] = use_tabs
        extra["tab_stops"] = tab_stops
        extra["strip_spaces"] = strip_spaces
    checked = _prepare_common(
        texts, warn, term_cap, ctl, normalize, carry, terminate, extra
    )
    if use_tabs and strip_spaces:
        raise FansiError("`tabs.as.spaces` and `strip.spaces` should not both be TRUE.")
    indent_i = _nonneg_int(indent, "indent")
    exdent_i = _nonneg_int(exdent, "exdent")
    if subtract_width:
        width_i = _wrap_width(width)
    else:
        width_i = width
    prefix_s = _scalar_text(prefix, "prefix")
    initial_s = _scalar_text(initial, "initial")
    pad = _pad_byte(pad_end)
    pieces = strwrap_csi(
        texts,
        width_i,
        indent_i,
        exdent_i,
        prefix_s,
        initial_s,
        wrap_always,
        pad,
        bool(strip_spaces),
        bool(use_tabs),
        checked.get("tab_stops", [8]),
        checked["warn_int"],
        checked["term_cap_int"],
        not subtract_width,
        checked["ctl_int"],
        checked["normalize"],
        checked["carry"],
        checked["terminate"],
    )
    # strtrim is the non-subtract path and returns one string per input.
    if not subtract_width:
        if checked["normalize"]:
            off = WARN_MASK & WARN_ERROR
            # normalize_state(res, warn=FALSE) keeps the default term cap and carry.
            cap = prepare(term_cap=option("fansi.term.cap", dflt_term_cap()), coerce_x=False)[
                "term_cap_int"
            ]
            return _normalize_vector(pieces, off, cap, None)
        return pieces
    return _after_wrap(
        pieces,
        simplify,
        checked["normalize"],
        term_cap,
        checked["carry"],
        checked["term_cap_int"],
    )


def strwrap2_ctl(
    x,
    width=_MISSING,
    indent=0,
    exdent=0,
    prefix="",
    simplify=True,
    initial=_MISSING,
    wrap_always=False,
    pad_end="",
    strip_spaces=_MISSING,
    tabs_as_spaces=_MISSING,
    tab_stops=_MISSING,
    warn=_MISSING,
    term_cap=_MISSING,
    ctl="all",
    normalize=_MISSING,
    carry=_MISSING,
    terminate=_MISSING,
):
    """Wrap each string. An omitted width is 72, which is 0.9 times 80."""
    if width is _MISSING:
        width = 72
    if initial is _MISSING:
        initial = prefix
    if tabs_as_spaces is _MISSING:
        tabs_as_spaces = option("fansi.tabs.as.spaces", False)
    if strip_spaces is _MISSING:
        strip_spaces = not bool(tabs_as_spaces) if not isinstance(tabs_as_spaces, str) else False
    wrap_always = _require_flag(wrap_always, "wrap.always")
    if wrap_always:
        values = _numeric_values(width)
        if values is not None and len(values) == 1 and isinstance(values[0], (int, float)):
            if values[0] < 2:
                raise FansiError("Width must be at least 2 in `wrap.always` mode.")
        elif values is not None and min(v for v in values if isinstance(v, (int, float))) < 2:
            raise FansiError("Width must be at least 2 in `wrap.always` mode.")
    warn = resolve_warn(warn, _MISSING)
    if term_cap is _MISSING:
        term_cap = option("fansi.term.cap", dflt_term_cap())
    if normalize is _MISSING:
        normalize = option("fansi.normalize", False)
    if carry is _MISSING:
        carry = option("fansi.carry", False)
    if terminate is _MISSING:
        terminate = option("fansi.terminate", True)
    if tab_stops is _MISSING:
        tab_stops = option("fansi.tab.stops", 8)
    return _run_wrap(
        x,
        width,
        indent,
        exdent,
        prefix,
        initial,
        simplify,
        wrap_always,
        pad_end,
        strip_spaces,
        tabs_as_spaces,
        tab_stops,
        warn,
        term_cap,
        ctl,
        normalize,
        carry,
        terminate,
        True,
    )


def strwrap_ctl(
    x,
    width=_MISSING,
    indent=0,
    exdent=0,
    prefix="",
    simplify=True,
    initial=_MISSING,
    warn=_MISSING,
    term_cap=_MISSING,
    ctl="all",
    normalize=_MISSING,
    carry=_MISSING,
    terminate=_MISSING,
):
    """strwrap2_ctl with whitespace collapsed and no hard breaks."""
    kwargs = {}
    if width is not _MISSING:
        kwargs["width"] = width
    if initial is not _MISSING:
        kwargs["initial"] = initial
    if warn is not _MISSING:
        kwargs["warn"] = warn
    if term_cap is not _MISSING:
        kwargs["term_cap"] = term_cap
    if normalize is not _MISSING:
        kwargs["normalize"] = normalize
    if carry is not _MISSING:
        kwargs["carry"] = carry
    if terminate is not _MISSING:
        kwargs["terminate"] = terminate
    return strwrap2_ctl(
        x,
        indent=indent,
        exdent=exdent,
        prefix=prefix,
        simplify=simplify,
        ctl=ctl,
        **kwargs,
    )


def strwrap2_sgr(
    x,
    width=_MISSING,
    indent=0,
    exdent=0,
    prefix="",
    simplify=True,
    initial=_MISSING,
    wrap_always=False,
    pad_end="",
    strip_spaces=_MISSING,
    tabs_as_spaces=_MISSING,
    tab_stops=_MISSING,
    warn=_MISSING,
    term_cap=_MISSING,
    normalize=_MISSING,
    carry=_MISSING,
    terminate=_MISSING,
):
    """strwrap2_ctl that treats only SGR sequences as controls."""
    kwargs = {"ctl": "sgr", "wrap_always": wrap_always, "pad_end": pad_end}
    if width is not _MISSING:
        kwargs["width"] = width
    if initial is not _MISSING:
        kwargs["initial"] = initial
    if strip_spaces is not _MISSING:
        kwargs["strip_spaces"] = strip_spaces
    if tabs_as_spaces is not _MISSING:
        kwargs["tabs_as_spaces"] = tabs_as_spaces
    if tab_stops is not _MISSING:
        kwargs["tab_stops"] = tab_stops
    if warn is not _MISSING:
        kwargs["warn"] = warn
    if term_cap is not _MISSING:
        kwargs["term_cap"] = term_cap
    if normalize is not _MISSING:
        kwargs["normalize"] = normalize
    if carry is not _MISSING:
        kwargs["carry"] = carry
    if terminate is not _MISSING:
        kwargs["terminate"] = terminate
    return strwrap2_ctl(
        x, indent=indent, exdent=exdent, prefix=prefix, simplify=simplify, **kwargs
    )


def strwrap_sgr(
    x,
    width=_MISSING,
    indent=0,
    exdent=0,
    prefix="",
    simplify=True,
    initial=_MISSING,
    warn=_MISSING,
    term_cap=_MISSING,
    normalize=_MISSING,
    carry=_MISSING,
    terminate=_MISSING,
):
    """strwrap_ctl that treats only SGR sequences as controls."""
    kwargs = {"ctl": "sgr"}
    if width is not _MISSING:
        kwargs["width"] = width
    if initial is not _MISSING:
        kwargs["initial"] = initial
    if warn is not _MISSING:
        kwargs["warn"] = warn
    if term_cap is not _MISSING:
        kwargs["term_cap"] = term_cap
    if normalize is not _MISSING:
        kwargs["normalize"] = normalize
    if carry is not _MISSING:
        kwargs["carry"] = carry
    if terminate is not _MISSING:
        kwargs["terminate"] = terminate
    return strwrap_ctl(
        x, indent=indent, exdent=exdent, prefix=prefix, simplify=simplify, **kwargs
    )


def strtrim_width(width):
    """The positive integer strtrim passes through, without subtracting one."""
    if isinstance(width, bool) or not isinstance(width, (int, float)):
        raise FansiError(
            "Argument `width` must be a positive scalar numeric representable as an integer."
        )
    if isinstance(width, float) and (width != width or abs(width) == float("inf")):
        raise FansiError(
            "Argument `width` must be a positive scalar numeric representable as an integer."
        )
    if width < 0:
        raise FansiError(
            "Argument `width` must be a positive scalar numeric representable as an integer."
        )
    return int(width)
