"""CSI, OSC, and UTF-8 reader from fansi src/read.c and src/utils.c.

Byte tests follow the C scanner. A C0 control, a final CSI byte, and a UTF-8
lead all use the same ranges as that file. Display width comes from
`fansi._width.unicode_width`.
"""

from __future__ import annotations

import sys
import warnings

from fansi._args import FansiError, as_character, option
from fansi._const import (
    BRD_ENCIRC,
    BRD_FRAMED,
    BRD_OVERLN,
    CLR_256,
    CLR_8,
    CLR_BRIGHT,
    CLR_TRU,
    COUNT_BYTES,
    COUNT_GRAPH,
    COUNT_WIDTH,
    CTL_ALL,
    CTL_C0,
    CTL_CSI,
    CTL_ESC,
    CTL_NL,
    CTL_OSC,
    CTL_SGR,
    CTL_URL,
    ERR_BAD_CSI_OSC,
    ERR_BAD_SUB,
    ERR_BAD_UTF8,
    ERR_C0,
    ERR_ESC_OTHER,
    ERR_ESC_OTHER_BAD,
    ERR_EXCEED_CAP,
    ERR_MESSAGES,
    ERR_NON_ASCII,
    ERR_NOT_SPECIAL,
    ERR_NOT_SPECIAL_BAD_SUB,
    ERR_UNKNOWN_SUB,
    FONT_ALL,
    FONT_START,
    IDG_MASK,
    IDG_OVERL,
    IDG_OVERL2,
    IDG_STRESS,
    IDG_UNDERL,
    IDG_UNDERL2,
    SET_ESCONE,
    SET_TERMOLD,
    SET_WARN,
    SET_WIDTH,
    STAT_DONE,
    STAT_ERR_ALL,
    STAT_ERR_START,
    STAT_OVERSHOT,
    STAT_PERSIST,
    STAT_RI,
    STAT_SPECIAL,
    STAT_WARNED,
    STAT_ZWJ,
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
    TERM_256,
    TERM_BRIGHT,
    TERM_TRUECOLOR,
    get_range,
    set_range,
)
from fansi._state import INT_MAX, Offset, Sgr, Url
from fansi._width import unicode_width

# SGR, CSI, ESC, URL, and OSC. Newlines and other C0 controls are separate.
CTL_ESC_CTL = CTL_SGR | CTL_CSI | CTL_ESC | CTL_URL | CTL_OSC
FONT_MASK = FONT_ALL << FONT_START

_UTF8_TABLE4 = (
    1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
    1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
    2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2,
    3, 3, 3, 3, 3, 3, 3, 3, 4, 4, 4, 4, 5, 5, 5, 5,
)


def _emit_warning(message):
    """Print every warning. An empty registry keeps the default filter from swallowing the next one."""
    frame = sys._getframe(2)
    warnings.warn_explicit(
        message,
        UserWarning,
        frame.f_code.co_filename,
        frame.f_lineno,
        module="fansi._read",
        registry={},
    )


def _get_err(status):
    return get_range(status, STAT_ERR_START, STAT_ERR_ALL)


def _set_err(status, err):
    return set_range(status, STAT_ERR_START, STAT_ERR_ALL, err)


def _is_print(byte):
    return 0x20 <= byte < 0x7F


def _is_utf8(byte):
    return byte > 0x7F


def _is_esc(byte):
    return byte == 0x1B


def _maybe_ctl(byte):
    return bool(byte and (not (byte & ~0x1F) or byte == 0x7F))


def resolve_warn(warn, missing):
    """Missing uses the fansi.warn option. None is R's NA and is an error."""
    if warn is missing:
        return option("fansi.warn", True)
    if warn is None:
        raise FansiError("Argument `warn` must be TRUE or FALSE.")
    return warn


