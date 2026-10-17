"""Create a progress bar the way pbapply's startpb does."""

from __future__ import annotations

import sys
from typing import Any, Callable, Mapping, MutableMapping, Optional

from pbapply.pbtypes import pbtypes as _pbtypes

_BAD_RANGE = "must have 'max' > 'min'"
_DEFAULT_PBOPTIONS: dict[str, Any] = {
    "type": "none",
    "char": "+",
    "txt.width": 50,
    "gui.width": 300,
    "style": 3,
    "initial": 0,
    "title": "R progress bar",
    "label": "",
    "nout": 100,
    "min_time": 0,
    "use_lb": False,
}

_pboptions: dict[str, Any] = dict(_DEFAULT_PBOPTIONS)


class _TxtProgressBar:
    """Minimal utils::txtProgressBar stand-in for startpb."""

    __slots__ = ("_min", "_max", "_value", "_closed")

    def __init__(self, *, min: float, max: float, initial: float) -> None:
        self._min = float(min)
        self._max = float(max)
        self._value = float(initial)
        self._closed = False

    def get_val(self) -> float:
        return self._value

    def up(self, value: float) -> None:
        self._value = float(value)

    def kill(self) -> None:
        self._closed = True


class _TimerProgressBar(_TxtProgressBar):
    """timerProgressBar inherits txtProgressBar in R."""


class _ShinyProgress:
    __slots__ = ("_value", "_closed")

    def __init__(self, *, min: float, max: float) -> None:
        self._value = float(min)
        self._closed = False

    def close(self) -> None:
        self._closed = True

    def set(self, value: float, *, inc: Optional[float] = None) -> float:
        prev = self._value
        if inc is not None:
            self._value += float(inc)
        else:
            self._value = float(value)
        return prev


def startpb(min: float = 0, max: float = 1):
    """Start a progress bar when pboptions allow it; otherwise return None."""
    if not _dopb():
        return None

    control = dict(_pboptions)
    bar_type = control.get("type")
    initial = control.get("initial", 0)
    style = control.get("style", 3)
    width = control.get("txt.width", 50)
    char = control.get("char", "+")
    min_time = control.get("min_time", 0)
    title = control.get("title", "R progress bar")
    label = control.get("label", "")

    pb: Any
    if bar_type == "timer":
        pb = _timer_progress_bar(
            min=min,
            max=max,
            initial=initial,
            style=style,
            width=width,
            char=char,
            min_time=min_time,
        )
    elif bar_type == "txt":
        pb = _txt_progress_bar(
            min=min,
            max=max,
            initial=initial,
            style=style,
            width=width,
            char=char,
        )
    elif bar_type == "win":
        pb = _win_progress_bar(
            min=min,
            max=max,
            initial=initial,
            title=title,
            label=label,
            width=control.get("gui.width", 300),
        )
    elif bar_type == "tk":
        pb = _tk_progress_bar(
            min=min,
            max=max,
            initial=initial,
            title=title,
            label=label,
            width=control.get("gui.width", 300),
        )
    else:
        pb = None

    if _doshiny():
        pb = _ShinyProgress(min=min, max=max)
        _setpb(pb, 0)

    return pb


def getpb(pb) -> Optional[float]:
    """Return the current progress value when pboptions allow a progress bar."""
    if not _dopb():
        return None
    bar_type = _pboptions.get("type")
    rval: Optional[float] = None
    if bar_type in ("timer", "txt"):
        if isinstance(pb, (_TxtProgressBar, _TimerProgressBar)):
            rval = pb.get_val()
    elif bar_type == "win" and sys.platform == "win32":
        if isinstance(pb, (_TxtProgressBar, _TimerProgressBar)):
            rval = pb.get_val()
    elif bar_type == "tk":
        if isinstance(pb, (_TxtProgressBar, _TimerProgressBar)):
            rval = pb.get_val()
    if _doshiny() and isinstance(pb, _ShinyProgress):
        rval = pb._value
    return rval


def setpb(pb, value: float) -> Optional[float]:
    """Set the progress value; return the previous value when dopb() is true."""
    if not _dopb():
        return None
    bar_type = _pboptions.get("type")
    rval: Optional[float] = None
    if bar_type in ("timer", "txt"):
        if isinstance(pb, (_TxtProgressBar, _TimerProgressBar)):
            rval = pb.get_val()
            pb.up(value)
    elif bar_type == "win" and sys.platform == "win32":
        if isinstance(pb, (_TxtProgressBar, _TimerProgressBar)):
            rval = pb.get_val()
            pb.up(value)
    elif bar_type == "tk":
        if isinstance(pb, (_TxtProgressBar, _TimerProgressBar)):
            rval = pb.get_val()
            pb.up(value)
    if _doshiny() and isinstance(pb, _ShinyProgress):
        rval = pb.set(value)
    return rval


def closepb(pb) -> None:
    """Close a progress bar created by startpb."""
    if pb is None:
        return
    if _doshiny():
        close = getattr(pb, "close", None)
        if callable(close):
            close()
    elif isinstance(pb, (_TxtProgressBar, _TimerProgressBar)):
        pb.kill()


def replace_pboptions(**tags: Any) -> dict[str, Any]:
    """Replace pboptions entries; proof scripts use this where R calls pboptions."""
    former = dict(_pboptions)
    for key, value in tags.items():
        if value is None and key == "type":
            _pboptions[key] = None
        else:
            _pboptions[key] = value
    return former


def reset_pboptions(options: Optional[Mapping[str, Any]] = None) -> None:
    """Restore defaults or a former options dict from replace_pboptions."""
    _pboptions.clear()
    if options is None:
        _pboptions.update(_DEFAULT_PBOPTIONS)
    else:
        _pboptions.update(options)


def _dopb() -> bool:
    from pbapply.dopb import dopb

    return dopb()


def _doshiny() -> bool:
    bar_type = _pboptions.get("type")
    if bar_type != "shiny":
        return False
    return _shiny_namespace_available() and _shiny_app_running()


def _setpb(pb, value: float) -> None:
    setpb(pb, value)


def _require_range(min: float, max: float) -> None:
    if not (max > min):
        raise ValueError(_BAD_RANGE)


def _txt_progress_bar(
    *,
    min: float,
    max: float,
    initial: float,
    style: int,
    width: Any,
    char: str,
) -> _TxtProgressBar:
    _require_range(min, max)
    return _TxtProgressBar(min=min, max=max, initial=initial)


def _timer_progress_bar(
    *,
    min: float,
    max: float,
    initial: float,
    style: int,
    width: Any,
    char: str,
    min_time: float,
) -> _TimerProgressBar:
    _require_range(min, max)
    return _TimerProgressBar(min=min, max=max, initial=initial)


def _win_progress_bar(
    *,
    min: float,
    max: float,
    initial: float,
    title: str,
    label: str,
    width: int,
) -> _TxtProgressBar:
    _require_range(min, max)
    return _TxtProgressBar(min=min, max=max, initial=initial)


def _tk_progress_bar(
    *,
    min: float,
    max: float,
    initial: float,
    title: str,
    label: str,
    width: int,
) -> _TxtProgressBar:
    _require_range(min, max)
    return _TxtProgressBar(min=min, max=max, initial=initial)


def _shiny_namespace_available() -> bool:
    import importlib.util

    return importlib.util.find_spec("shiny") is not None


def _shiny_app_running() -> bool:
    try:
        import shiny  # type: ignore[import-not-found]
    except ImportError:
        return False
    session = getattr(shiny, "session", None)
    if session is None:
        return False
    get_current = getattr(session, "get_current_session", None)
    if get_current is None:
        return False
    return get_current() is not None
