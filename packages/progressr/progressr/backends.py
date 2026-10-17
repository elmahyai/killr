"""Handlers whose backends are a text bar and a Tcl/Tk window.

``handler_progress`` draws with the same tokens as ``progress::progress_bar``.
``handler_tkprogressbar`` opens a ``tkinter`` ttk bar, the standard-library
binding for Tcl/Tk.
"""

from __future__ import annotations

import math

from progressr.bars import (
    _MISSING,
    _expand_inputs,
    _first,
    _set_first,
    handler_backend_args,
    is_fake,
    message_to_backend_targets,
)
from progressr.condition import condition_message
from progressr.factory import make_progression_handler
from progressr.options import ProgressrError, dquote, get_option, match_arg, squote, stop_if_not
from progressr.progress_bar import ProgressBar


_TYPES = ("default", "steps", "percent", "time")
_FORMATS = {
    "default": ":spin [:bar] :percent :message",
    "steps": ":spin [:bar] :current/:total :message",
    "percent": ":spin [:bar] :percent :message",
    "time": "[:elapsed] :spin [:bar] :percent [:current/:total] (ETA: :eta) :message",
}
_TK_CREATE = ("title", "label", "min", "max", "initial", "width")
_TK_SET = ("pb", "value", "title", "label")
_TK_DEFAULTS = {"title": "R progress bar", "label": ""}


def _tcltk_available() -> bool:
    try:
        import tkinter as tk
    except Exception:
        return False
    try:
        root = tk.Tk()
    except Exception:
        return False
    root.withdraw()
    root.destroy()
    return True


class TkProgressBar:
    """The fields ``tcltk::tkProgressBar`` stores on the window."""

    def __init__(
        self,
        title="R progress bar",
        label="",
        min=0,
        max=1,
        initial=0,
        width=300,
    ):
        import tkinter as tk
        from tkinter import ttk

        self.min = float(min)
        self.max = float(max)
        self.value = None
        self.killed = False
        self.width = int(width)
        self._root = tk.Tk()
        self._root.withdraw()
        self.win = tk.Toplevel(self._root)
        self.win.geometry(f"{self.width + 40}x80")
        self.win.title("" if title is None else str(title))
        self.lab = tk.Label(self.win, text="" if label is None else str(label), font=("helvetica", 12), pady=10)
        self.lab.pack(side="top")
        tk.Label(self.win, text="", font=("helvetica", 12)).pack(side="bottom")
        self.var = tk.DoubleVar(master=self.win, value=0)
        bar = ttk.Progressbar(self.win, length=self.width, variable=self.var, maximum=100)
        bar.pack(side="bottom")
        self.up(initial)
        self.win.update_idletasks()

    def up(self, value) -> None:
        try:
            number = float(value)
        except (TypeError, ValueError):
            return
        if not math.isfinite(number) or number < self.min or number > self.max:
            return
        self.value = number
        span = self.max - self.min
        self.var.set(0 if span == 0 else 100 * (number - self.min) / span)

    def set_title(self, title) -> None:
        self.win.title("" if title is None else str(title))

    def set_label(self, label) -> None:
        self.lab.configure(text="" if label is None else str(label))

    def kill(self) -> None:
        if self.killed:
            return
        self.killed = True
        self.win.destroy()
        self._root.destroy()

    def snapshot(self) -> dict:
        if self.killed:
            return {"gone": True}
        self.win.update_idletasks()
        geometry = self.win.geometry().split("+", 1)[0]
        return {
            "gone": False,
            "title": self.win.title(),
            "label": self.lab.cget("text"),
            "percent": float(self.var.get()),
            "geometry": geometry,
        }


def setTkProgressBar(pb, value, title=None, label=None):
    """``tcltk::setTkProgressBar``. Returns the previous value."""
    old = pb.value
    pb.up(value)
    if title is not None:
        pb.set_title(title)
    if label is not None:
        pb.set_label(label)
    if not pb.killed:
        pb.win.update_idletasks()
    return old


def close(con) -> None:
    """``close.tkProgressBar`` calls ``kill``."""
    kill = getattr(con, "kill", None)
    if kill is not None:
        kill()