def coerce_texts(value):
    """Character vector: a str or bytes is one element, None is a missing string."""
    if isinstance(value, bytes):
        value = value.decode("utf-8", "surrogateescape")
    elif isinstance(value, (list, tuple)) and any(isinstance(item, bytes) for item in value):
        value = [
            item.decode("utf-8", "surrogateescape") if isinstance(item, bytes) else item
            for item in value
        ]
    return as_character(value)


def seek_ctl(data, start=0):
    """Bytes from `start` until the next possible C0 control, or the end."""
    limit = len(data)
    index = start
    while index < limit:
        byte = data[index]
        if byte == 0 or _maybe_ctl(byte):
            break
        index += 1
    offset = index - start
    if offset > INT_MAX:
        raise FansiError("Internal error: sought past INT_MAX, should not happen.")
    return offset


def _utf8clen(data, start):
    """Return (byte_count, mb_err), matching utf8clen()."""
    lead = data[start]
    if (lead & 0xC0) != 0xC0:
        size = 1
    else:
        size = 1 + _UTF8_TABLE4[lead & 0x3F]
    mb_err = 0
    limit = len(data)
    for step in range(1, size):
        if start + step >= limit or data[start + step] == 0:
            mb_err = 1
            size = step
            break
    return size, mb_err


def _valid_utf8(data, start, size):
    if size <= 1:
        return 0
    passed = not (data[start] & (0x20 >> (size - 2)))
    if size not in (2, 3, 4):
        return 0
    for step in range(1, size):
        passed = passed and ((data[start + step] & 0xC0) == 0x80)
    return 1 if passed else 0


def _utf8_to_cp(data, start, size):
    lead_mask = 0xFF >> (size + (1 if size > 1 else 0))
    code = (data[start] & lead_mask) << ((size - 1) * 6)
    for remaining in range(size - 1, 0, -1):
        code |= (data[start + size - remaining] & 0x3F) << ((remaining - 1) * 6)
    return code


def alert(state, index, arg):
    """Warn or stop the way read.c alert() does. The message text matches."""
    err_code = _get_err(state.status)
    err_mode = err_code in (ERR_BAD_UTF8, ERR_NON_ASCII)
    armed = (not (state.status & STAT_WARNED) or err_mode) and err_code
    if not armed:
        return
    if not (state.settings & (1 << (SET_WARN + err_code - 1))):
        return
    if arg:
        prefix = f"Argument `{arg}` contains"
    else:
        prefix = "Encountered"
    trailer = "." if err_mode else "; you can use `warn=FALSE` to turn off these warnings."
    message = (
        f"{prefix} {ERR_MESSAGES[err_code - 1]} at index [{index + 1}], "
        f"see `?unhandled_ctl`{trailer}"
    )
    if err_mode:
        raise FansiError(message)
    _emit_warning(message)
    state.status |= STAT_WARNED


def _get_url_param(data, start, length, param):
    result = Offset()
    plen = 0
    while plen <= 128 and plen < len(param) and param[plen]:
        plen += 1
    if plen < len(param) and param[plen]:
        raise FansiError("Internal Error: max allowed param len 128 bytes.")
    if not plen:
        return result
    if param[plen - 1] != ord("="):
        raise FansiError("Internal Error: trailing param char must be '='.")
    if plen > length:
        return result
    target = start
    limit = len(data)
    while (
        target < limit
        and data[target]
        and (target - start < length - plen)
        and data[target:target + plen] != param
    ):
        target += 1
    if target < limit and data[target]:
        value_start = target + plen
        end = target
        while end < limit and data[end] and data[end] not in (ord(":"), ord(";")):
            end += 1
        result = Offset(value_start, end - value_start)
    return result


