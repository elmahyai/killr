"""Text and Windows progress bars from utils 4.5.0.

``txtProgressBar`` writes the same console text as R. ``winProgressBar``
keeps the value, title, and label from the Windows C code. This host has
no Win32 window, so the dialog is not drawn.
"""

from __future__ import annotations

import math
import sys
from typing import TextIO


class ProgressError(Exception):
    """An error raised by a progress bar, matching R's stop message."""


WIDTH = 80

_OPEN = "\u201c"
_CLOSE = "\u201d"


class TxtProgressBar:
    """The list R stores under class ``txtProgressBar``."""

    def __init__(self, get_val, up, kill) -> None:
        self.getVal = get_val
        self.up = up
        self.kill = kill
        self.classes = ("txtProgressBar",)

    def __repr__(self) -> str:
        return "TxtProgressBar()"


class WinProgressBar:
    """The state behind class ``winProgressBar``. There is no window here."""

    def __init__(self, title: str, label: str, minimum: float, maximum: float, value: float, width: int) -> None:
        self.title = title
        self.label = label
        self.has_label = label != ""
        self.minimum = minimum
        self.maximum = maximum
        self.value = value
        self.width = width
        self.closed = False
        self.classes = ("winProgressBar",)

    def position(self) -> int:
        span = self.maximum - self.minimum
        if span == 0:
            return 0
        return int(self.width * (self.value - self.minimum) / span)

    def __repr__(self) -> str:
        return f"WinProgressBar(value={self.value})"


def txtProgressBar(
    min=0,
    max=1,
    initial=0,
    char="=",
    width=None,
    title=None,
    label=None,
    style=1,
    file="",
):
    """Draw a text progress bar. ``title`` and ``label`` are accepted and ignored."""
    del title, label
    stream = _open_file(file)
    style = _style(style)
    if not isinstance(char, str):
        raise ProgressError("nchar() requires a character vector")
    nw = _display_width(char)
    if nw == 0:
        raise ProgressError("'char' must have a non-zero width")
    minimum = float(min)
    maximum = float(max)
    if maximum <= minimum:
        raise ProgressError("must have 'max' > 'min'")
    if width is None or (isinstance(width, float) and math.isnan(width)):
        bar_width = WIDTH
        if style == 3:
            bar_width -= 10
        if nw > 1:
            bar_width = math.trunc(bar_width / nw)
    else:
        bar_width = int(width)
    state = {"value": float(initial), "nb": 0, "pc": -1, "killed": False}

    def up1(value: float) -> None:
        if not _in_range(value, minimum, maximum):
            return
        state["value"] = value
        nb = _blocks(bar_width, value, minimum, maximum)
        if state["nb"] < nb:
            stream.write(char * (nb - state["nb"]))
            _flush(stream)
        elif state["nb"] > nb:
            stream.write("\r" + (" " * (state["nb"] * nw)) + "\r" + (char * nb))
            _flush(stream)
        state["nb"] = nb

    def up2(value: float) -> None:
        if not _in_range(value, minimum, maximum):
            return
        state["value"] = value
        nb = _blocks(bar_width, value, minimum, maximum)
        if state["nb"] <= nb:
            stream.write("\r" + (char * nb))
            _flush(stream)
        else:
            stream.write("\r" + (" " * (state["nb"] * nw)) + "\r" + (char * nb))
            _flush(stream)
        state["nb"] = nb

    def up3(value: float) -> None:
        if not _in_range(value, minimum, maximum):
            return
        state["value"] = value
        nb = _blocks(bar_width, value, minimum, maximum)
        pc = round(100 * (value - minimum) / (maximum - minimum))
        if nb == state["nb"] and pc == state["pc"]:
            return
        stream.write("\r  |" + (" " * (nw * bar_width + 6)))
        body = "\r  |" + (char * nb) + (" " * (nw * (bar_width - nb))) + f"| {pc:3d}%"
        stream.write(body)
        _flush(stream)
        state["nb"] = nb
        state["pc"] = pc

    def get_val() -> float:
        return state["value"]

    def kill() -> None:
        if not state["killed"]:
            stream.write("\n")
            _flush(stream)
            state["killed"] = True

    up = (up1, up2, up3)[style - 1]
    up(float(initial))
    return TxtProgressBar(get_val, up, kill)


