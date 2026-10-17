"""Convert CSI SGR and OSC hyperlinks to HTML, from src/tohtml.c and R/tohtml.R."""

from __future__ import annotations

import sys
import warnings

from fansi._args import FansiError, option, prepare
from fansi._const import (
    CLR_256,
    CLR_8,
    CLR_BRIGHT,
    CLR_TRU,
    STAT_WARNED,
    STL_INVERT,
    STL_MASK2,
    WARN_ERROR,
    WARN_MASK,
)
from fansi._read import coerce_texts, read_all, read_next, resolve_warn
from fansi._state import state_init_full, reset_pos
from fansi.simple import dflt_term_cap

_MISSING = object()
CLR_MASK = 240

# Codes 1 through 9. Invert is present so the bit offsets stay aligned.
_CSS_STYLE = (
    "font-weight: bold",
    "font-weight: 100",
    "font-style: italic",
    "text-decoration: underline",
    "text-decoration: blink",
    "text-decoration: blink",
    "",
    "color: transparent",
    "text-decoration: line-through",
)

_STD_16 = (
    "000000", "800000", "008000", "808000",
    "000080", "800080", "008080", "C0C0C0",
    "808080", "FF0000", "00FF00", "FFFF00",
    "0000FF", "FF00FF", "00FFFF", "FFFFFF",
)
_STD_8 = (
    "000000", "BB0000", "00BB00", "BBBB00",
    "0000BB", "BB00BB", "00BBBB", "BBBBBB",
)
_STD_5 = ("00", "5F", "87", "AF", "D7", "FF")
_BRIGHT = (
    "555555", "FF5555", "55FF55", "FFFF55",
    "5555FF", "FF55FF", "55FFFF", "FFFFFF",
)
_HEX = "0123456789ABCDEF"


def _fansi_classes():
    names = []
    for index in range(256):
        names.append(f"fansi-color-{index:03d}")
        names.append(f"fansi-bgcol-{index:03d}")
    return names


_FANSI_CLASSES = _fansi_classes()


def _warn(message):
    frame = sys._getframe(1)
    warnings.warn_explicit(
        message,
        UserWarning,
        frame.f_code.co_filename,
        frame.f_lineno,
        module="fansi.to_html",
        registry={},
    )


def check_classes(classes):
    """Length 16, 32, or 512, and only ASCII class-name characters."""
    length = len(classes)
    if length not in (16, 32, 512):
        raise FansiError(
            "Argument `classes` must be length 16, 32, or 512 if it is a "
            f"character vector (is {length})."
        )
    if any(item is None for item in classes):
        raise FansiError("Argument `classes` contains NA values.")
    for item in classes:
        if not isinstance(item, str) or any(
            not (ord("0") <= ord(char) <= ord("9")
                 or ord("a") <= ord(char) <= ord("z")
                 or ord("A") <= ord(char) <= ord("Z")
                 or char in "-_")
            for char in item
        ):
            raise FansiError(
                "Argument `classes` contains charcters other than ASCII letters, "
                "numbers, the hyphen, and underscore."
            )
    return list(classes)


def _as_class_vector(classes):
    if classes is True:
        return list(_FANSI_CLASSES)
    if classes is False:
        return []
    if isinstance(classes, str):
        return check_classes([classes])
    if isinstance(classes, (list, tuple)):
        return check_classes(list(classes))
    raise FansiError("Argument `classes` must be TRUE, FALSE, or a character vector.")