def handler_progress(
    format=None,
    show_after=0.0,
    intrusiveness=None,
    target="terminal",
    type=_TYPES,
    *unnamed,
    **extra,
):
    """Report progress with a ``progress::progress_bar`` line.

    The ``show_after`` formal is not read. The bar waits for ``enable_after``.
    """
    del show_after
    if intrusiveness is None:
        intrusiveness = get_option("progressr.intrusiveness.terminal", 1)
    try:
        chosen = match_arg(type, _TYPES)
    except ProgressrError as exc:
        if "should be one of" not in str(exc):
            raise
        listed = ", ".join(dquote(choice) for choice in _TYPES)
        raise ProgressrError(f"'arg' should be one of {listed}") from None
    if isinstance(format, (list, tuple)):
        if len(format) != 1:
            raise ProgressrError(f"{squote('length(format) == 1L')} is not TRUE")
        format = format[0]
    if format is None:
        format = _FORMATS[chosen]
    if not isinstance(format, str):
        raise ProgressrError(f"{squote('is.character(format)')} is not TRUE")
    backend_args = handler_backend_args(*unnamed, **extra)
    bar_format = format
    create = ProgressBar

    def make_pb(config, show):
        args = {
            "format": bar_format,
            "total": config["max_steps"],
            "clear": config["clear"],
            "show_after": show,
            "force": True,
        }
        for key, value in backend_args.items():
            if key not in args:
                args[key] = value
        return create(**args)

    state_pb = {"pb": None, "tokens": {}}

    def tick(pb, delta, message):
        if pb.finished:
            return
        if pb._total == 0:
            return
        tokens = {"message": "" if message is None else f"{message}"}
        state_pb["tokens"] = tokens
        if delta < 0:
            return
        pb.tick(delta, tokens)

    def reset(**_unused):
        state_pb["pb"] = None

    def hide(**_unused):
        pb = state_pb["pb"]
        if pb is None or pb.finished:
            return
        pb._clear_line()
        pb._cursor()

    def unhide(**_unused):
        pb = state_pb["pb"]
        if pb is None or pb.finished:
            return
        pb._last_draw = ""
        pb.render(state_pb["tokens"])

    def interrupt(config, state, progression, **_unused):
        del config
        pb = state_pb["pb"]
        if pb is None:
            return
        pb._clear_line()
        pb._cursor()
        pb._last_draw = ""
        pb.render(state_pb["tokens"])
        text = condition_message(progression)
        import sys

        sys.stderr.write(f"\n{text}\n")

    def initiate(config, state, progression, **_unused):
        del progression
        if not state["enabled"] or config["times"] == 1:
            return
        stop_if_not(state_pb["pb"] is None)
        pb = make_pb(config, config["enable_after"])
        state_pb["pb"] = pb
        tick(pb, 0, state["message"])

    def update(config, state, progression, **_unused):
        if not state["enabled"] or config["times"] <= 2:
            return
        pb = state_pb["pb"]
        if pb is None:
            pb = make_pb(config, config["enable_after"])
            state_pb["pb"] = pb
        if inherits_sticky(progression):
            if _message_length(state["message"]) > 0 and not pb.finished:
                pb.message(state["message"])
        tick(pb, state["delta"], state["message"])

    def finish(config, state, progression, **_unused):
        pb = state_pb["pb"]
        if pb is None:
            return
        if not pb.finished:
            update(config, state, progression)
            if config["clear"] and not pb.finished:
                pb.update(1.0)
        state_pb["pb"] = None

    reporter = {
        "reset": reset,
        "hide": hide,
        "unhide": unhide,
        "interrupt": interrupt,
        "initiate": initiate,
        "update": update,
        "finish": finish,
    }
    handler = make_progression_handler(
        "progress",
        reporter,
        intrusiveness=intrusiveness,
        target=target,
        **extra,
    )
    handler.bar_format = bar_format
    return handler


def _message_length(message) -> int:
    if message is None:
        return 0
    if isinstance(message, (list, tuple)):
        return len(message)
    return 1


def inherits_sticky(progression) -> bool:
    from progressr.condition import inherits

    return inherits(progression, "sticky")