def parse_token(state):
    """Read one CSI parameter. Leaves `pos_x` on the delimiter."""
    data = state.ensure_bytes()
    limit = len(data)
    start = state.pos_x
    cursor = start
    leading_zeros = 0
    not_zero = 0
    non_standard = 0

    def at(index):
        if index < 0 or index >= limit:
            return 0
        return data[index]

    while True:
        byte = at(cursor)
        if byte < 0x30 or byte > 0x3F or byte == ord(";"):
            break
        is_zero = byte == ord("0")
        if not is_zero and not not_zero:
            not_zero = 1
        if is_zero and not not_zero:
            leading_zeros += 1
        if byte > 0x39:
            non_standard = 1
        cursor += 1
    length = cursor - start
    bad_sub = 1 if non_standard else 0
    while True:
        byte = at(cursor)
        if byte < 0x20 or byte > 0x2F:
            break
        cursor += 1
    len_intermediate = cursor - start - length
    byte = at(cursor)
    is_csi = 1
    err_code = 0
    len_tail = 0
    if byte in (ord(";"), ord("m")) and not len_intermediate:
        if byte == ord(";"):
            is_csi = 0
    elif 0x40 <= byte <= 0x7E:
        err_code = ERR_NOT_SPECIAL
    else:
        while at(cursor) and (at(cursor) < 0x40 or at(cursor) > 0x7E):
            if at(cursor) > 0x7F:
                err_code = ERR_NON_ASCII
            cursor += 1
            len_tail += 1
        bad_sub = 1
        if not at(cursor) and err_code < ERR_BAD_CSI_OSC:
            err_code = ERR_BAD_CSI_OSC
    is_sgr = 1 if at(cursor) == ord("m") else 0
    if length - leading_zeros > 3:
        bad_sub = 1
    value = 0
    if not bad_sub and err_code < ERR_BAD_SUB:
        remain = length - leading_zeros
        digit = start + length
        mult = 1
        while remain:
            remain -= 1
            digit -= 1
            char = data[digit]
            if char < 48 or char > 57:
                raise FansiError(
                    "Internal Error: attempt to convert non-numeric char "
                    f"({char}) to int."
                )
            value += (char - 48) * mult
            mult *= 10
    if value > 255:
        bad_sub = 1
    if bad_sub and not is_sgr and err_code < ERR_NOT_SPECIAL_BAD_SUB:
        err_code = ERR_NOT_SPECIAL_BAD_SUB
    elif bad_sub and err_code < ERR_BAD_SUB:
        err_code = ERR_BAD_SUB
    state.pos_x += length + len_intermediate + len_tail
    state.status = _set_err(state.status, err_code)
    if is_sgr:
        state.status |= CTL_SGR
    elif is_csi:
        state.status |= CTL_CSI
    return value


def parse_colors(state, mode):
    """Read 38/48 color parameters. `mode` is 3 for foreground and 4 for background."""
    if mode not in (3, 4):
        raise FansiError("Internal Error: parsing color with invalid mode.")
    data = state.string
    prev_x = state.pos_x
    if state.at(state.pos_x) != ord(";"):
        state.status = _set_err(state.status, ERR_BAD_SUB)
        return
    state.pos_x += 1
    tok_val = parse_token(state)
    err_tmp = _get_err(state.status)
    if not err_tmp and state.at(state.pos_x) == ord(";"):
        state.pos_x += 1
        if (tok_val not in (2, 5)) or (state.status & CTL_CSI):
            state.pos_x = prev_x
            state.status = _set_err(state.status, ERR_UNKNOWN_SUB)
            return
        cap_exceeded = (tok_val == 2 and not (state.settings & TERM_TRUECOLOR)) or (
            tok_val == 5 and not (state.settings & TERM_256)
        )
        if cap_exceeded and (state.settings & SET_TERMOLD):
            state.pos_x = prev_x
            state.status = _set_err(state.status, ERR_EXCEED_CAP)
            return
        tmp_col = [0, 0, 0]
        colors = tok_val
        err_col = 0
        early_end = 0
        i_max = 1 if colors == 5 else 3
        for index in range(i_max):
            tok_val = parse_token(state)
            err_col = _get_err(state.status)
            early_end = state.at(state.pos_x) != ord(";") and index < (i_max - 1)
            if early_end and err_col < ERR_BAD_SUB:
                state.status = _set_err(state.status, ERR_BAD_SUB)
                err_col = ERR_BAD_SUB
            tmp_col[index] = tok_val & 0xFF
            if state.at(state.pos_x) and index < (i_max - 1) and not early_end:
                state.pos_x += 1
            if early_end:
                break
        if not err_col and not early_end:
            if colors == 2:
                encoded = CLR_TRU | 8
            elif colors == 5:
                encoded = CLR_256 | 8
            else:
                raise FansiError("Internal Error: 1301341")
            if mode == 3:
                state.fmt.sgr.color.x = encoded
                state.fmt.sgr.color.extra[:] = tmp_col
            else:
                state.fmt.sgr.bgcol.x = encoded
                state.fmt.sgr.bgcol.extra[:] = tmp_col
        if cap_exceeded and err_col < ERR_EXCEED_CAP:
            state.status = _set_err(state.status, ERR_EXCEED_CAP)
    elif not err_tmp:
        state.status = _set_err(state.status, ERR_BAD_SUB)


