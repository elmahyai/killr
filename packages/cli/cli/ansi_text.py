"""ANSI escape scanning for strip, detection, and visible length.

The scanner follows clic__ansi_iterator: CSI ending in m is SGR, any
other CSI is a control sequence, and OSC 8 is a hyperlink. Counts then
use the same grapheme and width rules as utf8_nchar.
"""

from __future__ import annotations

import os

from cli.utf8 import (
    _TYPES,
    _as_int,
    _as_text,
    _match_arg,
    _measure,
    _scalar,
    _vector,
    graphemes,
)

_ANSI_REGEX = (
    "(?:(?:\\x{001b}\\[)|\\x{009b})"
    "(?:(?:[0-9]{1,3})?(?:(?:;[0-9]{0,3})*)?[A-M|f-m])"
    "|\\x{001b}[A-M]"
    "|\\x{001b}\\]8;.*?;.*?\\x{001b}\\\\"
    "|\\x{001b}\\]8;.*?;.*?\\x{0007}"
)


def ansi_regex() -> str:
    """The Perl pattern cli publishes for ANSI escapes."""

    return _ANSI_REGEX


def _flag(value, name: str) -> bool:
    if not isinstance(value, bool):
        raise TypeError(f"{name} must be TRUE or FALSE")
    return value


def _events(text: str):
    """Yield ('text'|'sgr'|'csi'|'link', piece) for one string."""

    n = len(text)
    i = 0
    shaft = 0
    while i < n:
        if text[i] == "\x1b" and i + 1 < n and text[i + 1] == "[":
            start = i
            intermed = i + 2
            while intermed < n and 0x30 <= ord(text[intermed]) <= 0x3F:
                intermed += 1
            end = intermed
            while end < n and 0x20 <= ord(text[end]) <= 0x2F:
                end += 1
            if start > shaft:
                yield "text", text[shaft:start]
            if end >= n:
                yield "csi", text[start:]
                shaft = n
                i = n
            else:
                kind = "sgr" if text[end] == "m" else "csi"
                yield kind, text[start : end + 1]
                shaft = end + 1
                i = end + 1
        elif (
            text[i] == "\x1b"
            and i + 3 < n
            and text[i + 1] == "]"
            and text[i + 2] == "8"
            and text[i + 3] == ";"
        ):
            start = i
            uri = i + 4
            while uri < n and text[uri] != ";":
                uri += 1
            uri = min(uri + 1, n)
            end = uri
            while end < n:
                if text[end] == "\x07":
                    break
                if text[end] == "\\" and end > 0 and text[end - 1] == "\x1b":
                    break
                end += 1
            if start > shaft:
                yield "text", text[shaft:start]
            if end >= n:
                yield "link", text[start:]
                shaft = n
                i = n
            else:
                yield "link", text[start : end + 1]
                shaft = end + 1
                i = end + 1
        else:
            i += 1
        while i < n and text[i] != "\x1b":
            i += 1
    if i > shaft:
        yield "text", text[shaft:i]


def ansi_has_any(string, sgr=True, csi=True, link=True):
    """Whether each string contains SGR, CSI, or hyperlink sequences."""

    want_sgr = _flag(sgr, "sgr")
    want_csi = _flag(csi, "csi")
    want_link = _flag(link, "link")
    out = []
    for value in _vector(string):
        text = _as_text(value)
        if text is None:
            out.append(None)
            continue
        found = False
        for kind, _piece in _events(text):
            if kind == "text":
                continue
            if (kind == "sgr" and want_sgr) or (kind == "csi" and want_csi) or (
                kind == "link" and want_link
            ):
                found = True
                break
        out.append(found)
    return _scalar(string, out)


def ansi_strip(string, sgr=True, csi=True, link=True):
    """Remove selected ANSI sequences. The result is plain text."""

    want_sgr = _flag(sgr, "sgr")
    want_csi = _flag(csi, "csi")
    want_link = _flag(link, "link")
    out = []
    for value in _vector(string):
        text = _as_text(value)
        if text is None:
            out.append(None)
            continue
        pieces = []
        removed = False
        for kind, piece in _events(text):
            drop = (
                (kind == "sgr" and want_sgr)
                or (kind == "csi" and want_csi)
                or (kind == "link" and want_link)
            )
            if drop:
                removed = True
                continue
            pieces.append(piece)
        out.append("".join(pieces) if removed else text)
    return _scalar(string, out)


