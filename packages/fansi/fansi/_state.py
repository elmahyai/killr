"""SGR and position state from fansi src/state.c."""

from __future__ import annotations

from fansi._args import FansiError
from fansi._const import (
    CLR_256,
    CLR_TRU,
    CTL_ALL,
    FONT_ALL,
    FONT_START,
    SET_ALLOWNA,
    SET_CTL,
    SET_KEEPNA,
    SET_TERMCAP,
    SET_TERMOLD,
    SET_WIDTH,
    STAT_WARNED,
    TERM_ALL,
    ctl_as_int,
    set_range,
    term_cap_as_int,
)

INT_MAX = 2147483647


class Offset:
    """Byte offset into the original string, the way FANSI_offset stores it."""

    __slots__ = ("start", "len")

    def __init__(self, start=0, length=0):
        self.start = start
        self.len = length

    def copy(self):
        return Offset(self.start, self.len)


class Color:
    """One foreground or background color."""

    __slots__ = ("x", "extra")

    def __init__(self, x=0, extra=None):
        self.x = x
        self.extra = [0, 0, 0] if extra is None else list(extra)

    def copy(self):
        return Color(self.x, self.extra)


class Sgr:
    """Active Select Graphic Rendition."""

    __slots__ = ("color", "bgcol", "style")

    def __init__(self):
        self.color = Color()
        self.bgcol = Color()
        self.style = 0

    def copy(self):
        other = Sgr()
        other.color = self.color.copy()
        other.bgcol = self.bgcol.copy()
        other.style = self.style
        return other


class Url:
    """OSC 8 hyperlink. `string` is the source buffer the offsets point into."""

    __slots__ = ("string", "url", "id")

    def __init__(self, string=None):
        self.string = string
        self.url = Offset()
        self.id = Offset()

    def copy(self):
        other = Url(self.string)
        other.url = self.url.copy()
        other.id = self.id.copy()
        return other


class Format:
    """SGR and URL active at one position."""

    __slots__ = ("sgr", "url")

    def __init__(self):
        self.sgr = Sgr()
        self.url = Url()

    def copy(self):
        other = Format()
        other.sgr = self.sgr.copy()
        other.url = self.url.copy()
        return other


class State:
    """Parse position for one string.

    `string` is bytes, or a str that is encoded to UTF-8 on first read.
    `pos_x` is the next unread byte. `pos_w` is the width already consumed.
    `fmt` holds the active SGR and URL. `utf8` is the byte just after the
    last UTF-8 character that was read.
    """

    __slots__ = ("settings", "status", "string", "pos_x", "pos_w", "fmt", "utf8")

    def __init__(self):
        self.settings = 0
        self.status = 0
        self.string = b""
        self.pos_x = 0
        self.pos_w = 0
        self.fmt = Format()
        self.utf8 = 0

    def copy(self):
        other = State()
        other.settings = self.settings
        other.status = self.status
        other.string = self.string
        other.pos_x = self.pos_x
        other.pos_w = self.pos_w
        other.fmt = self.fmt.copy()
        other.utf8 = self.utf8
        return other

    def become(self, other):
        """Replace this state with a snapshot. Later edits to either stay separate."""
        self.settings = other.settings
        self.status = other.status
        self.string = other.string
        self.pos_x = other.pos_x
        self.pos_w = other.pos_w
        self.fmt = other.fmt.copy()
        self.utf8 = other.utf8

    def ensure_bytes(self):
        """Store `string` as bytes and return that buffer."""
        text = self.string
        if text is None:
            self.string = b""
        elif isinstance(text, str):
            self.string = text.encode("utf-8", "surrogateescape")
        elif not isinstance(text, (bytes, bytearray)):
            raise FansiError("Internal error: state string is not bytes or str.")
        return self.string

    def at(self, index):
        """Byte at `index`, or 0 past either end, like a C string."""
        data = self.string
        if data is None or index < 0 or index >= len(data):
            return 0
        return data[index]


def _as_bytes(text):
    if text is None:
        return b""
    if isinstance(text, str):
        return text.encode("utf-8", "surrogateescape")
    if isinstance(text, (bytes, bytearray)):
        return bytes(text)
    raise FansiError("Internal error: state string is not bytes or str.")


def _element(x, index):
    if index < 0 or index >= len(x):
        raise FansiError(
            "Internal error: state_init with out of bounds index "
            f"[{index + 1}] for strsxp."
        )
    return x[index]


def state_init_full(x, warn, term_cap, allow_na, keep_na, width, ctl, index):
    """Build a State for element `index` of character vector `x`.

    `warn` is the shifted warning mask. `term_cap` and `ctl` are 1-based
    match() indexes. `width` is the 0-based count mode. `keep_na` may be
    None, which is R's NA and still sets the keep-NA bit.
    """
    text = _element(x, index)
    data = _as_bytes(text)
    if len(data) > INT_MAX:
        raise FansiError(
            "Strings longer than INT_MAX not supported "
            f"(length {len(data)} at index {index + 1})."
        )
    term_raw = term_cap_as_int(term_cap)
    settings = 0
    if term_raw > TERM_ALL:
        settings |= SET_TERMOLD
    settings = set_range(settings, SET_TERMCAP, TERM_ALL, term_raw & TERM_ALL)
    settings = set_range(settings, SET_WIDTH, 3, int(width))
    settings = set_range(settings, SET_CTL, CTL_ALL, ctl_as_int(ctl))
    if allow_na:
        settings |= SET_ALLOWNA
    if keep_na is None or keep_na:
        settings |= SET_KEEPNA
    settings |= int(warn) & 0xFFFFFFFF
    state = State()
    state.string = data
    state.settings = settings
    return state


