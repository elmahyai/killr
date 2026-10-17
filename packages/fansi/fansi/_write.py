"""SGR and URL writers from fansi src/write.c, src/normalize.c, and src/carry.c.

Writers append to a byte buffer. They do not build an R string.
"""

from __future__ import annotations

from fansi._args import FansiError
from fansi._const import (
    BRD_ENCIRC,
    BRD_FRAMED,
    BRD_OVERLN,
    CLR_256,
    CLR_8,
    CLR_BRIGHT,
    CLR_TRU,
    FONT_ALL,
    FONT_START,
    IDG_OVERL,
    IDG_OVERL2,
    IDG_STRESS,
    IDG_UNDERL,
    IDG_UNDERL2,
    STAT_SPECIAL,
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
    get_range,
)
from fansi._read import read_next
from fansi._state import (
    CLR_MASK,
    FONT_MASK,
    INT_MAX,
    offset_bytes,
    sgr_active,
    sgr_intersect,
    sgr_setdiff,
    url_active,
    url_comp,
)

CLR_BUFF_SIZE = 20

# Same groups src/write.c closes with one sequence.
_S_BOLDFAINT = STL_BOLD | STL_BLUR
_S_FRAKTAL = STL_ITALIC | STL_FRAKTUR
_S_UNDERLINE = STL_UNDER | STL_UNDER2
_S_BLINK = STL_BLINK1 | STL_BLINK2
_B_FRAMED = BRD_FRAMED | BRD_ENCIRC
_IDG_MASK = IDG_UNDERL | IDG_UNDERL2 | IDG_OVERL | IDG_OVERL2 | IDG_STRESS


class Buff:
    """Growing byte buffer. `data` is the bytes written so far."""

    __slots__ = ("data",)

    def __init__(self):
        self.data = bytearray()


def _check_append(cur, extra, err_msg, index):
    if cur < 0 or extra < 0:
        raise FansiError("Internal Error: negative lengths.")
    if cur > INT_MAX - extra:
        raise FansiError(
            f"{err_msg} will create string longer than INT_MAX at index "
            f"[{index + 1}]. Try again with smaller strings."
        )


def _copy(buff, raw, index, err_msg):
    if isinstance(raw, str):
        raw = raw.encode("ascii")
    _check_append(len(buff.data), len(raw), err_msg, index)
    buff.data.extend(raw)
    return len(raw)


def _mcopy(buff, raw, index, err_msg):
    _check_append(len(buff.data), len(raw), err_msg, index)
    buff.data.extend(raw)
    return len(raw)


def _copy_span(buff, data, start, stop, index, err_msg):
    """Copy `data[start:stop]`. A backwards span is the C negative-length error."""
    span = stop - start
    if span < 0:
        raise FansiError("Internal Error: negative lengths.")
    _mcopy(buff, data[start:stop], index, err_msg)


def _token(val, normalize):
    if len(val) > 2:
        raise FansiError("Internal error: token maker limited to 2 chars max.")
    if not normalize:
        return val + b";"
    return b"\033[" + val + b"m"


def _color_token(color, mode, normalize):
    """One color parameter, or a whole SGR when `normalize` is true."""
    if mode not in (3, 4):
        raise FansiError("Internal Error: color mode must be 3 or 4")
    out = bytearray()
    if normalize:
        out.append(0x1B)
        out.append(ord("["))
    clrval = color.x & ~CLR_MASK
    if (color.x & CLR_MASK) == CLR_BRIGHT:
        if mode == 3:
            out.append(ord("9"))
        else:
            out.append(ord("1"))
            out.append(ord("0"))
        out.append(ord("0") + clrval)
    else:
        out.append(ord("0") + mode)
        out.append(ord("0") + clrval)
        if color.x & (CLR_256 | CLR_TRU):
            out.append(ord(";"))
            if color.x & CLR_TRU:
                piece = f"2;{color.extra[0]};{color.extra[1]};{color.extra[2]}"
            else:
                piece = f"5;{color.extra[0]}"
            out.extend(piece.encode("ascii"))
        elif not (color.x & CLR_8):
            raise FansiError("Internal Error: unexpected color mode.")
    if normalize:
        out.append(ord("m"))
    else:
        out.append(ord(";"))
    if len(out) >= CLR_BUFF_SIZE - 1:
        raise FansiError(
            f"Internal Error: exceeded color buffer ({len(out)} vs {CLR_BUFF_SIZE})."
        )
    return bytes(out)


