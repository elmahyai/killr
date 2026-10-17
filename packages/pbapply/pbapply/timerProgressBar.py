"""Console timer progress bar matching pbapply's timerProgressBar."""

from __future__ import annotations

import math
import sys
import time
from typing import Any, List, TextIO, Union

from pbapply.startpb import _TimerProgressBar
from pbapply.time import getTimeAsString

_BAD_RANGE = "must have 'max' > 'min'"
_BAD_FILE = "'file' must be \"\" or an open connection object"
_MIN_LETTERS = 17
_THROBBER = ("|", "/", "-", "\\")


def timerProgressBar(
    min: float = 0,
    max: float = 1,
    initial: float = 0,
    char: str = "=",
    width: float = float("nan"),
    *,
    title: Any = None,
    label: Any = None,
    style: int = 1,
    file: Union[str, TextIO] = "",
    min_time: float = 0,
) -> _TimerProgressBar:
    """Create a timer progress bar object like R's timerProgressBar."""
    del title, label
    out = _resolve_file(file)
    if max <= min:
        raise ValueError(_BAD_RANGE)
    if style not in range(1, 7):
        style = 1

    bar_char = _prepare_char(str(char), style)
    bar_width = _default_width() if math.isnan(width) else int(width)

    pb = _TimerProgressBarImpl(
        min=min,
        max=max,
        initial=initial,
        char=bar_char,
        width=bar_width,
        style=style,
        min_time=min_time,
        file=out,
    )
    pb.up(initial)
    return pb


class _TimerProgressBarImpl(_TimerProgressBar):
    def __init__(
        self,
        *,
        min: float,
        max: float,
        initial: float,
        char: Union[str, List[str]],
        width: int,
        style: int,
        min_time: float,
        file: TextIO,
    ) -> None:
        super().__init__(min=min, max=max, initial=initial)
        self._char = char
        self._width = width
        self._style = style
        self._min_time = float(min_time)
        self._file = file
        self._start = time.perf_counter()
        self._killed = False
        self._showpb = min_time <= 0
        self._counter = 1 if style in (2, 4) else 0

    def get_val(self) -> float:
        return self._value

    def up(self, value: float) -> None:
        _UPDATERS[self._style](self, value)

    def kill(self) -> None:
        if self._killed:
            return
        if self._showpb:
            self._file.write("\n")
            self._file.flush()
        self._killed = True
        self._closed = True


def _resolve_file(file: Union[str, TextIO]) -> TextIO:
    if file == "":
        return sys.stdout
    if hasattr(file, "write") and callable(getattr(file, "write")):
        if getattr(file, "closed", False) is False:
            return file  # type: ignore[return-value]
    raise ValueError(_BAD_FILE)


def _default_width() -> int:
    try:
        import shutil

        return int(shutil.get_terminal_size(fallback=(80, 24)).columns)
    except Exception:
        return 80


def _prepare_char(char: str, style: int) -> Union[str, List[str]]:
    if len(char) < 1:
        char = "="
    if len(char) > 1 and style in (1, 2, 3, 4):
        char = char[0]
    if len(char) > 4 and style in (5, 6):
        char = char[:4]
    if style not in (5, 6):
        return char

    width = len(char)
    if width == 1:
        parts = ["|", char, " ", "|"]
    elif width == 2:
        parts = [char[0], char[1], " ", char[0]]
    elif width == 3:
        parts = [char[0], char[1], char[2], char[0]]
    else:
        parts = [char[0], char[1], char[2], char[3]]
    if parts[1] == parts[2]:
        parts[2] = " "
    return parts


def _valid_value(pb: _TimerProgressBarImpl, value: float) -> bool:
    return math.isfinite(value) and pb._min <= value <= pb._max


def _elapsed(pb: _TimerProgressBarImpl) -> float:
    return time.perf_counter() - pb._start


def _remaining_time(pb: _TimerProgressBarImpl, time0: float) -> float:
    i = pb._value - pb._min
    n = pb._max - pb._min
    if i == 0:
        return math.nan
    return time0 / (i / n) - time0


def _maybe_show(pb: _TimerProgressBarImpl, time0: float, time_left: float) -> None:
    extra = time_left if math.isfinite(time_left) else 0.0
    if pb._value > pb._min and (time0 + extra) > pb._min_time:
        pb._showpb = True


def _pad_text(text: str) -> str:
    missing = _MIN_LETTERS - len(text)
    if missing > 0:
        text += " " * missing
    return text


def _percent_text(i: float, n: float) -> str:
    return f"{100 * i / n:2.0f}%"


def _txt_width(pb: _TimerProgressBarImpl) -> int:
    return max(pb._width, pb._width - _MIN_LETTERS - 4)


def _write_line(pb: _TimerProgressBarImpl, bar: str, text: str) -> None:
    pb._file.write(f"\r{bar}{text}")
    pb._file.flush()


def _style34_text(i: float, n: float, time0: float, time_left: float) -> str:
    prefix = " ~" if i != n else " elapsed="
    if i == 0:
        left_time = getTimeAsString(None)
    elif i != n:
        left_time = getTimeAsString(time_left)
    else:
        left_time = getTimeAsString(time0)
    return _pad_text(f"{_percent_text(i, n)}{prefix}{left_time}")