def parse_url(state):
    """Read an OSC 8 hyperlink. Returns the OSC length excluding the opening ESC."""
    data = state.ensure_bytes()
    limit = len(data)
    cursor = state.pos_x

    def at(index):
        if index < 0 or index >= limit:
            return 0
        return data[index]

    if not (at(cursor) == ord("8") and at(cursor + 1) == ord(";")):
        raise FansiError("Internal Error: non-URL OSC fed to URL parser.")
    o_dat = state.pos_x + 2
    end = o_dat
    o_semic = 0
    o_bad = 0
    err_tmp = 0
    while end < limit and data[end] and data[end] != 0x07 and not (
        data[end] == 0x1B and at(end + 1) == ord("\\")
    ):
        byte = data[end]
        if 0x20 <= byte <= 0x7E:
            if byte == ord(";") and o_semic <= o_dat:
                o_semic = end
        elif byte > 0x7F:
            err_tmp = ERR_NON_ASCII
        elif not (0x08 <= byte <= 0x0D):
            if err_tmp < ERR_BAD_SUB:
                err_tmp = ERR_BAD_SUB
            o_bad = end
        else:
            if err_tmp < ERR_BAD_SUB:
                err_tmp = ERR_BAD_SUB
            o_bad = end
        end += 1
    if end < limit and data[end]:
        if o_semic >= o_dat:
            state.fmt.url = Url(data)
            id_tmp = _get_url_param(data, o_dat, o_semic - o_dat, b"id=")
            if id_tmp.start > o_bad:
                state.fmt.url.id = id_tmp
            if o_semic > o_bad:
                state.fmt.url.url = Offset(o_semic + 1, end - (o_semic + 1))
            ident = state.fmt.url.id
            if (
                ident.start > o_dat + 3
                or (ident.start and o_semic > ident.start + ident.len)
                or (not ident.start and o_semic > o_dat)
            ):
                if err_tmp < ERR_UNKNOWN_SUB:
                    err_tmp = ERR_UNKNOWN_SUB
            if (end < ident.len) or (end < state.fmt.url.url.len):
                raise FansiError("Internal Error: bad URI size.")
    else:
        err_tmp = ERR_BAD_CSI_OSC
    if end < o_dat:
        raise FansiError("Internal Error: bad url data detection")
    terminated = 1 if end < limit and data[end] else 0
    st_extra = 1 if end < limit and data[end] == 0x1B else 0
    osc_len = end - o_dat + 2 + terminated + st_extra
    state.status |= CTL_URL
    state.pos_x += osc_len
    state.status = _set_err(state.status, err_tmp)
    return osc_len


def _is_st(data, end):
    """ESC \\ string terminator. A missing second byte is not a terminator."""
    return (
        end < len(data)
        and data[end] == 0x1B
        and end + 1 < len(data)
        and data[end + 1] == ord("\\")
    )