def write_sgr(buff, sgr, normalize, enclose, index):
    """Append the active SGR. Order matches src/write.c and stays fixed."""
    err_msg = "Writing SGR tokens"
    if not sgr_active(sgr):
        return
    if not normalize and enclose:
        _copy(buff, b"\033[", index, err_msg)
    style = sgr.style
    if style & STL_BOLD:
        _copy(buff, _token(b"1", normalize), index, err_msg)
    if style & STL_BLUR:
        _copy(buff, _token(b"2", normalize), index, err_msg)
    if style & STL_ITALIC:
        _copy(buff, _token(b"3", normalize), index, err_msg)
    if style & STL_UNDER:
        _copy(buff, _token(b"4", normalize), index, err_msg)
    if style & STL_BLINK1:
        _copy(buff, _token(b"5", normalize), index, err_msg)
    if style & STL_BLINK2:
        _copy(buff, _token(b"6", normalize), index, err_msg)
    if style & STL_INVERT:
        _copy(buff, _token(b"7", normalize), index, err_msg)
    if style & STL_CONCEAL:
        _copy(buff, _token(b"8", normalize), index, err_msg)
    if style & STL_CROSSOUT:
        _copy(buff, _token(b"9", normalize), index, err_msg)
    if style & STL_FRAKTUR:
        _copy(buff, _token(b"20", normalize), index, err_msg)
    if style & STL_UNDER2:
        _copy(buff, _token(b"21", normalize), index, err_msg)
    if style & STL_PROPSPC:
        _copy(buff, _token(b"26", normalize), index, err_msg)
    if sgr.color.x:
        _copy(buff, _color_token(sgr.color, 3, normalize), index, err_msg)
    if sgr.bgcol.x:
        _copy(buff, _color_token(sgr.bgcol, 4, normalize), index, err_msg)
    if style & BRD_FRAMED:
        _copy(buff, _token(b"51", normalize), index, err_msg)
    if style & BRD_ENCIRC:
        _copy(buff, _token(b"52", normalize), index, err_msg)
    if style & BRD_OVERLN:
        _copy(buff, _token(b"53", normalize), index, err_msg)
    if style & IDG_UNDERL:
        _copy(buff, _token(b"60", normalize), index, err_msg)
    if style & IDG_UNDERL2:
        _copy(buff, _token(b"61", normalize), index, err_msg)
    if style & IDG_OVERL:
        _copy(buff, _token(b"62", normalize), index, err_msg)
    if style & IDG_OVERL2:
        _copy(buff, _token(b"63", normalize), index, err_msg)
    if style & IDG_STRESS:
        _copy(buff, _token(b"64", normalize), index, err_msg)
    font = get_range(style, FONT_START, FONT_ALL)
    if font:
        tok = bytes((ord("1"), ord("0") + (font % 10)))
        _copy(buff, _token(tok, normalize), index, err_msg)
    if enclose and buff.data:
        buff.data[-1] = ord("m")


def write_sgr_close(buff, sgr, normalize, index):
    """Append the sequences that turn off `sgr`.

    With `normalize` false, any active SGR closes as ESC[0m.
    """
    err_msg = "Generating closing SGR"
    sgr = sgr.copy()
    if not sgr_active(sgr):
        return
    if not normalize:
        _copy(buff, b"\033[0m", index, err_msg)
        return
    if sgr.style & FONT_MASK:
        sgr.style &= ~FONT_MASK
        _copy(buff, b"\033[10m", index, err_msg)
    if sgr.style & _S_BOLDFAINT:
        sgr.style &= ~_S_BOLDFAINT
        _copy(buff, b"\033[22m", index, err_msg)
    if sgr.style & _S_FRAKTAL:
        sgr.style &= ~_S_FRAKTAL
        _copy(buff, b"\033[23m", index, err_msg)
    if sgr.style & _S_UNDERLINE:
        sgr.style &= ~_S_UNDERLINE
        _copy(buff, b"\033[24m", index, err_msg)
    if sgr.style & _S_BLINK:
        sgr.style &= ~_S_BLINK
        _copy(buff, b"\033[25m", index, err_msg)
    if sgr.style & STL_INVERT:
        sgr.style &= ~STL_INVERT
        _copy(buff, b"\033[27m", index, err_msg)
    if sgr.style & STL_CONCEAL:
        sgr.style &= ~STL_CONCEAL
        _copy(buff, b"\033[28m", index, err_msg)
    if sgr.style & STL_CROSSOUT:
        sgr.style &= ~STL_CROSSOUT
        _copy(buff, b"\033[29m", index, err_msg)
    if sgr.color.x:
        sgr.color.x = 0
        _copy(buff, b"\033[39m", index, err_msg)
    if sgr.bgcol.x:
        sgr.bgcol.x = 0
        _copy(buff, b"\033[49m", index, err_msg)
    if sgr.style & STL_PROPSPC:
        sgr.style &= ~STL_PROPSPC
        _copy(buff, b"\033[50m", index, err_msg)
    if sgr.style & _B_FRAMED:
        sgr.style &= ~_B_FRAMED
        _copy(buff, b"\033[54m", index, err_msg)
    if sgr.style & BRD_OVERLN:
        sgr.style &= ~BRD_OVERLN
        _copy(buff, b"\033[55m", index, err_msg)
    if sgr.style & _IDG_MASK:
        sgr.style &= ~_IDG_MASK
        _copy(buff, b"\033[65m", index, err_msg)
    if sgr_active(sgr):
        raise FansiError(
            "Internal Error: did not successfully close all styles "
            f"(clr: {sgr.color.x} bg: {sgr.bgcol.x} st: {sgr.style})."
        )


