"""The part of progress::progress_bar that handler_progress draws.

The complete cells are paste(rep("", n), collapse = char): n - 1 copies of
the character. The current cell fills the last place. Tokens that depend on
the clock are filled with the same terse units the R bar uses for a short run.
"""

from __future__ import annotations

import math
import sys
import time

from progressr.condition import Condition, condition_message, signal_condition, with_restarts


def _paste_cells(count: int, char: str) -> str:
    """R ``paste(rep("", count), collapse = char)``."""
    if count <= 1:
        return ""
    return char * (count - 1)


def _percent_token(percent: float) -> str:
    """R ``format(round(percent), width = 3)`` plus a percent sign."""
    return f"{int(round(percent)):3d}%"


def _vague_terse(seconds: float) -> str:
    """prettyunits::vague_dt(seconds, format = "terse") for a finite span."""
    if math.isnan(seconds) or math.isinf(seconds):
        return " ?s"
    seconds = float(seconds)
    if seconds < 0:
        seconds = 0.0
    if seconds < 1:
        return "<1s" if seconds > 0 else "0s"
    if seconds < 60:
        return f"{int(round(seconds))}s"
    if seconds < 3600:
        return f"{int(round(seconds / 60))}m"
    if seconds < 86400:
        return f"{int(round(seconds / 3600))}h"
    return f"{int(round(seconds / 86400))}d"


class ProgressBar:
    """A text bar with the tokens handler_progress passes to progress_bar$new."""

    def __init__(
        self,
        format="[:bar] :percent",
        total=100,
        width=None,
        stream=None,
        complete="=",
        incomplete="-",
        current=">",
        callback=None,
        clear=True,
        show_after=0.2,
        force=False,
        message_class=None,
    ):
        del stream
        if width is None:
            width = 78
        self.finished = False
        self._first = True
        self._supported = bool(force)
        self._format = format
        self._total = float(total)
        self._current = 0.0
        self._width = int(width)
        self._chars = {"complete": complete, "incomplete": incomplete, "current": current}
        self._callback = callback if callback is not None else (lambda _self: None)
        self._clear = bool(clear)
        self._show_after = float(show_after)
        self._last_draw = ""
        self._start = None
        self._toupdate = False
        self._complete = False
        self._spin_index = 0
        self._spin_symbols = ("-", "\\", "|", "/")
        names = (
            "current",
            "total",
            "elapsedfull",
            "elapsed",
            "eta",
            "percent",
            "rate",
            "bytes",
            "bar",
            "spin",
            "tick_rate",
        )
        self._has = {name: f":{name}" in format for name in names}

    def _spin(self) -> str:
        symbol = self._spin_symbols[self._spin_index]
        self._spin_index = 0 if self._spin_index >= 3 else self._spin_index + 1
        return symbol

    def _ratio(self) -> float:
        if math.isnan(self._total) or self._total == 0:
            ratio = 0.0
        else:
            ratio = self._current / self._total
        return min(max(ratio, 0.0), 1.0)

    def _emit(self, text: str) -> None:
        condition = Condition({"message": text}, ("message", "condition"))

        def go():
            signal_condition(condition)
            sys.stderr.write(condition_message(condition))

        with_restarts(go, muffleMessage=lambda _condition: None)
        sys.stderr.flush()

    def _clear_line(self) -> None:
        self._emit("\r" + (" " * self._width))

    def _cursor(self) -> None:
        self._emit("\r")

    def tick(self, length=1, tokens=None):
        if self.finished:
            raise RuntimeError("progress bar is finished")
        if tokens is None:
            tokens = {}
        if self._first:
            self._first = False
            self._start = time.perf_counter()
        self._current += float(length)
        if not self._toupdate and self._start is not None:
            if time.perf_counter() - self._start >= self._show_after:
                self._toupdate = True
        if not math.isnan(self._total) and self._current >= self._total:
            self._complete = True
        if self._toupdate:
            self.render(tokens)
        if self._complete:
            self.terminate()
            self._callback(self)
        return self

    def update(self, ratio, tokens=None):
        if self.finished:
            raise RuntimeError("progress bar is finished")
        goal = math.floor(float(ratio) * self._total)
        return self.tick(goal - self._current, tokens)

    def message(self, msg, set_width=True):
        del set_width
        if self.finished:
            raise RuntimeError("progress bar is finished")
        text = str(msg)
        if self._supported:
            self._clear_line()
            self._cursor()
        self._emit(text + "\n")
        if self._supported and not self.finished:
            self._emit(self._last_draw)

    def terminate(self):
        self.finished = True
        if not self._supported or not self._toupdate:
            return None
        if self._clear:
            self._clear_line()
            self._cursor()
        else:
            self._emit("\n")
        return None

    def render(self, tokens=None):
        if not self._supported:
            return self
        if tokens is None:
            tokens = {}
        text = self._format
        if self._has["percent"]:
            text = text.replace(":percent", _percent_token(self._ratio() * 100), 1)
        if self._has["elapsed"]:
            elapsed = 0.0 if self._start is None else time.perf_counter() - self._start
            text = text.replace(":elapsed", _vague_terse(elapsed), 1)
        if self._has["eta"]:
            if math.isnan(self._total):
                eta = "?"
            else:
                percent = self._ratio() * 100
                elapsed = 0.0 if self._start is None else time.perf_counter() - self._start
                if percent == 100 or self._current == 0:
                    eta_secs = 0.0 if percent == 100 else math.nan
                else:
                    eta_secs = elapsed * (self._total / self._current - 1.0)
                if math.isnan(eta_secs) or math.isinf(eta_secs):
                    eta = " ?s"
                else:
                    eta = _vague_terse(eta_secs)
            text = text.replace(":eta", eta, 1)
        if self._has["current"]:
            text = text.replace(":current", str(int(round(self._current))), 1)
        if self._has["total"]:
            text = text.replace(":total", str(int(round(self._total))), 1)
        if self._has["spin"]:
            text = text.replace(":spin", self._spin(), 1)
        for name, value in tokens.items():
            try:
                replacement = "" if value is None else str(value)
            except Exception:
                replacement = "???"
            text = text.replace(f":{name}", replacement)
        if self._has["bar"]:
            aside = text.replace(":bar", "", 1)
            bar_width = max(0, self._width - len(aside))
            complete_len = int(round(bar_width * self._ratio()))
            complete = _paste_cells(complete_len, self._chars["complete"])
            if self._complete:
                current = self._chars["complete"]
            elif complete_len >= 1:
                current = self._chars["current"]
            else:
                current = ""
            incomplete = _paste_cells(bar_width - complete_len + 1, self._chars["incomplete"])
            text = text.replace(":bar", complete + current + incomplete, 1)
        if len(text) > self._width:
            text = text[: self._width - 3] + "..."
        if self._last_draw != text:
            if len(self._last_draw) > len(text):
                self._clear_line()
            self._cursor()
            self._emit(text)
            self._last_draw = text
        return self