def _parse_osc(data, start):
    """Length and error of a generic OSC, excluding the opening ESC ]."""
    limit = len(data)
    end = start
    error = 0
    while end < limit and data[end] and data[end] != 0x07 and not _is_st(data, end):
        byte = data[end]
        if not ((0x08 <= byte <= 0x0D) or (0x20 <= byte <= 0x7E)):
            if byte > 0x7F:
                error = ERR_NON_ASCII
            elif error < ERR_NOT_SPECIAL_BAD_SUB:
                error = ERR_NOT_SPECIAL_BAD_SUB
        end += 1
    if (end >= limit or not data[end]) and error < ERR_BAD_CSI_OSC:
        error = ERR_BAD_CSI_OSC
    present = 1 if end < limit and data[end] else 0
    extra = 1 if end < limit and data[end] == 0x1B else 0
    return end - start + present + extra, error


def _apply_sgr_token(state, tok_val):
    """Record one valid SGR number. Unknown numbers set ERR_UNKNOWN_SUB."""
    style = state.fmt.sgr.style
    if tok_val < 10:
        state.fmt.sgr.style = style | (1 << (tok_val - 1))
    elif tok_val < 20:
        style &= ~FONT_MASK
        if tok_val > 10:
            style |= tok_val << FONT_START
        state.fmt.sgr.style = style
    elif tok_val == 20:
        state.fmt.sgr.style = style | STL_FRAKTUR
    elif tok_val == 21:
        state.fmt.sgr.style = style | STL_UNDER2
    elif tok_val == 26:
        state.fmt.sgr.style = style | STL_PROPSPC
    elif tok_val == 22:
        state.fmt.sgr.style = style & ~STL_BOLD & ~STL_BLUR
    elif tok_val == 23:
        state.fmt.sgr.style = style & ~STL_ITALIC & ~STL_FRAKTUR
    elif tok_val == 24:
        state.fmt.sgr.style = style & ~STL_UNDER & ~STL_UNDER2
    elif tok_val == 25:
        state.fmt.sgr.style = style & ~STL_BLINK1 & ~STL_BLINK2
    elif tok_val == 27:
        state.fmt.sgr.style = style & ~STL_INVERT
    elif tok_val == 28:
        state.fmt.sgr.style = style & ~STL_CONCEAL
    elif tok_val == 29:
        state.fmt.sgr.style = style & ~STL_CROSSOUT
    elif tok_val == 50:
        state.fmt.sgr.style = style & ~STL_PROPSPC
    elif 50 < tok_val < 60:
        if tok_val == 51:
            state.fmt.sgr.style = style | BRD_FRAMED
        elif tok_val == 52:
            state.fmt.sgr.style = style | BRD_ENCIRC
        elif tok_val == 53:
            state.fmt.sgr.style = style | BRD_OVERLN
        elif tok_val == 54:
            state.fmt.sgr.style = style & ~(BRD_FRAMED | BRD_ENCIRC)
        elif tok_val == 55:
            state.fmt.sgr.style = style & ~BRD_OVERLN
        else:
            state.status = _set_err(state.status, ERR_UNKNOWN_SUB)
    elif 60 <= tok_val <= 65:
        if tok_val == 60:
            state.fmt.sgr.style = style | IDG_UNDERL
        elif tok_val == 61:
            state.fmt.sgr.style = style | IDG_UNDERL2
        elif tok_val == 62:
            state.fmt.sgr.style = style | IDG_OVERL
        elif tok_val == 63:
            state.fmt.sgr.style = style | IDG_OVERL2
        elif tok_val == 64:
            state.fmt.sgr.style = style | IDG_STRESS
        else:
            state.fmt.sgr.style = style & ~IDG_MASK
    else:
        state.status = _set_err(state.status, ERR_UNKNOWN_SUB)


def _record_basic_color(state, tok_val):
    foreground = tok_val < 40
    code = tok_val - (30 if foreground else 40)
    encoded = CLR_8 | code
    if foreground:
        state.fmt.sgr.color.x = encoded
    else:
        state.fmt.sgr.bgcol.x = encoded


