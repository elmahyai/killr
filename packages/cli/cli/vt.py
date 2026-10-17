"""A small VT screen: printable text, newline, carriage return, and SGR."""

from __future__ import annotations

from cli.ansi_text import _AnsiState, _update_sgr, _walk


class _Pen:
    def __init__(self):
        self.fg = 0
        self.bg = 0
        self.fg_text = ""
        self.bg_text = ""
        self.bold = False
        self.italic = False
        self.underline = False
        self.strikethrough = False
        self.blink = False
        self.inverse = False

    def label(self) -> str:
        parts = []
        if self.fg_text:
            parts.append(self.fg_text)
        if self.bg_text:
            parts.append(self.bg_text)
        if self.bold:
            parts.append("bold;")
        if self.italic:
            parts.append("italic;")
        if self.underline:
            parts.append("underline;")
        if self.strikethrough:
            parts.append("strikethrough;")
        if self.blink:
            parts.append("blink;")
        if self.inverse:
            parts.append("inverse;")
        return "".join(parts)

    def empty(self) -> bool:
        return self.label() == ""


def _pen_from_sgr(state: _AnsiState) -> _Pen:
    pen = _Pen()
    fg = state.new.fg
    bg = state.new.bg
    if fg.col == 254:
        pen.fg = fg.col
        pen.fg_text = f"fg:{fg.r};"
    elif fg.col == 255:
        pen.fg = fg.col
        pen.fg_text = f"fg:#{fg.r:02x}{fg.g:02x}{fg.b:02x};"
    elif 30 <= fg.col <= 37:
        pen.fg = fg.col
        pen.fg_text = f"fg:{fg.col - 30};"
    elif 90 <= fg.col <= 97:
        pen.fg = fg.col
        pen.fg_text = f"fg:{fg.col - 90 + 8};"
    if bg.col == 254:
        pen.bg = bg.col
        pen.bg_text = f"bg:{bg.r};"
    elif bg.col == 255:
        pen.bg = bg.col
        pen.bg_text = f"bg:#{bg.r:02x}{bg.g:02x}{bg.b:02x};"
    elif 40 <= bg.col <= 47:
        pen.bg = bg.col
        pen.bg_text = f"bg:{bg.col - 40};"
    elif 100 <= bg.col <= 107:
        pen.bg = bg.col
        pen.bg_text = f"bg:{bg.col - 100 + 8};"
    pen.bold = bool(state.new.bold)
    pen.italic = bool(state.new.italic)
    pen.underline = bool(state.new.underline)
    pen.strikethrough = bool(state.new.crossedout)
    pen.blink = bool(state.new.blink)
    pen.inverse = bool(state.new.inverse)
    return pen


def _capture(label: str, pattern: str):
    import re

    match = re.search(pattern, label)
    return match.group(1) if match else None


def vt_output(output, width: int = 80, height: int = 25):
    """Replay output onto a width-by-height screen and return the runs."""

    if isinstance(output, (bytes, bytearray)):
        text = bytes(output).decode("latin1")
    elif isinstance(output, (list, tuple)):
        text = "".join(output)
    else:
        text = "" if output is None else str(output)
    width = int(width)
    height = int(height)
    screen = [[(32, "") for _ in range(width)] for _ in range(height)]
    x = y = 0
    state = _AnsiState()
    pen = _Pen()

    def put(ch: str) -> None:
        nonlocal x, y
        if y >= height:
            return
        if x >= width:
            x = 0
            y += 1
            if y >= height:
                return
        screen[y][x] = (ord(ch), pen.label())
        x += 1

    for event in _walk(text):
        kind = event[0]
        if kind == "text":
            for char in event[1]:
                if char == "\n":
                    x = 0
                    y += 1
                elif char == "\r":
                    x = 0
                elif char >= " ":
                    put(char)
        elif kind == "sgr":
            _update_sgr(state, event[1], event[2], [])
            pen = _pen_from_sgr(state)
            state.old = state.new.clone()
        elif kind == "csi":
            continue
    rows = []
    for lineno, line in enumerate(screen, start=1):
        chars = "".join(chr(ch) for ch, _pen in line)
        labels = [cell[1] for cell in line]
        runs = []
        start = 0
        for index in range(1, len(labels) + 1):
            if index == len(labels) or labels[index] != labels[start]:
                runs.append((start, index, labels[start]))
                start = index
        for segmentno, (start, end, label) in enumerate(runs, start=1):
            segment = chars[start:end]
            rows.append(
                {
                    "lineno": lineno,
                    "segmentno": segmentno,
                    "segment": segment,
                    "bold": "bold;" in label,
                    "italic": "italic;" in label,
                    "underline": "underline;" in label,
                    "strikethrough": "strikethrough;" in label,
                    "blink": "blink;" in label,
                    "inverse": "inverse;" in label,
                    "color": _capture(label, r"fg:([0-9]+|#[0-9a-f]+);"),
                    "background_color": _capture(label, r"bg:([0-9]+|#[0-9a-f]+);"),
                }
            )
    return rows