def _pipe_bar(pb: _TimerProgressBarImpl, i: float, n: float, txt_width: int) -> str:
    done = math.ceil(txt_width * i / n)
    fill = str(pb._char) * done
    empty = " " * (txt_width - done)
    return f" |{fill}{empty}|"


def _bracket_bar(pb: _TimerProgressBarImpl, i: float, n: float, txt_width: int) -> str:
    chars = pb._char
    assert isinstance(chars, list)
    done = math.ceil(txt_width * i / n)
    fill = chars[1] * done
    empty = chars[2] * (txt_width - done)
    return f" {chars[0]}{fill}{empty}{chars[3]}"


def _up1(pb: _TimerProgressBarImpl, value: float) -> None:
    if not _valid_value(pb, value):
        return
    time0 = _elapsed(pb)
    pb._value = float(value)
    i = pb._value - pb._min
    n = pb._max - pb._min
    time_left = _remaining_time(pb, time0)
    _maybe_show(pb, time0, time_left)
    if not pb._showpb:
        return
    txt_width = _txt_width(pb)
    spent = f" elapsed={getTimeAsString(time0)}"
    left = "" if i == 0 else f", remaining~{getTimeAsString(time_left)}"
    text = _pad_text(f"{_percent_text(i, n)}{spent}{left}")
    if txt_width <= 0:
        _write_line(pb, " ", text)
    else:
        _write_line(pb, _pipe_bar(pb, i, n, txt_width), text)


def _up2(pb: _TimerProgressBarImpl, value: float) -> None:
    if not _valid_value(pb, value):
        return
    time0 = _elapsed(pb)
    pb._value = float(value)
    i = pb._value - pb._min
    n = pb._max - pb._min
    time_left = _remaining_time(pb, time0)
    if i != 0:
        pb._counter += 1
    _maybe_show(pb, time0, time_left)
    if not pb._showpb:
        return
    txt_width = _txt_width(pb)
    spent = f" elapsed={getTimeAsString(time0)}"
    left = "" if i == 0 else f", remaining~{getTimeAsString(time_left)}"
    text = _pad_text(f"{_percent_text(i, n)}{spent}{left}")
    bar = _THROBBER[pb._counter % 4]
    _write_line(pb, f" {bar}", text)


def _up3(pb: _TimerProgressBarImpl, value: float) -> None:
    if not _valid_value(pb, value):
        return
    time0 = _elapsed(pb)
    pb._value = float(value)
    i = pb._value - pb._min
    n = pb._max - pb._min
    time_left = _remaining_time(pb, time0)
    _maybe_show(pb, time0, time_left)
    if not pb._showpb:
        return
    txt_width = _txt_width(pb)
    text = _style34_text(i, n, time0, time_left)
    if txt_width <= 0:
        _write_line(pb, " ", text)
    else:
        _write_line(pb, _pipe_bar(pb, i, n, txt_width), text)


def _up4(pb: _TimerProgressBarImpl, value: float) -> None:
    if not _valid_value(pb, value):
        return
    time0 = _elapsed(pb)
    pb._value = float(value)
    i = pb._value - pb._min
    n = pb._max - pb._min
    time_left = _remaining_time(pb, time0)
    if i != 0:
        pb._counter += 1
    _maybe_show(pb, time0, time_left)
    if not pb._showpb:
        return
    text = _style34_text(i, n, time0, time_left)
    bar = _THROBBER[pb._counter % 4]
    _write_line(pb, f" {bar}", text)


def _up5(pb: _TimerProgressBarImpl, value: float) -> None:
    if not _valid_value(pb, value):
        return
    time0 = _elapsed(pb)
    pb._value = float(value)
    i = pb._value - pb._min
    n = pb._max - pb._min
    time_left = _remaining_time(pb, time0)
    _maybe_show(pb, time0, time_left)
    if not pb._showpb:
        return
    txt_width = _txt_width(pb)
    spent = f" elapsed={getTimeAsString(time0)}"
    left = "" if i == 0 else f", remaining~{getTimeAsString(time_left)}"
    text = _pad_text(f"{_percent_text(i, n)}{spent}{left}")
    if txt_width <= 0:
        _write_line(pb, " ", text)
    else:
        _write_line(pb, _bracket_bar(pb, i, n, txt_width), text)


def _up6(pb: _TimerProgressBarImpl, value: float) -> None:
    if not _valid_value(pb, value):
        return
    time0 = _elapsed(pb)
    pb._value = float(value)
    i = pb._value - pb._min
    n = pb._max - pb._min
    time_left = _remaining_time(pb, time0)
    _maybe_show(pb, time0, time_left)
    if not pb._showpb:
        return
    txt_width = _txt_width(pb)
    text = _style34_text(i, n, time0, time_left)
    if txt_width <= 0:
        _write_line(pb, " ", text)
    else:
        _write_line(pb, _bracket_bar(pb, i, n, txt_width), text)


_UPDATERS = {
    1: _up1,
    2: _up2,
    3: _up3,
    4: _up4,
    5: _up5,
    6: _up6,
}

__all__ = ["timerProgressBar"]