def _record_bright_color(state, tok_val):
    term_old = state.settings & SET_TERMOLD
    if (state.settings & TERM_BRIGHT) or not term_old:
        if not (state.settings & TERM_BRIGHT) and not term_old:
            state.status = _set_err(state.status, ERR_EXCEED_CAP)
        foreground = tok_val < 100
        code = tok_val - (90 if foreground else 100)
        encoded = CLR_BRIGHT | code
        if foreground:
            state.fmt.sgr.color.x = encoded
        else:
            state.fmt.sgr.bgcol.x = encoded


def read_esc(state, term_i):
    """Consume one run of escape sequences, greedily, the way read_esc does."""
    data = state.ensure_bytes()
    if state.at(state.pos_x) != 27:
        raise FansiError(
            "Internal error: parsing ESC sequence that doesn't start with ESC "
            f"(decimal char {state.at(state.pos_x)})."
        )
    esc_types = 0
    err_code = 0
    state.status &= ~CTL_ALL
    sgr_sup = state.settings & CTL_SGR
    csi_sup = state.settings & CTL_CSI
    while True:
        state_prev = state.copy()
        recognized = 1
        state.pos_x += 1
        state.status &= STAT_WARNED
        byte = state.at(state.pos_x)
        nxt = state.at(state.pos_x + 1)
        nxt2 = state.at(state.pos_x + 2)
        if byte == ord("[") and (sgr_sup or csi_sup):
            state.pos_x += 1
            ctl_prev = state.status & CTL_ALL
            state.status &= ~CTL_ALL
            while True:
                state.status = _set_err(state.status, 0)
                tok_val = parse_token(state)
                if not _get_err(state.status):
                    if not tok_val:
                        state.fmt.sgr = Sgr()
                    elif tok_val == 39:
                        state.fmt.sgr.color.x = 0
                    elif tok_val == 49:
                        state.fmt.sgr.bgcol.x = 0
                    elif tok_val in (38, 48):
                        parse_colors(state, 3 if tok_val < 40 else 4)
                    elif 30 <= tok_val < 48:
                        _record_basic_color(state, tok_val)
                    elif (90 <= tok_val <= 97) or (100 <= tok_val <= 107):
                        _record_bright_color(state, tok_val)
                    else:
                        _apply_sgr_token(state, tok_val)
                if _get_err(state.status) > err_code:
                    err_code = _get_err(state.status)
                if state.at(state.pos_x) != ord(";"):
                    break
                state.pos_x += 1
            if state.at(state.pos_x):
                state.pos_x += 1
            sgr = state.status & CTL_SGR
            csi = state.status & CTL_CSI
            if sgr and sgr_sup:
                esc_types |= 2
            elif csi and csi_sup:
                esc_types |= 1
            elif (sgr and not sgr_sup) or (csi and not csi_sup):
                state.become(state_prev)
                state.status &= STAT_WARNED
                _read_one(state)
            else:
                raise FansiError("Internal Error: unexpected CSI/SGR status.")
            state.status |= ctl_prev
        elif byte == ord("]") and nxt == ord("8") and nxt2 == ord(";") and (
            state.settings & CTL_URL
        ):
            state.pos_x += 1
            parse_url(state)
            esc_types |= 2
        elif byte == ord("]") and (state.settings & CTL_OSC):
            state.pos_x += 1
            osc_len, osc_err = _parse_osc(data, state.pos_x)
            err_code = osc_err
            state.status |= CTL_OSC
            esc_types |= 1
            state.pos_x += osc_len
        elif not byte and (state.settings & CTL_ESC_CTL):
            state.status |= CTL_ESC
            esc_types |= 1
            err_code = ERR_ESC_OTHER_BAD
        elif state.settings & CTL_ESC:
            esc_types |= 1
            state.status |= CTL_ESC
            if 0x40 <= byte <= 0x7E:
                err_code = ERR_ESC_OTHER
            elif byte > 0x7F:
                err_code = ERR_NON_ASCII
            else:
                err_code = ERR_ESC_OTHER_BAD
            if byte:
                state.pos_x += 1
        else:
            esc_types |= 1
            recognized = 0
        if esc_types == 3:
            state.become(state_prev)
            break
        if _get_err(state.status) > err_code:
            err_code = _get_err(state.status)
        if recognized:
            if esc_types == 2 and (
                err_code <= ERR_EXCEED_CAP or not (state.settings & SET_TERMOLD)
            ):
                if term_i and not state.at(state.pos_x):
                    state.become(state_prev)
                    state.status |= STAT_DONE
                    break
                state.status |= STAT_SPECIAL
        else:
            state.become(state_prev)
            _read_one(state)
            break
        if state.at(state.pos_x) != 0x1B or (state.settings & SET_ESCONE):
            break
    if err_code > _get_err(state.status):
        state.status = _set_err(state.status, err_code)