class _Color:
    __slots__ = ("col", "r", "g", "b")

    def __init__(self, col=0, r=0, g=0, b=0):
        self.col = col
        self.r = r
        self.g = g
        self.b = b

    def clone(self):
        return _Color(self.col, self.r, self.g, self.b)

    def same(self, other) -> bool:
        return (
            self.col == other.col
            and self.r == other.r
            and self.g == other.g
            and self.b == other.b
        )


class _Link:
    __slots__ = ("param", "uri", "end")

    def __init__(self, param: str, uri: str, end: str):
        self.param = param
        self.uri = uri
        self.end = end


class _Sgr:
    __slots__ = (
        "fg",
        "bg",
        "bold",
        "faint",
        "italic",
        "underline",
        "blink",
        "inverse",
        "hide",
        "crossedout",
        "link",
    )

    def __init__(self):
        self.fg = _Color()
        self.bg = _Color()
        self.bold = 0
        self.faint = 0
        self.italic = 0
        self.underline = 0
        self.blink = 0
        self.inverse = 0
        self.hide = 0
        self.crossedout = 0
        self.link = None

    def clone(self):
        copied = _Sgr()
        copied.fg = self.fg.clone()
        copied.bg = self.bg.clone()
        copied.bold = self.bold
        copied.faint = self.faint
        copied.italic = self.italic
        copied.underline = self.underline
        copied.blink = self.blink
        copied.inverse = self.inverse
        copied.hide = self.hide
        copied.crossedout = self.crossedout
        copied.link = self.link
        return copied


class _AnsiState:
    def __init__(self):
        self.old = _Sgr()
        self.new = _Sgr()
        self.unknown = False
        self.off = False


def _strtol(text: str, start: int) -> tuple[int, int]:
    index = start
    if index < len(text) and text[index] in "+-":
        index += 1
    end = index
    while end < len(text) and text[end].isdigit():
        end += 1
    if end == index:
        return 0, start
    return int(text[start:end], 10), end


def _readnum(text: str, start: int, limit: int) -> tuple[int, int]:
    if start >= limit or text[start] != ";":
        return 0, start
    start += 1
    number, end = _strtol(text, start)
    if end == start:
        number = 0
        end = start
    while end < limit and text[end] != ";":
        end += 1
    return number, end


def _parse_color(text: str, start: int, limit: int, color: _Color) -> int:
    if (
        start + 2 >= limit
        or text[start] != ";"
        or text[start + 1] not in "25"
        or text[start + 2] != ";"
    ):
        color.r = color.g = color.b = 0
        return limit
    color.col = 254 if text[start + 1] == "5" else 255
    start += 2
    red, start = _readnum(text, start, limit)
    green = blue = 0
    if color.col == 255:
        green, start = _readnum(text, start, limit)
        blue, start = _readnum(text, start, limit)
    color.r = red & 0xFF
    color.g = green & 0xFF
    color.b = blue & 0xFF
    return start


def _update_sgr(state: _AnsiState, params: str, raw: str, buf: list[str]) -> None:
    index = 0
    limit = len(params)
    while True:
        number, end = _strtol(params, index)
        if end == index or number == 0:
            state.new = _Sgr()
            state.off = True
        elif number == 1:
            state.new.bold = 1
        elif number == 2:
            state.new.faint = 1
        elif number == 3:
            state.new.italic = 1
        elif number == 4:
            state.new.underline = 1
        elif number == 5:
            state.new.blink = 1
        elif number == 7:
            state.new.inverse = 1
        elif number == 8:
            state.new.hide = 1
        elif number == 9:
            state.new.crossedout = 1
        elif number == 22:
            state.new.bold = state.new.faint = 0
        elif number == 23:
            state.new.italic = 0
        elif number == 24:
            state.new.underline = 0
        elif number == 25:
            state.new.blink = 0
        elif number == 27:
            state.new.inverse = 0
        elif number == 28:
            state.new.hide = 0
        elif number == 29:
            state.new.crossedout = 0
        elif (30 <= number <= 37) or (90 <= number <= 97):
            state.new.fg.col = number
        elif number == 38:
            end = _parse_color(params, end, limit, state.new.fg)
        elif number == 39:
            state.new.fg.col = 0
        elif (40 <= number <= 47) or (100 <= number <= 107):
            state.new.bg.col = number
        elif number == 48:
            end = _parse_color(params, end, limit, state.new.bg)
        elif number == 49:
            state.new.bg.col = 0
        else:
            state.unknown = True
            buf.append(raw)
        if end < limit and params[end] == ";":
            index = end + 1
            continue
        break


def _hyperlink_posix() -> bool:
    return os.environ.get("R_CLI_HYPERLINK_MODE") == "posix"


