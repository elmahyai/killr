"""Text and Windows progress-bar handlers.

``txtProgressBar`` keeps its connection and counters in a closure. Erase and
``clear = TRUE`` write those cells. On unix, ``handler_winprogressbar`` stops
with the OS type before it validates ``inputs``.
"""

from __future__ import annotations

import inspect
import os
import re
import sys
import tempfile

from progressr.condition import condition_message, inherits
from progressr.condition import message as signal_message
from progressr.factory import make_progression_handler
from progressr.options import ProgressrError, file_test_f, get_option, squote, stop_if_not
from utils.progress import (
    close,
    setTxtProgressBar,
    setWinProgressBar,
    txtProgressBar,
    winProgressBar,
)


_ANSI = re.compile(
    r"(?:(?:\x1b\[)|\x9b)(?:(?:[0-9]{1,3})?(?:(?:;[0-9]{0,3})*)?[A-M|f-m])|\x1b[A-M]"
)

_HANDLER_FORMALS = {
    "name",
    "reporter",
    "handler",
    "enable",
    "enable_after",
    "times",
    "interval",
    "intrusiveness",
    "clear",
    "target",
}

_INPUT_SOURCES = ("message", "non_sticky_message", "sticky_message")
_MISSING = object()

_FAKE: dict[str, bool] = {}


def drop_ansi(text: str) -> str:
    """Remove ANSI SGR and cursor sequences. The bar width uses what remains."""
    return _ANSI.sub("", text)


def _os_type() -> str:
    """R ``.Platform$OS.type``: ``windows`` or ``unix``."""
    return "windows" if os.name == "nt" else "unix"


def is_fake(name: str) -> bool:
    """True when ``progressr.tests.fake_handlers`` names this handler.

    The first lookup is kept, matching the R cache.
    """
    if name not in _FAKE:
        option = get_option("progressr.tests.fake_handlers", None)
        if option is None:
            _FAKE[name] = False
        elif isinstance(option, str):
            _FAKE[name] = option == name
        else:
            _FAKE[name] = name in list(option)
    return _FAKE[name]


def handler_backend_args(*unnamed, **kwargs):
    """Named arguments for the backend, minus ``make_progression_handler`` formals."""
    if unnamed or any(name == "" for name in kwargs):
        raise ProgressrError("Additional arguments must be named")
    if not kwargs:
        return {}
    return {key: value for key, value in kwargs.items() if key not in _HANDLER_FORMALS}


def _message_length(message) -> int:
    """R ``length`` of a progression message. An empty string has length 1."""
    if message is None:
        return 0
    if isinstance(message, (list, tuple)):
        return len(message)
    return 1


def message_to_backend_targets(progression, inputs, message=_MISSING):
    """Map a progression message onto title or label, when that source is selected."""
    if message is _MISSING:
        message = progression.get("message") if isinstance(progression, dict) else None
    if _message_length(message) == 0:
        return {}
    sticky = inherits(progression, "sticky")
    args = {}
    for target, sources in inputs.items():
        if sticky:
            if "sticky_message" in sources:
                args[target] = message
        elif "non_sticky_message" in sources:
            args[target] = message
    return args


def _free_cells(fn):
    closure = getattr(fn, "__closure__", None)
    if not closure:
        return {}
    return dict(zip(fn.__code__.co_freevars, closure))


def _style_code(pb) -> int:
    return {"up1": 1, "up2": 2, "up3": 3}.get(pb.up.__name__, 1)


def _stream_cells(pb):
    found = []
    for fn in (getattr(pb, "up", None), getattr(pb, "kill", None)):
        if fn is None:
            continue
        cell = _free_cells(fn).get("stream")
        if cell is not None and all(cell is not item for item in found):
            found.append(cell)
    return found


def _flush_console() -> None:
    """R ``flush.console``."""
    sys.stdout.flush()
    sys.stderr.flush()


def eraseTxtProgressBar(pb) -> None:
    """Overwrite the current text bar with spaces and reset its counters."""
    if inherits(pb, "voidProgressBar"):
        return
    cells = _free_cells(pb.up)
    state = cells["state"].cell_contents
    style = _style_code(pb)
    if style in (1, 2):
        count = state["nb"]
    elif style == 3:
        count = 3 + cells["nw"].cell_contents * cells["bar_width"].cell_contents + 6
    else:
        raise ProgressrError("txtProgressBar style is not 1, 2, or 3")
    stream = cells["stream"].cell_contents
    stream.write("\r" + (" " * int(count)) + "\r")
    flush = getattr(stream, "flush", None)
    if flush is not None:
        flush()
    _flush_console()
    state["nb"] = 0
    state["pc"] = -1