def _read_one(state):
    state.pos_x += 1
    state.pos_w += 1


def read_c0(state):
    """A newline or other C0 byte. Recognized controls add no width."""
    nl_sup = state.settings & CTL_NL
    c0_sup = state.settings & CTL_C0
    is_nl = state.at(state.pos_x) == ord("\n")
    state.status &= STAT_WARNED
    if not is_nl:
        state.status = _set_err(state.status, ERR_C0)
    _read_one(state)
    if (is_nl and nl_sup) or (not is_nl and c0_sup):
        state.pos_w -= 1
        state.status |= CTL_NL if is_nl else CTL_C0


def read_ascii_until(state, until, reset):
    if reset:
        state.status &= STAT_WARNED
    remain = until - state.pos_w
    data = state.string
    limit = len(data)
    start = state.pos_x
    end = start
    if remain > 0:
        stop = start + remain
        if stop > limit:
            stop = limit
        while end < stop:
            byte = data[end]
            if byte < 0x20 or byte >= 0x7F:
                break
            end += 1
    count = end - start
    state.pos_w += count
    state.pos_x = end


def read_utf8_until(state, until, overshoot):
    """Read UTF-8 until `until`, joining marks, ZWJ sequences, and flag pairs."""
    data = state.ensure_bytes()
    width_mode = get_range(state.settings, SET_WIDTH, 3)
    cur_ri = state.status & STAT_RI
    cur_zwj = state.status & STAT_ZWJ
    state.status &= STAT_WARNED
    while True:
        byte = state.at(state.pos_x)
        if not byte or not _is_utf8(byte):
            break
        prev_zwj = cur_zwj
        prev_ri = cur_ri
        cur_zwj = 0
        cur_ri = 0
        byte_size, mb_err = _utf8clen(data, state.pos_x)
        mb_err = mb_err or not _valid_utf8(data, state.pos_x, byte_size)
        if mb_err:
            disp_size = None
        elif width_mode in (COUNT_WIDTH, COUNT_GRAPH):
            code = _utf8_to_cp(data, state.pos_x, byte_size)
            if 0x1F1E6 <= code <= 0x1F1FF:
                if not prev_ri:
                    cur_ri |= STAT_RI
                    disp_size = 2
                else:
                    disp_size = 0
            elif 0x1F3FB <= code <= 0x1F3FF:
                disp_size = 0
            elif code == 0x200D:
                cur_zwj |= STAT_ZWJ
                disp_size = 0
            elif prev_zwj:
                disp_size = 0
            else:
                disp_size = unicode_width(code)
            if width_mode == COUNT_GRAPH and disp_size > 1:
                disp_size = 1
        elif width_mode == COUNT_BYTES:
            disp_size = byte_size
        else:
            disp_size = 1
        if prev_ri:
            cur_ri = 0
        if disp_size is None:
            state.status = _set_err(state.status, ERR_BAD_UTF8)
            disp_size = 1
            byte_size = 1
        total = state.pos_w + disp_size
        if total > until and not overshoot:
            state.status |= STAT_DONE
            break
        if total == until:
            overshoot = 0
        elif total > until and overshoot:
            state.status |= STAT_OVERSHOT
            until = total
            overshoot = 0
        state.pos_x += byte_size
        state.utf8 = state.pos_x
        state.status &= cur_ri | ~STAT_RI
        state.status &= cur_zwj | ~STAT_ZWJ
        if state.pos_w > INT_MAX - disp_size:
            raise FansiError("Internal Error:  width greater than INT_MAX")
        if not prev_zwj or width_mode not in (COUNT_WIDTH, COUNT_GRAPH):
            state.pos_w += disp_size
        if mb_err:
            break