def write_url(buff, url, index):
    """Append an OSC 8 hyperlink, terminated by ESC \\."""
    if not url_active(url):
        return
    err_msg = "Writing URL"
    _copy(buff, b"\033]8;", index, err_msg)
    if url.id.len:
        _copy(buff, b"id=", index, err_msg)
        _mcopy(buff, offset_bytes(url.string, url.id), index, err_msg)
    _copy(buff, b";", index, err_msg)
    _mcopy(buff, offset_bytes(url.string, url.url), index, err_msg)
    _copy(buff, b"\033\\", index, err_msg)


def write_url_close(buff, url, index):
    """Append the OSC 8 closer when a URL is active."""
    if url_active(url):
        _copy(buff, b"\033]8;;\033\\", index, "Generating URL end")


def write_close(buff, fmt, normalize, index):
    """Append the SGR close, then the URL close."""
    write_sgr_close(buff, fmt.sgr, normalize, index)
    write_url_close(buff, fmt.url, index)


def write_bridge(buff, end, restart, normalize, index, err_msg):
    """Append the transition from `end` to `restart`."""
    mode = int(not normalize)
    to_close = sgr_setdiff(end.fmt.sgr, restart.fmt.sgr, mode)
    to_open = sgr_setdiff(restart.fmt.sgr, end.fmt.sgr, mode)
    if not normalize:
        renew = sgr_intersect(end.fmt.sgr, restart.fmt.sgr)
        active_open = sgr_active(to_open)
        active_close = sgr_active(to_close)
        if active_open and active_close:
            _copy(buff, b"\033[0;", index, err_msg)
            write_sgr(buff, renew, normalize, 0, index)
            write_sgr(buff, to_open, normalize, 0, index)
            if buff.data:
                buff.data[-1] = ord("m")
        elif active_close:
            _copy(buff, b"\033[0;", index, err_msg)
            write_sgr(buff, renew, normalize, 0, index)
            if buff.data:
                buff.data[-1] = ord("m")
        else:
            write_sgr(
                buff,
                sgr_setdiff(restart.fmt.sgr, end.fmt.sgr, 0),
                normalize,
                1,
                index,
            )
    else:
        write_sgr_close(buff, to_close, normalize, index)
        write_sgr(buff, to_open, normalize, 1, index)
    if url_comp(end.fmt.url, restart.fmt.url):
        if not url_active(restart.fmt.url):
            write_url_close(buff, end.fmt.url, index)
        write_url(buff, restart.fmt.url, index)
    return len(buff.data)


def write_normalize(buff, state, stop, index, err_msg, arg):
    """Rewrite SGR and URL sequences up to byte `stop`.

    Returns the number of bytes appended, or -1 when the string has no
    special sequence to rewrite. `state` ends at the position where reading
    stopped, with the active format of that prefix.
    """
    state_int = state.copy()
    data = state_int.ensure_bytes()
    before = len(buff.data)
    cursor = state_int.pos_x
    last = cursor
    any_to_exp = False
    limit = len(data)
    while True:
        pos = cursor
        while pos < limit and data[pos] not in (0, 0x1B):
            pos += 1
        state_int.pos_x = pos
        if state_int.pos_x >= stop:
            if any_to_exp:
                _copy_span(buff, data, last, stop, index, err_msg)
            break
        if pos < limit and data[pos] == 0x1B:
            state_prev = state_int.copy()
            read_next(state_int, index, arg)
            if state_int.status & STAT_SPECIAL:
                any_to_exp = True
                _copy_span(buff, data, last, pos, index, err_msg)
                write_bridge(buff, state_prev, state_int, 1, index, err_msg)
                last = state_int.pos_x
            cursor = state_int.pos_x
            continue
        if pos >= limit or data[pos] == 0:
            raise FansiError("Internal Error: unexpected `stop` value for normalize.")
        raise FansiError("Internal Error: normalize logic error.")
    state.become(state_int)
    if not any_to_exp:
        return -1
    return len(buff.data) - before


def state_as_chr(buff, state, normalize, index):
    """Replace `buff` with the active SGR followed by the active URL."""
    buff.data.clear()
    write_sgr(buff, state.fmt.sgr, normalize, 1, index)
    write_url(buff, state.fmt.url, index)
    return buff