def redrawTxtProgressBar(pb) -> None:
    """Draw the text bar again at its current value."""
    if inherits(pb, "voidProgressBar"):
        return
    setTxtProgressBar(pb, value=pb.getVal())


def txtProgressBar2(min=0, max=1, *, char, **rest):
    """``txtProgressBar`` that allows ``max == min`` and an ANSI ``char``."""
    if max == min:
        pb = txtProgressBar()
        pb.classes = ("voidProgressBar", "txtProgressBar")
        return pb
    clean = drop_ansi(char)
    pb = txtProgressBar(min=min, max=max, char=clean, **rest)
    if clean != char:
        cells = _free_cells(pb.up)
        # The slot count was computed from the stripped symbol. ``nw`` is then
        # ``nchar(clean)``, the character count, and the drawn symbol keeps the ANSI.
        cells["char"].cell_contents = char
        cells["nw"].cell_contents = len(clean)
    return pb


def _close_onto_tempfile(pb) -> None:
    """Erase, send ``close``'s newline to a temp path, then delete that file."""
    eraseTxtProgressBar(pb)
    cells = _stream_cells(pb)
    original = cells[0].cell_contents if cells else None
    directory = tempfile.mkdtemp()
    path = os.path.join(directory, "pb")
    handle = open(path, "w", encoding="utf-8", newline="\n")
    for cell in cells:
        cell.cell_contents = handle
    try:
        close(pb)
    finally:
        handle.flush()
        handle.close()
        if file_test_f(path):
            os.remove(path)
        for cell in cells:
            cell.cell_contents = original
        try:
            os.rmdir(directory)
        except OSError:
            pass


def _write(file, text) -> None:
    if file == "":
        sys.stdout.write(text)
        sys.stdout.flush()
        return
    file.write(text)
    flush = getattr(file, "flush", None)
    if flush is not None:
        flush()


def handler_txtprogressbar(
    char="=",
    style=3,
    file=None,
    intrusiveness=None,
    target="terminal",
    *unnamed,
    **extra,
):
    """Report progress with ``utils.txtProgressBar``. The default style is 3."""
    if file is None:
        file = sys.stderr
    if intrusiveness is None:
        intrusiveness = get_option("progressr.intrusiveness.terminal", 1)
    backend_args = handler_backend_args(*unnamed, char=char, style=style, **extra)
    pb_box = [None]

    def make_pb(maximum, **kwargs):
        if pb_box[0] is not None:
            return pb_box[0]
        args = {"max": maximum}
        args.update(kwargs)
        for key, value in backend_args.items():
            if key in args:
                raise ProgressrError(
                    f'formal argument "{key}" matched by multiple actual arguments'
                )
            args[key] = value
        pb_box[0] = txtProgressBar2(**args)
        return pb_box[0]

    def reset(*args, **kwargs):
        pb_box[0] = None

    def hide(*args, **kwargs):
        if pb_box[0] is None:
            return None
        eraseTxtProgressBar(pb_box[0])
        return None

    def unhide(*args, **kwargs):
        if pb_box[0] is None:
            return None
        redrawTxtProgressBar(pb_box[0])
        return None

    def interrupt(config, state, progression, **kwargs):
        del config, state
        if pb_box[0] is None:
            return None
        eraseTxtProgressBar(pb_box[0])
        redrawTxtProgressBar(pb_box[0])
        msg = condition_message(progression)
        _write(file, "\n".join(("", msg, "")))
        return None

    def initiate(config, state, progression, **kwargs):
        del progression, kwargs
        if not state["enabled"] or config["times"] == 1:
            return None
        stop_if_not(pb_box[0] is None)
        make_pb(config["max_steps"], file=file)
        return None

    def update(config, state, progression, **kwargs):
        del kwargs
        if not state["enabled"] or config["times"] == 1:
            return None
        make_pb(config["max_steps"], file=file)
        if inherits(progression, "sticky"):
            eraseTxtProgressBar(pb_box[0])
            signal_message(f"{state['message']}")
            redrawTxtProgressBar(pb_box[0])
        if progression.get("amount") == 0:
            return None
        setTxtProgressBar(pb_box[0], value=state["step"])
        return None

    def finish(config, state, progression, **kwargs):
        del progression, kwargs
        if pb_box[0] is None:
            return None
        if not state["enabled"]:
            return None
        if config["clear"]:
            _close_onto_tempfile(pb_box[0])
        else:
            setTxtProgressBar(pb_box[0], value=config["max_steps"])
            close(pb_box[0])
        pb_box[0] = None
        return None

    reporter = {
        "reset": reset,
        "hide": hide,
        "unhide": unhide,
        "interrupt": interrupt,
        "initiate": initiate,
        "update": update,
        "finish": finish,
    }
    return make_progression_handler(
        "txtprogressbar",
        reporter,
        intrusiveness=intrusiveness,
        target=target,
        **extra,
    )