def read_next(state, index, arg):
    """Read one character, escape, or C0 control and update `state`."""
    state.ensure_bytes()
    byte = state.at(state.pos_x)
    state.status &= STAT_PERSIST
    is_utf8 = _is_utf8(byte)
    is_print = _is_print(byte)
    if is_print:
        _read_one(state)
    elif is_utf8:
        read_utf8_until(state, state.pos_w + 1, 1)
    elif _is_esc(byte):
        read_esc(state, 0)
    elif byte:
        read_c0(state)
    if is_print or (not is_utf8 and not (state.status & CTL_ALL)):
        state.status &= ~(STAT_RI | STAT_ZWJ)
    alert(state, index, arg)


def read_until(state, until, overshoot, term_i, mode, index, arg):
    """Read until width `until`. `mode` 0 keeps trailing controls."""
    state.ensure_bytes()
    state.status &= STAT_WARNED
    aborted = False
    while state.at(state.pos_x) and state.pos_w < until and not (
        state.status & (STAT_OVERSHOT | STAT_DONE)
    ):
        state.status &= STAT_PERSIST
        byte = state.at(state.pos_x)
        if _is_print(byte):
            read_ascii_until(state, until, 1)
        elif _is_utf8(byte):
            read_utf8_until(state, until, overshoot)
        elif _is_esc(byte):
            read_esc(state, term_i)
        elif byte:
            read_c0(state)
        alert(state, index, arg)
        if _get_err(state.status) == ERR_BAD_UTF8:
            aborted = True
            break
    state_tmp = None
    if not aborted:
        overshoot = 0
        until = state.pos_w
        state_tmp = state.copy()
        while (
            state_tmp.at(state_tmp.pos_x)
            and state_tmp.pos_w == until
            and not _is_print(state_tmp.at(state_tmp.pos_x))
            and not (state_tmp.status & STAT_DONE)
        ):
            state_tmp.status &= STAT_PERSIST
            byte = state_tmp.at(state_tmp.pos_x)
            if _is_utf8(byte):
                pos_prev = state_tmp.pos_x
                read_utf8_until(state_tmp, until, overshoot)
                if state_tmp.pos_x == pos_prev:
                    break
                if state_tmp.pos_w == state.pos_w:
                    state.become(state_tmp)
            else:
                if _is_esc(byte):
                    read_esc(state_tmp, term_i)
                elif byte:
                    read_c0(state_tmp)
                if not (state_tmp.status & CTL_ALL):
                    break
                if mode == 0:
                    state.become(state_tmp)
            alert(state_tmp, index, arg)
            if _get_err(state.status) == ERR_BAD_UTF8:
                aborted = True
                break
        if not aborted:
            alert(state_tmp, index, arg)
    if state_tmp is not None:
        state.status |= state_tmp.status & STAT_WARNED


def read_all(state, index, arg):
    """Read the rest of the string. Width is capped at INT_MAX."""
    read_until(state, INT_MAX, 0, 0, 1, index, arg)


def find_ctl(state, index, arg):
    """Advance to the next recognized control. Return the byte it starts at."""
    state.ensure_bytes()
    data = state.string
    pos = state.pos_x
    limit = len(data)
    while state.pos_x < limit and data[state.pos_x]:
        state.pos_x += seek_ctl(data, state.pos_x)
        pos = state.pos_x
        read_next(state, index, arg)
        if state.status & CTL_ALL:
            break
    return pos