def _flush_state(buf: list[str], state: _AnsiState) -> None:
    if state.unknown and state.off:
        state.unknown = False
        state.off = False
        buf.append("\x1b[0m")
    old = state.old
    new = state.new
    if old.bg.col != 0 and new.bg.col != old.bg.col:
        buf.append("\x1b[49m")
    if old.fg.col != 0 and new.fg.col != old.fg.col:
        buf.append("\x1b[39m")
    if new.crossedout < old.crossedout:
        buf.append("\x1b[29m")
    if new.hide < old.hide:
        buf.append("\x1b[28m")
    if new.inverse < old.inverse:
        buf.append("\x1b[27m")
    if new.blink < old.blink:
        buf.append("\x1b[25m")
    if new.underline < old.underline:
        buf.append("\x1b[24m")
    if new.italic < old.italic:
        buf.append("\x1b[23m")
    if new.faint < old.faint:
        buf.append("\x1b[22m")
    if new.bold < old.bold:
        buf.append("\x1b[22m")
    if old.link is not None and new.link is not old.link:
        buf.append("\x1b]8;;\x1b\\" if _hyperlink_posix() else "\x1b]8;;\x07")
    if new.link is not None and new.link is not old.link:
        link = new.link
        buf.append("\x1b]8;")
        buf.append(link.param)
        buf.append(link.uri)
        buf.append("\x1b\\" if _hyperlink_posix() else "\x07")
    if new.bold > old.bold:
        buf.append("\x1b[1m")
    if new.faint > old.faint:
        buf.append("\x1b[2m")
    if new.italic > old.italic:
        buf.append("\x1b[3m")
    if new.underline > old.underline:
        buf.append("\x1b[4m")
    if new.blink > old.blink:
        buf.append("\x1b[5m")
    if new.inverse > old.inverse:
        buf.append("\x1b[7m")
    if new.hide > old.hide:
        buf.append("\x1b[8m")
    if new.crossedout > old.crossedout:
        buf.append("\x1b[9m")
    if new.fg.col != 0 and not new.fg.same(old.fg):
        if new.fg.col == 254:
            buf.append(f"\x1b[38;5;{new.fg.r}m")
        elif new.fg.col == 255:
            buf.append(f"\x1b[38;2;{new.fg.r};{new.fg.g};{new.fg.b}m")
        else:
            buf.append(f"\x1b[{new.fg.col}m")
    if new.bg.col != 0 and not new.bg.same(old.bg):
        if new.bg.col == 254:
            buf.append(f"\x1b[48;5;{new.bg.r}m")
        elif new.bg.col == 255:
            buf.append(f"\x1b[48;2;{new.bg.r};{new.bg.g};{new.bg.b}m")
        else:
            buf.append(f"\x1b[{new.bg.col}m")
    state.old = new.clone()


def _walk(text: str):
    """Yield text, sgr, csi, and link pieces. Positions match the C iterator."""

    n = len(text)
    i = 0
    shaft = 0
    while i < n:
        if text[i] == "\x1b" and i + 1 < n and text[i + 1] == "[":
            start = i
            intermed = i + 2
            while intermed < n and 0x30 <= ord(text[intermed]) <= 0x3F:
                intermed += 1
            end = intermed
            while end < n and 0x20 <= ord(text[end]) <= 0x2F:
                end += 1
            if start > shaft:
                yield ("text", text[shaft:start])
            if end >= n:
                yield ("csi", "", text[start:])
                shaft = n
                i = n
            else:
                raw = text[start : end + 1]
                params = text[start + 2 : intermed]
                kind = "sgr" if text[end] == "m" else "csi"
                yield (kind, params, raw)
                shaft = end + 1
                i = end + 1
        elif (
            text[i] == "\x1b"
            and i + 3 < n
            and text[i + 1] == "]"
            and text[i + 2] == "8"
            and text[i + 3] == ";"
        ):
            start = i
            uri = i + 4
            while uri < n and text[uri] != ";":
                uri += 1
            uri = min(uri + 1, n)
            end = uri
            while end < n:
                if text[end] == "\x07":
                    break
                if text[end] == "\\" and end > 0 and text[end - 1] == "\x1b":
                    break
                end += 1
            if start > shaft:
                yield ("text", text[shaft:start])
            if end >= n:
                yield ("link", text[start + 4 : uri], text[uri:], "", text[start:])
                shaft = n
                i = n
            else:
                yield (
                    "link",
                    text[start + 4 : uri],
                    text[uri:end],
                    text[end],
                    text[start : end + 1],
                )
                shaft = end + 1
                i = end + 1
        else:
            i += 1
        while i < n and text[i] != "\x1b":
            i += 1
    if i > shaft:
        yield ("text", text[shaft:i])