def state_reinit(state, x, index):
    """Point `state` at element `index` and clear position, format, and status."""
    text = _element(x, index)
    data = _as_bytes(text)
    if len(data) > INT_MAX:
        raise FansiError(
            "Strings longer than INT_MAX not supported "
            f"(length {len(data)} at index {index + 1})."
        )
    state.string = data
    reset_state(state)


def state_init(x, warn, term_cap, index):
    """State that treats every escape as special and does not measure width."""
    return state_init_full(x, warn, term_cap, True, False, 0, [1], index)


def state_init_ctl(x, warn, ctl, index):
    """State for has/strip: all terminal caps, character width, selected ctl."""
    return state_init_full(x, warn, [1], True, False, 0, ctl, index)


def reset_width(state):
    state.pos_w = 0


def reset_pos(state):
    """Clear the position counters and keep a warning that was already issued."""
    state.pos_x = 0
    state.pos_w = 0
    warned = state.status & STAT_WARNED
    state.status = STAT_WARNED if warned else 0


def reset_state(state):
    """Clear format, position, status, and the UTF-8 mark. Settings stay."""
    state.fmt = Format()
    state.pos_x = 0
    state.pos_w = 0
    state.status = 0
    state.utf8 = 0


# Bits 20-24 hold the alternate font. Color mode lives in the high nibble.
FONT_MASK = FONT_ALL << FONT_START
CLR_MASK = 240


def offset_bytes(base, offset):
    """Bytes an Offset selects. An empty span is empty."""
    if base is None or offset.len <= 0:
        return b""
    return base[offset.start:offset.start + offset.len]


def _colors_differ(target, current):
    """True when two colors are not the same, including 256 and truecolor bytes."""
    tclr = target.x
    cclr = current.x
    wide = tclr & (CLR_256 | CLR_TRU)
    tru = tclr & CLR_TRU
    return (
        tclr != cclr
        or (wide and target.extra[0] != current.extra[0])
        or (tru and target.extra[1] != current.extra[1])
        or (tru and target.extra[2] != current.extra[2])
    )


def sgr_comp_color(target, current):
    """1 when foreground or background differs."""
    return int(
        _colors_differ(target.color, current.color)
        or _colors_differ(target.bgcol, current.bgcol)
    )


def sgr_setdiff(old, new, mode):
    """Styles in `old` that are missing from `new`.

    `mode` 0 closes a color or font that the new state replaces. `mode` 1
    closes them only when the new state turns them off.
    """
    res = Sgr()
    if (not mode and _colors_differ(old.color, new.color)) or (
        mode and old.color.x and not new.color.x
    ):
        res.color = old.color.copy()
    if (not mode and _colors_differ(old.bgcol, new.bgcol)) or (
        mode and old.bgcol.x and not new.bgcol.x
    ):
        res.bgcol = old.bgcol.copy()
    font_old = old.style & FONT_MASK
    font_new = new.style & FONT_MASK
    if (not mode and font_old != font_new) or (mode and font_old and not font_new):
        res.style = (res.style & ~FONT_MASK) | font_old
    style_old = old.style & ~FONT_MASK
    style_new = new.style & ~FONT_MASK
    res.style |= style_old & ~style_new
    return res


def sgr_intersect(old, new):
    """Styles present in both states.

    An equal font is not copied: state.c applies `&=` to a zeroed style word,
    so the font bits stay clear.
    """
    res = Sgr()
    if old.color.x == new.color.x:
        res.color = new.color.copy()
    if old.bgcol.x == new.bgcol.x:
        res.bgcol = new.bgcol.copy()
    font_old = old.style & FONT_MASK
    font_new = new.style & FONT_MASK
    if font_old == font_new:
        res.style &= font_new | ~FONT_MASK
    style_old = old.style & ~FONT_MASK
    style_new = new.style & ~FONT_MASK
    res.style |= style_old & style_new
    return res


def sgr_active(sgr):
    """1 when any style bit or color is on."""
    return 1 if (sgr.style or sgr.color.x or sgr.bgcol.x) else 0


def url_active(url):
    """1 when an OSC 8 URL has a non-empty target. An id alone is inactive."""
    return 1 if url.url.len > 0 else 0


def url_comp(target, current):
    """0 when both the URL and the id are the same, otherwise 1.

    An empty id does not count as the same id when a URL is present. Two
    empty URLs compare equal.
    """
    url_eq = target.url.len == current.url.len and (
        not target.url.len
        or offset_bytes(target.string, target.url) == offset_bytes(current.string, current.url)
    )
    id_eq = target.id.len == current.id.len and (
        (not target.url.len and not target.id.len)
        or (
            target.id.len
            and offset_bytes(target.string, target.id) == offset_bytes(current.string, current.id)
        )
    )
    return 0 if url_eq and id_eq else 1