def _validate_tk_inputs(inputs) -> None:
    """The same predicates R checks, with R's deparsed stop_if_not text."""
    if not isinstance(inputs, dict):
        raise ProgressrError(f"{squote('is.list(inputs)')} is not TRUE")
    names = list(inputs)
    if any(not isinstance(name, str) or name == "" for name in names):
        raise ProgressrError(f"{squote('!is.null(names(inputs))')} is not TRUE")
    if any(name not in ("title", "label") for name in names):
        raise ProgressrError(
            f"{squote('all(names(inputs) %in% c(\"title\", \"label\"))')} is not TRUE"
        )
    if not all(_tk_source_ok(value) for value in inputs.values()):
        raise ProgressrError(
            f"{squote('all(vapply(inputs, FUN = function(x) { ...')} is not TRUE"
        )


def _tk_source_ok(value) -> bool:
    if value is None:
        return True
    if not isinstance(value, str):
        return False
    return value in ("message", "non_sticky_message", "sticky_message")


def handler_tkprogressbar(
    intrusiveness=None,
    target="terminal",
    inputs=None,
    *unnamed,
    **extra,
):
    """Report progress with a Tcl/Tk progress window."""
    if intrusiveness is None:
        intrusiveness = get_option("progressr.intrusiveness.gui", 1)
    if inputs is None:
        inputs = {"title": None, "label": "message"}
    backend_args = handler_backend_args(*unnamed, **extra)
    if not is_fake("handler_tkprogressbar"):
        if not _tcltk_available():
            raise ProgressrError("handler_tkprogressbar requires TclTk support")
        create_bar = TkProgressBar
        set_bar = setTkProgressBar
    else:
        def create_bar(title="R progress bar", label="", min=0, max=1, initial=0, width=300):
            return {"title": title, "label": label, "min": min, "max": max, "value": initial, "width": width, "killed": False}

        def set_bar(pb, value, title=None, label=None):
            pb["value"] = value
            if title is not None:
                pb["title"] = title
            if label is not None:
                pb["label"] = label
            return None

    _validate_tk_inputs(inputs)
    expanded = _expand_inputs(dict(inputs))
    pb_config = [None]
    # R captures the finish arguments before the second shutdown update.
    reported_steps = []

    def update_pb(state, progression, message=_MISSING):
        mapped = message_to_backend_targets(progression, expanded, message)
        for name, value in mapped.items():
            pb_config[0][name] = value
        args = dict(pb_config[0])
        args["value"] = state["step"]
        set_bar(**{key: value for key, value in args.items() if key in _TK_SET})

    def reset(**_unused):
        pb_config[0] = None

    def initiate(config, state, progression, **kwargs):
        del progression
        if not state["enabled"] or config["times"] == 1:
            return None
        if config["clear"]:
            stop_if_not(pb_config[0] is None)
        pairs = list(backend_args.items())
        pairs.append(("max", config["max_steps"]))
        pairs.append(("initial", state["step"]))
        pairs.extend(kwargs.items())
        for name in ("title", "label"):
            if _first(pairs, name) is None:
                _set_first(pairs, name, _TK_DEFAULTS[name])
        seen = {}
        for key, value in pairs:
            if key not in _TK_CREATE:
                continue
            if key in seen:
                raise ProgressrError(f'formal argument "{key}" matched by multiple actual arguments')
            seen[key] = value
        pb = create_bar(**seen)
        seen["pb"] = pb
        pb_config[0] = {key: value for key, value in seen.items() if key in _TK_SET}
        return pb_config[0]

    def interrupt(config, state, progression, **kwargs):
        del config, kwargs
        if not state["enabled"]:
            return None
        update_pb(state, progression, message=condition_message(progression))
        return None

    def update(config, state, progression, **kwargs):
        del kwargs
        if not state["enabled"] or config["times"] <= 2:
            return None
        reported_steps.append(state["step"])
        update_pb(state, progression)
        return None

    def finish(config, state, progression, **kwargs):
        del kwargs
        if pb_config[0] is None:
            return None
        if not state["enabled"]:
            return None
        if config["clear"]:
            close(pb_config[0]["pb"])
            pb_config[0] = None
            return None
        shown = dict(state)
        if progression.get("type") == "shutdown" and len(reported_steps) >= 2:
            shown["step"] = reported_steps[-2]
        update_pb(shown, progression)
        return None

    reporter = {
        "reset": reset,
        "initiate": initiate,
        "interrupt": interrupt,
        "update": update,
        "finish": finish,
    }
    return make_progression_handler(
        "tkprogressbar",
        reporter,
        intrusiveness=intrusiveness,
        target=target,
        **extra,
    )