def getTxtProgressBar(pb) -> float:
    """Return the current value of a text progress bar."""
    _require_txt(pb)
    return pb.getVal()


def setTxtProgressBar(pb, value, title=None, label=None) -> float:
    """Update a text progress bar and return the previous value."""
    del title, label
    _require_txt(pb)
    old = pb.getVal()
    pb.up(float(value))
    return old


def winProgressBar(
    title="R progress bar",
    label="",
    min=0,
    max=1,
    initial=0,
    width=300,
):
    """Keep a Windows progress-bar value. No dialog is drawn on this host."""
    title_text = _required_string(title, "title")
    label_text = _required_string(label, "label")
    minimum = _finite(min, "min")
    maximum = _finite(max, "max")
    start = _finite(initial, "initial")
    pixels = _width(width)
    return WinProgressBar(title_text, label_text, minimum, maximum, start, pixels)


def getWinProgressBar(pb) -> float:
    """Return the current Windows progress-bar value."""
    return setWinProgressBar(pb, None)


def setWinProgressBar(pb, value, title=None, label=None) -> float:
    """Update a Windows progress bar and return the previous value."""
    _require_win(pb)
    if pb.closed:
        raise ProgressError("invalid progressbar -- has it been closed?")
    old = pb.value
    if value is not None:
        number = float(value)
        if math.isfinite(number) and pb.minimum <= number <= pb.maximum:
            pb.value = number
    if title is not None:
        pb.title = _required_string(title, "title")
    if label is not None and pb.has_label:
        pb.label = _required_string(label, "label")
    return old


def close(con, *args):
    """Close a progress bar. Other objects have no ``close`` method here."""
    del args
    if isinstance(con, TxtProgressBar):
        con.kill()
        return None
    if isinstance(con, WinProgressBar):
        con.closed = True
        return None
    raise ProgressError(f"no applicable method for 'close' applied to an object of class {type(con).__name__}")


def _require_txt(pb) -> None:
    if not isinstance(pb, TxtProgressBar):
        raise ProgressError(f"'pb' is not from class {_OPEN}txtProgressBar{_CLOSE}")


def _require_win(pb) -> None:
    if not isinstance(pb, WinProgressBar):
        raise ProgressError(f"'pb' is not from class {_OPEN}winProgressBar{_CLOSE}")


def _open_file(file) -> TextIO:
    if file == "":
        return sys.stdout
    if hasattr(file, "write") and not getattr(file, "closed", False):
        return file
    raise ProgressError('\'file\' must be "" or an open connection object')


def _style(style) -> int:
    values = list(style) if isinstance(style, (list, tuple)) else [style]
    if len(values) != 1:
        raise ProgressError("the condition has length > 1")
    number = values[0]
    if number in (1, 2, 3, 1.0, 2.0, 3.0) or number is True:
        return int(number)
    return 1


def _display_width(text: str) -> int:
    """``nchar(type = "width")`` for the characters a bar is drawn with."""
    width = 0
    for char in text:
        code = ord(char)
        if code < 32 or code == 127:
            continue
        width += 2 if 0x1100 <= code <= 0x115F or 0x2E80 <= code <= 0x9FFF or 0xAC00 <= code <= 0xD7A3 or 0xF900 <= code <= 0xFAFF or 0xFE10 <= code <= 0xFE6F or 0xFF00 <= code <= 0xFF60 else 1
    return width


def _in_range(value: float, minimum: float, maximum: float) -> bool:
    return math.isfinite(value) and minimum <= value <= maximum


def _blocks(width: int, value: float, minimum: float, maximum: float) -> int:
    return round(width * (value - minimum) / (maximum - minimum))


def _flush(stream: TextIO) -> None:
    flush = getattr(stream, "flush", None)
    if flush is not None:
        flush()


def _required_string(value, name: str) -> str:
    # NULL becomes character(0). A missing string is not a Python str here.
    if not isinstance(value, str):
        raise ProgressError(f"invalid '{name}' argument")
    return value


def _finite(value, name: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ProgressError(f"invalid '{name}' argument") from None
    if not math.isfinite(number):
        raise ProgressError(f"invalid '{name}' argument")
    return number


def _width(width) -> int:
    try:
        if width is None or (isinstance(width, float) and math.isnan(width)):
            return 200
        number = int(width)
    except (TypeError, ValueError):
        return 200
    if number < 0:
        return 200
    return number