def color_to_html(color):
    """`#RRGGBB` for one fansi color, the way color_to_html writes it."""
    clrval = color.x & ~CLR_MASK
    if clrval == 9:
        raise FansiError("Internal Error: applying non-color.")
    mode = color.x & CLR_MASK
    if mode == CLR_8:
        body = _STD_8[clrval]
    elif mode == CLR_BRIGHT:
        body = _BRIGHT[clrval]
    elif mode == CLR_256:
        color_5 = color.extra[0]
        if color_5 < 16:
            body = _STD_16[color_5]
        elif color_5 < 232:
            cube = color_5 - 16
            red, cube = divmod(cube, 36)
            green, blue = divmod(cube, 6)
            body = _STD_5[red] + _STD_5[green] + _STD_5[blue]
        else:
            shade = (color_5 - 232) * 10 + 8
            pair = _HEX[shade // 16] + _HEX[shade % 16]
            body = pair * 3
    elif mode == CLR_TRU:
        body = "".join(
            _HEX[channel // 16] + _HEX[channel % 16] for channel in color.extra[:3]
        )
    else:
        raise FansiError("Internal Error: unknown color mode.")
    return "#" + body


def _color_to_8bit(color):
    mode = color.x & CLR_MASK
    if mode == CLR_8:
        return color.x & ~CLR_MASK
    if mode == CLR_BRIGHT:
        return (color.x & ~CLR_MASK) + 8
    if mode == CLR_256:
        return color.extra[0]
    return -1


def _class_for(color, classes, background):
    index = _color_to_8bit(color)
    if index >= 0 and len(classes) // 2 > index:
        return classes[index * 2 + background]
    return None


def _colors_differ(left, right):
    left_mode = left.x
    right_mode = right.x
    wide = left_mode & (CLR_256 | CLR_TRU)
    true = left_mode & CLR_TRU
    return (
        left_mode != right_mode
        or (wide and left.extra[0] != right.extra[0])
        or (true and left.extra[1] != right.extra[1])
        or (true and left.extra[2] != right.extra[2])
    )


def _sgr_colors_differ(left, right):
    return _colors_differ(left.color, right.color) or _colors_differ(left.bgcol, right.bgcol)


def _has_color(sgr):
    return bool(sgr.color.x or sgr.bgcol.x)


def _has_html_style(sgr):
    return bool((sgr.style & STL_MASK2) or sgr.color.x or sgr.bgcol.x)


def _sgr_changed(target, current):
    invert_diff = (target.style & STL_INVERT) ^ (current.style & STL_INVERT)
    return bool(
        _sgr_colors_differ(target, current)
        or ((target.style & STL_MASK2) != (current.style & STL_MASK2))
        or (_has_color(target) and invert_diff)
    )


def _url_piece(url, offset):
    if url.string is None or not offset.len:
        return b""
    start = offset.start
    return bytes(url.string[start:start + offset.len])


def _url_active(url):
    return url.url.len > 0


def _url_changed(target, current):
    target_url = _url_piece(target, target.url)
    current_url = _url_piece(current, current.url)
    target_id = _url_piece(target, target.id)
    urls_equal = len(target_url) == len(current_url) and (
        not target_url or target_url == current_url
    )
    ids_equal = len(target_id) == len(_url_piece(current, current.id)) and (
        (not target_url and not target_id)
        or (target_id and target_id == _url_piece(current, current.id))
    )
    return not (urls_equal and ids_equal)


def _state_as_html(out, state, previous, classes):
    sgr = state.fmt.sgr
    changed = _sgr_changed(sgr, previous.fmt.sgr) or _url_changed(
        state.fmt.url, previous.fmt.url
    )
    if not changed:
        return
    if _has_html_style(previous.fmt.sgr):
        out += b"</span>"
    if _url_active(previous.fmt.url):
        out += b"</a>"
    if _url_active(state.fmt.url):
        out += b"<a href='"
        out += _url_piece(state.fmt.url, state.fmt.url.url)
        out += b"'>"
    if not _has_html_style(sgr):
        return
    out += b"<span"
    invert = sgr.style & STL_INVERT
    color = sgr.bgcol if invert else sgr.color
    background = sgr.color if invert else sgr.bgcol
    color_class = _class_for(color, classes, 0)
    background_class = _class_for(background, classes, 1)
    if color_class or background_class:
        out += b" class='"
        if color_class:
            out += color_class.encode("ascii")
        if color_class and background_class:
            out += b" "
        if background_class:
            out += background_class.encode("ascii")
        out += b"'"
    needs_style = bool(sgr.style & STL_MASK2) or (
        (color.x and not color_class) or (background.x and not background_class)
    )
    if needs_style:
        out += b" style='"
        written = False
        if color.x and not color_class:
            out += b"color: "
            out += color_to_html(color).encode("ascii")
            written = True
        if background.x and not background_class:
            if written:
                out += b"; "
            out += b"background-color: "
            out += color_to_html(background).encode("ascii")
            written = True
        for bit in range(9):
            if sgr.style & STL_MASK2 & (1 << bit):
                if written:
                    out += b"; "
                out += _CSS_STYLE[bit].encode("ascii")
                written = True
        out += b";'"
    out += b">"


def _find_esc(data, pos, warned, index):
    limit = len(data)
    while pos < limit:
        byte = data[pos]
        if byte == 0 or byte == 0x1B:
            break
        if byte in (ord("<"), ord(">")) and not warned[0]:
            _warn(
                "`x` contains unescaped HTML special character "
                f"'{chr(byte)}' at index [{index + 1}] (see ?html_esc); "
                "you can use `warn=FALSE` to turn off these warnings."
            )
            warned[0] = True
        pos += 1
    if pos >= limit or data[pos] == 0:
        return len(data) if pos >= limit or data[pos] != 0 else pos
    return pos


def _convert_one(data, state, template, classes, index, warn_unescaped):
    """One string. `state` already holds the carried format and this buffer."""
    state.pos_x = 0
    state.pos_w = 0
    state.status &= ~STAT_WARNED
    previous = template.copy()
    out = bytearray()
    if data and data[0] != 0x1B and (
        _has_html_style(state.fmt.sgr) or _url_active(state.fmt.url)
    ):
        _state_as_html(out, state, previous, classes)
        previous = state.copy()
    non_error = (state.settings & WARN_MASK & ~WARN_ERROR) == 0
    warned = [non_error or not warn_unescaped]
    pos = 0
    limit = len(data)
    while True:
        trail_span = _has_html_style(previous.fmt.sgr)
        trail_anchor = _url_active(previous.fmt.url)
        nxt = _find_esc(data, pos, warned, index)
        if nxt > limit:
            nxt = limit
        # A C string ends at the first NUL, which is not copied.
        if nxt < limit and data[nxt] == 0:
            nxt_copy = nxt
            at_escape = False
        else:
            nxt_copy = nxt
            at_escape = nxt < limit and data[nxt] == 0x1B
        out += data[pos:nxt_copy]
        pos = nxt
        if not at_escape:
            if trail_span:
                out += b"</span>"
            if trail_anchor:
                out += b"</a>"
            break
        state.pos_x = pos
        read_next(state, index, "x")
        pos = state.pos_x
        if pos < limit and (pos >= len(data) or data[pos] != 0):
            _state_as_html(out, state, previous, classes)
        previous.become(state)
        if pos >= limit or (pos < len(data) and data[pos] == 0):
            if trail_span:
                out += b"</span>"
            if trail_anchor:
                out += b"</a>"
            break
    # The next element carries the format left by the last escape.
    state.fmt = previous.fmt.copy()
    if previous.fmt.url.string is not None:
        state.fmt.url.string = previous.fmt.url.string
    return bytes(out).decode("utf-8", "surrogateescape")


def _carry_format(carry_text, warn_int, term_cap_int):
    probe = [carry_text if carry_text else ""]
    carried = state_init_full(
        probe, warn_int, term_cap_int, True, True, 0, [1], 0
    )
    read_all(carried, 0, "carry")
    reset_pos(carried)
    return carried


def _to_html(x, warn, term_cap, classes, carry, warn_unescaped):
    warn = resolve_warn(warn, _MISSING)
    if term_cap is _MISSING:
        stored = option("fansi.term.cap", None)
        term_cap = dflt_term_cap() if stored is None else stored
    if carry is _MISSING:
        carry = True
    texts = coerce_texts(x)
    checked = prepare(
        x=texts,
        warn=warn,
        term_cap=term_cap,
        carry=carry,
        warn_mask=WARN_MASK,
        coerce_x=False,
    )
    class_names = _as_class_vector(classes)
    do_carry = checked["carry"] is not None
    warn_int = checked["warn_int"]
    term_int = checked["term_cap_int"]
    template = state_init_full([""], warn_int, term_int, True, False, 0, [1], 0)
    carried = _carry_format(
        checked["carry"] if do_carry else "", warn_int, term_int
    )
    out = list(texts)
    any_na = False
    previous = template.copy()
    previous.fmt = carried.fmt.copy()
    for index, text in enumerate(texts):
        if text is None or (any_na and do_carry):
            out[index] = None
            any_na = True
            continue
        if do_carry:
            state = previous.copy()
        else:
            state = template.copy()
        state.string = text.encode("utf-8", "surrogateescape")
        state.settings = template.settings
        converted = _convert_one(
            state.string, state, template, class_names, index, warn_unescaped
        )
        out[index] = converted
        previous = state
    return out


def to_html(x, warn=_MISSING, term_cap=_MISSING, classes=False, carry=_MISSING):
    """CSI SGR and OSC hyperlinks as SPAN and A tags. `carry` defaults to TRUE."""
    return _to_html(x, warn, term_cap, classes, carry, True)


def sgr_to_html(x, warn=_MISSING, term_cap=_MISSING, classes=False, carry=_MISSING):
    """`to_html` limited to the same sequences, without the unescaped `<`/`>` warning."""
    return _to_html(x, warn, term_cap, classes, carry, False)