def _events(text: str):
    for event in _walk(text):
        kind = event[0]
        if kind == "text":
            yield "text", event[1]
        elif kind == "link":
            yield "link", event[4]
        else:
            yield kind, event[2]


def _close_state(buf: list[str], state: _AnsiState) -> None:
    state.new = _Sgr()
    _flush_state(buf, state)


def _styled_substr(text: str, start: int, stop: int) -> str:
    state = _AnsiState()
    buf: list[str] = []
    pos = 1
    for event in _walk(text):
        kind = event[0]
        if kind == "sgr":
            _update_sgr(state, event[1], event[2], buf)
            continue
        if kind == "link":
            param, uri, end = event[1], event[2], event[3]
            state.new.link = None if uri == "" else _Link(param, uri, end)
            continue
        if kind != "text":
            continue
        piece = event[1]
        clusters = graphemes(piece)
        index = 0
        if pos < start:
            while pos < start and index < len(clusters):
                index += 1
                pos += 1
        if pos <= stop and index < len(clusters):
            taken = []
            while pos <= stop and index < len(clusters):
                taken.append(clusters[index])
                index += 1
                pos += 1
            if taken:
                _flush_state(buf, state)
                buf.append("".join(taken))
        if pos > stop:
            _close_state(buf, state)
            return "".join(buf)
    _close_state(buf, state)
    return "".join(buf)


def ansi_substr(x, start, stop):
    """Substring by grapheme, keeping the ANSI styles that apply there."""

    values = _vector(x)
    if not values and isinstance(x, (list, tuple)):
        return []
    starts = _vector(start)
    stops = _vector(stop)
    if not starts or not stops:
        raise ValueError("start and stop must be non-empty")
    start_ints = [_as_int(item) for item in starts]
    stop_ints = [_as_int(item) for item in stops]
    if any(item is None for item in start_ints + stop_ints):
        raise ValueError("start and stop must not be NA")
    out = []
    for i, value in enumerate(values):
        text = _as_text(value)
        if text is None:
            out.append(None)
            continue
        out.append(
            _styled_substr(
                text,
                start_ints[i % len(start_ints)],
                stop_ints[i % len(stop_ints)],
            )
        )
    return _scalar(x, out)


def ansi_substring(text, first, last=1000000):
    """Like ansi_substr, recycling text to the longest index."""

    values = _vector(text)
    starts = [_as_int(item) for item in _vector(first)]
    stops = [_as_int(item) for item in _vector(last)]
    if not starts or not stops:
        raise ValueError("first and last must be non-empty")
    n = max(len(values), len(starts), len(stops))
    if values and len(values) < n:
        values = [values[i % len(values)] for i in range(n)]
    elif not values:
        return [] if isinstance(text, (list, tuple)) else ""
    out = []
    for i, value in enumerate(values):
        item = _as_text(value)
        if item is None:
            out.append(None)
            continue
        out.append(
            _styled_substr(
                item,
                starts[i % len(starts)],
                stops[i % len(stops)],
            )
        )
    return _scalar(text, out) if len(values) == 1 and not isinstance(text, (list, tuple)) else out


def ansi_simplify(x, csi="keep"):
    """Rewrite SGR tags from the current style state."""

    mode = _match_arg(csi, ("keep", "drop"))
    keep = mode == "keep"
    out = []
    for value in _vector(x):
        text = _as_text(value)
        if text is None:
            out.append(None)
            continue
        state = _AnsiState()
        buf: list[str] = []
        tags = 0
        for event in _walk(text):
            kind = event[0]
            if kind == "sgr":
                tags += 1
                _update_sgr(state, event[1], event[2], buf)
            elif kind == "csi":
                if keep:
                    buf.append(event[2])
                else:
                    tags += 1
            elif kind == "link":
                tags += 1
                param, uri, end = event[1], event[2], event[3]
                state.new.link = None if uri == "" else _Link(param, uri, end)
            else:
                _flush_state(buf, state)
                buf.append(event[1])
        _close_state(buf, state)
        out.append(text if tags == 0 else "".join(buf))
    return _scalar(x, out)


def ansi_nchar(x, type="chars"):
    """Count visible text, ignoring ANSI sequences."""

    kind = _match_arg(type, _TYPES)
    if kind == "chars":
        kind = "graphemes"
    out = []
    for value in _vector(x):
        text = _as_text(value)
        if text is None:
            out.append(None)
            continue
        total = 0
        for event, piece in _events(text):
            if event == "text":
                total += _measure(piece, kind)
        out.append(total)
    return _scalar(x, out)