def _input_source_ok(value) -> bool:
    if value is None:
        return True
    if not isinstance(value, str):
        return False
    return value in _INPUT_SOURCES


def _validate_inputs(inputs) -> None:
    names = tuple(inputs) if isinstance(inputs, dict) else None
    stop_if_not(isinstance(inputs, dict))
    stop_if_not(names is not None)
    stop_if_not(all(name in ("title", "label") for name in names))
    stop_if_not(all(_input_source_ok(value) for value in inputs.values()))


def _expand_inputs(inputs):
    """``message`` becomes ``non_sticky_message`` and ``sticky_message``."""
    expanded = {}
    for name, value in inputs.items():
        if value is None:
            expanded[name] = []
            continue
        items = [value] if isinstance(value, str) else list(value)
        if "message" in items:
            items = [item for item in items if item != "message"]
            items.extend(("non_sticky_message", "sticky_message"))
        unique = []
        for item in items:
            if item not in unique:
                unique.append(item)
        expanded[name] = unique
    return expanded


def _first(pairs, name):
    for key, value in pairs:
        if key == name:
            return value
    return None


def _set_first(pairs, name, value) -> None:
    for index, (key, _value) in enumerate(pairs):
        if key == name:
            pairs[index] = (name, value)
            return
    pairs.append((name, value))


def _formal_names(fn):
    return tuple(inspect.signature(fn).parameters)


def handler_winprogressbar(
    intrusiveness=None,
    target="gui",
    inputs=None,
    *unnamed,
    **extra,
):
    """Report progress with ``utils.winProgressBar``. Requires MS Windows."""
    if intrusiveness is None:
        intrusiveness = get_option("progressr.intrusiveness.gui", 1)
    if inputs is None:
        inputs = {"title": None, "label": "message"}
    backend_args = handler_backend_args(*unnamed, **extra)

    if not is_fake("handler_winprogressbar"):
        os_type = _os_type()
        if os_type != "windows":
            raise ProgressrError(
                f"handler_winprogressbar requires MS Windows: {squote(os_type)}"
            )
        create_bar = winProgressBar
        set_bar = setWinProgressBar
    else:
        def create_bar(
            title="R progress bar",
            label="",
            min=0,
            max=1,
            initial=0,
            width=300,
        ):
            return {"title": title, "label": label, "min": min, "max": max, "initial": initial, "width": width}

        def set_bar(pb, value, title=None, label=None):
            del pb, value, title, label
            return None

    _validate_inputs(inputs)
    inputs = _expand_inputs(dict(inputs))
    create_formals = _formal_names(winProgressBar)
    set_formals = _formal_names(setWinProgressBar)
    create_signature = inspect.signature(winProgressBar)
    pb_config = [None]

    def update_pb(state, progression, message=_MISSING):
        mapped = message_to_backend_targets(progression, inputs, message)
        for name, value in mapped.items():
            pb_config[0][name] = value
        args = dict(pb_config[0])
        args["value"] = state["step"]
        set_bar(**{key: value for key, value in args.items() if key in set_formals})

    def reset(*args, **kwargs):
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
                _set_first(pairs, name, create_signature.parameters[name].default)
        if _first(pairs, "label") == "":
            _set_first(pairs, "label", " ")
        filtered = [(key, value) for key, value in pairs if key in create_formals]
        seen = {}
        for key, value in filtered:
            if key in seen:
                raise ProgressrError(
                    f'formal argument "{key}" matched by multiple actual arguments'
                )
            seen[key] = value
        pb = create_bar(**seen)
        seen["pb"] = pb
        pb_config[0] = {key: value for key, value in seen.items() if key in set_formals}
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
        else:
            update_pb(state, progression)
        return None

    reporter = {
        "reset": reset,
        "initiate": initiate,
        "interrupt": interrupt,
        "update": update,
        "finish": finish,
    }
    return make_progression_handler(
        "winprogressbar",
        reporter,
        intrusiveness=intrusiveness,
        target=target,
        **extra,
    )
