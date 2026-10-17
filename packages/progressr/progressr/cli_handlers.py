"""Terminal handlers that report through cli progress bars and an ANSI color bar."""

from __future__ import annotations

import math
import sys

from cli import (
    bg_blue,
    bg_cyan,
    cli_progress_bar,
    cli_progress_done,
    cli_progress_update,
    col_white,
    console_width,
    get_option as cli_get_option,
    num_ansi_colors,
    options as cli_options,
)
from progressr.condition import condition_message, inherits
from progressr.factory import make_progression_handler
from progressr.options import ProgressrError, dquote, get_option, squote, stop_if_not


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

_FORMATS = {
    "default": None,
    "steps": "{cli::pb_spin} {cli::pb_bar} {cli::pb_current}/{cli::pb_total} {cli::pb_status}",
    "percent": "{cli::pb_spin} {cli::pb_bar} {cli::pb_percent} {cli::pb_status}",
    "time": "[{cli::pb_elapsed}] {cli::pb_spin} {cli::pb_bar} {cli::pb_percent} [{cli::pb_current}/{cli::pb_total}] (ETA: {cli::pb_eta}) {cli::pb_status}",
}

_FORMATS_DONE = {
    "default": None,
    "steps": "{cli::pb_bar} {cli::pb_current}/{cli::pb_total} {cli::pb_status}",
    "percent": "{cli::pb_bar} {cli::pb_percent} {cli::pb_status}",
    "time": "[{cli::pb_elapsed}] {cli::pb_bar} {cli::pb_percent} [{cli::pb_current}/{cli::pb_total}] {cli::pb_status}",
}

_TYPE_CHOICES = ("default", "steps", "percent", "time")
_SPEC_CHOICES = ("progress", "cli")
_FAKE = {}
_SPINNER = ("-", "\\", "|", "/", "-", "\\", "|", "/")


class _NACharacter(str):
    """R NA_character_: one character element whose value is missing."""

    def __new__(cls):
        return str.__new__(cls, "NA")


_NA = _NACharacter()
_MISSING = object()


class _Env(dict):
    """A one-frame environment, the way handler_cli stores the cli bar total."""


def _match_arg(arg, choices):
    """R 4.5 match.arg. A non-unique prefix uses the same message as a miss."""
    choices = tuple(choices)
    if arg is None:
        return choices[0]
    if isinstance(arg, (list, tuple)):
        if list(arg) == list(choices):
            return choices[0]
        if len(arg) != 1:
            raise ProgressrError(f"{squote('arg')} must be of length 1")
        arg = arg[0]
        if arg is None:
            return choices[0]
    if not isinstance(arg, str):
        raise ProgressrError(f"{squote('arg')} must be of length 1")
    if arg in choices:
        return arg
    matches = [choice for choice in choices if choice.startswith(arg)]
    if len(matches) == 1:
        return matches[0]
    listed = ", ".join(dquote(choice) for choice in choices)
    raise ProgressrError(f"'arg' should be one of {listed}")


def _is_fake(name) -> bool:
    if name not in _FAKE:
        handlers = get_option("progressr.tests.fake_handlers")
        if handlers is None:
            handlers = ()
        _FAKE[name] = name in handlers
    return _FAKE[name]


def _backend_args(pairs: dict) -> dict:
    if not pairs:
        return {}
    return {key: value for key, value in pairs.items() if key not in _HANDLER_FORMALS}


def _r_length(value) -> int:
    if value is None:
        return 0
    if isinstance(value, (str, bytes, _NACharacter)):
        return 1
    if isinstance(value, (list, tuple)):
        return len(value)
    return 1


def _is_character(value) -> bool:
    return isinstance(value, str)


def _is_numeric(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _is_finite_number(value) -> bool:
    return _is_numeric(value) and math.isfinite(float(value))


def _as_numeric(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ProgressrError("is.numeric(fraction) is not TRUE")
    return float(value)


def _as_integer(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        number = float(value)
    else:
        number = float(value)
    if math.isnan(number):
        return None
    return int(number)


def _cat_stderr(*parts) -> None:
    chunks = []
    for part in parts:
        if isinstance(part, (list, tuple)):
            chunks.extend("" if item is None else str(item) for item in part)
        elif part is None:
            chunks.append("")
        else:
            chunks.append(str(part))
    sys.stderr.write("".join(chunks))
    sys.stdout.flush()
    sys.stderr.flush()


def _option_width():
    value = cli_get_option("width", 80)
    if value is None:
        return 80
    return value


def _push_cli(**values):
    return cli_options(**values)


def _pop_cli(previous) -> None:
    if previous:
        cli_options(**previous)


def _namespace_available(name: str) -> bool:
    if name == "cli":
        return True
    if name == "progress":
        # This machine's R has the progress package. Do not invent a Python one.
        return True
    return False


def _default_complete(text):
    return bg_blue(col_white(text))


def _default_incomplete(text):
    return bg_cyan(col_white(text))


def _substr(text, start, stop) -> str:
    start_i = int(start)
    stop_i = int(stop)
    if start_i < 1:
        start_i = 1
    if stop_i < start_i:
        return ""
    return text[start_i - 1 : stop_i]


def _pad_field(width, text) -> str:
    width_i = int(float(width))
    body = "" if text is None else str(text)
    if width_i <= 0:
        return body if width_i < 0 else ""
    return f"{body:>{width_i}}"


def pbcol(
    fraction=0.0,
    msg="",
    adjust=0,
    pad=1,
    width=None,
    complete=_MISSING,
    incomplete=_MISSING,
    spin=" ",
):
    """ANSI background bar used by handler_pbcol. Not an R export."""
    if complete is _MISSING:
        complete = _default_complete
    if incomplete is _MISSING:
        incomplete = _default_incomplete
    if width is None:
        width = _option_width() - 1
    if _r_length(msg) == 0:
        msg = ""
    stop_if_not(_r_length(msg) == 1, _is_character(msg))
    fraction = _as_numeric(fraction)
    stop_if_not(
        _r_length(fraction) == 1,
        fraction == fraction,
        fraction >= 0,
        fraction <= 1,
    )
    width = _as_integer(width)
    stop_if_not(_r_length(width) == 1, width is not None, width is not None and width > 0)
    msgfraction = f" {100.0 * fraction:3.0f}%"
    nmsg = len(msg) + len(msgfraction)
    msgpad = (width - 2 * pad) - nmsg
    if msgpad < 0:
        msg = _substr(msg, pad, len(msg) + msgpad - pad)
        msg = _substr(msg, 1, len(msg) - 3)
        msg = f"{msg}..."
        msgpad = (width - 2 * pad) - len(msg) - len(msgfraction)
        stop_if_not(msgpad >= 0)
    lpad = math.floor(adjust * msgpad) + pad
    rpad = math.floor((1 - adjust) * msgpad)
    stop_if_not(lpad >= 0, rpad >= 0)
    pmsg = (
        _pad_field(lpad, "")
        + msg
        + _pad_field(rpad, "")
        + msgfraction
        + str(spin)
        + _pad_field(pad, "")
    )
    length = int(round(fraction * len(pmsg)))
    left = _substr(pmsg, 1, length)
    right = _substr(pmsg, length + 1, len(pmsg))
    if complete is not None:
        left = complete(left)
    if incomplete is not None:
        right = incomplete(right)
    return f"{'' if left is None else left}{'' if right is None else right}"


def handler_cli(
    show_after=0.0,
    intrusiveness=None,
    target="terminal",
    type=_TYPE_CHOICES,
    *args,
    **kwargs,
):
    """Progress reported by cli::cli_progress_bar. show_after is accepted and unused."""
    if args:
        raise ProgressrError("Additional arguments must be named")
    type = _match_arg(type, _TYPE_CHOICES)
    backend_args = _backend_args(kwargs)
    # A missing or NULL format is the type default. An explicit string is kept.
    if backend_args.get("format") is None:
        chosen = _FORMATS[type]
        if chosen is not None:
            backend_args["format"] = chosen
    if backend_args.get("format_done") is None:
        chosen = _FORMATS_DONE[type]
        if chosen is not None:
            backend_args["format_done"] = chosen
    if intrusiveness is None:
        intrusiveness = get_option("progressr.intrusiveness.terminal", 1)

    # The formal is part of the closure. The reporter reads config enable_after.
    _accepted_show_after = show_after

    if not _is_fake("handler_cli"):
        cli_n_colors = num_ansi_colors()

        def cli_freeze_color_options():
            return _push_cli(
                **{
                    "cli.num_colors": cli_n_colors,
                    "crayon.enabled": cli_n_colors > 1,
                    "crayon.colors": cli_n_colors,
                }
            )

        def cli_progress_call(fun, **call):
            previous = cli_freeze_color_options()
            try:
                # Translated cli_progress_bar returns an id and does not signal
                # cliMessage in a non-dynamic session, so nothing is written here.
                return fun(**call)
            finally:
                _pop_cli(previous)

        def progress_bar(total, **call):
            if total == 0:
                return _NA
            previous = _push_cli(**{"cli.progress_handlers_only": "cli"})
            try:
                return cli_progress_call(cli_progress_bar, total=total, **call)
            finally:
                _pop_cli(previous)

        def progress_update(ident, envir, **call):
            if envir["total"] == 0:
                return ident
            return cli_progress_call(cli_progress_update, id=ident, envir=envir, **call)

        def progress_done(ident, envir, **call):
            if envir["total"] == 0:
                return ident
            return cli_progress_call(cli_progress_done, id=ident, envir=envir, **call)

        def erase_progress_bar(pb):
            if pb is None:
                return
            stop_if_not(_is_character(pb["id"]), isinstance(pb["envir"], _Env))
            previous = _push_cli(**{"cli.width": None})
            try:
                pb_width = console_width() - 1
            finally:
                _pop_cli(previous)
            _cat_stderr("\r", " " * int(pb_width), "\r")

        def redraw_progress_bar(pb):
            if pb is None:
                return
            stop_if_not(_is_character(pb["id"]), isinstance(pb["envir"], _Env))
            progress_update(pb["id"], pb["envir"], inc=0)
    else:
        def progress_bar(total, **call):
            return "id-dummy"

        def progress_update(ident, envir, **call):
            return "id-dummy"

        def progress_done(ident, envir, **call):
            return "id-dummy"

        def erase_progress_bar(pb):
            return None

        def redraw_progress_bar(pb):
            return None

    box = {"pb": None}

    def make_pb(total, clear, shown_after):
        if box["pb"] is not None:
            return box["pb"]
        stop_if_not(_is_numeric(total), _r_length(total) == 1, _is_finite_number(total))
        envir = _Env(total=total)
        call = {"total": total, "envir": envir}
        call.update(backend_args)
        call["clear"] = False
        call["auto_terminate"] = False
        call["auto_close"] = False
        previous = _push_cli(**{"cli.progress_show_after": shown_after})
        try:
            ident = progress_bar(**call)
        finally:
            _pop_cli(previous)
        box["pb"] = {"id": ident, "total": total, "envir": envir, "show_after": shown_after}
        stop_if_not(_is_character(box["pb"]["id"]), isinstance(box["pb"]["envir"], _Env))
        return box["pb"]

    def pb_tick(pb, delta=0, message=None):
        if pb is None:
            return
        stop_if_not(
            _is_character(pb["id"]),
            _r_length(pb["id"]) == 1,
            _is_numeric(delta),
            _r_length(delta) == 1,
            _is_finite_number(delta),
            isinstance(pb["envir"], _Env),
        )
        if delta <= 0:
            return
        previous = _push_cli(**{"cli.progress_show_after": pb["show_after"]})
        try:
            progress_update(pb["id"], pb["envir"], inc=delta, status=message)
        finally:
            _pop_cli(previous)

    def pb_update(pb, ratio, message=None):
        if pb is None:
            return
        stop_if_not(_is_character(pb["id"]), isinstance(pb["envir"], _Env))
        previous = _push_cli(**{"cli.progress_show_after": pb["show_after"]})
        try:
            if ratio >= 1.0:
                progress_done(pb["id"], pb["envir"])
            else:
                set_to = ratio * pb["total"]
                stop_if_not(
                    _r_length(set_to) == 1,
                    _is_numeric(set_to),
                    _is_finite_number(set_to),
                    set_to >= 0,
                    set_to < pb["total"],
                )
                progress_update(pb["id"], pb["envir"], set=set_to, status=message)
        finally:
            _pop_cli(previous)

    def reset(**_unused):
        box["pb"] = None

    def hide(**_unused):
        if box["pb"] is None:
            return
        erase_progress_bar(box["pb"])

    def unhide(**_unused):
        if box["pb"] is None:
            return
        redraw_progress_bar(box["pb"])

    def interrupt(config, state, progression, **_unused):
        pb = box["pb"]
        if pb is None:
            return
        stop_if_not(_is_character(pb["id"]), isinstance(pb["envir"], _Env))
        try:
            erase_progress_bar(pb)
            redraw_progress_bar(pb)
        except Exception:
            pass
        msg = condition_message(progression)
        _cat_stderr("\n", msg, "\n")

    def initiate(config, state, progression, **_unused):
        if not state["enabled"] or config["times"] == 1:
            return
        stop_if_not(box["pb"] is None)
        pb = make_pb(config["max_steps"], config["clear"], config["enable_after"])
        pb_tick(pb, delta=0, message=state["message"])

    def update(config, state, progression, **_unused):
        if not state["enabled"] or config["times"] <= 2:
            return
        if progression["amount"] == 0:
            return
        pb = make_pb(config["max_steps"], config["clear"], config["enable_after"])
        if inherits(progression, "sticky") and _r_length(state["message"]) > 0:
            # The R source leaves the sticky message unset on the cli bar.
            pass
        previous = _push_cli(**{"cli.progress_show_after": pb["show_after"]})
        try:
            progress_update(pb["id"], pb["envir"], set=state["step"], status=state["message"])
        finally:
            _pop_cli(previous)

    def finish(config, state, progression, **_unused):
        pb = box["pb"]
        if pb is None:
            return
        stop_if_not(_is_character(pb["id"]), isinstance(pb["envir"], _Env))
        make_pb(config["max_steps"], config["clear"], config["enable_after"])
        update(config=config, state=state, progression=progression)
        if config["clear"]:
            pb_update(box["pb"], ratio=1.0)
            erase_progress_bar(box["pb"])
        else:
            pb_update(box["pb"], ratio=1.0)
            sys.stderr.write("\n")
            sys.stdout.flush()
            sys.stderr.flush()
        box["pb"] = None

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
        "cli",
        reporter,
        intrusiveness=intrusiveness,
        target=target,
        **kwargs,
    )
    handler.backend_args = backend_args
    handler.show_after = _accepted_show_after
    return handler


def handler_pbcol(
    adjust=0.0,
    pad=1,
    complete=_default_complete,
    incomplete=_default_incomplete,
    intrusiveness=None,
    target="terminal",
    *_args,
    **extra,
):
    """Progress reported as an ANSI background color across the terminal line."""
    if intrusiveness is None:
        intrusiveness = get_option("progressr.intrusiveness.terminal", 1)
    crayon_enabled = cli_get_option("crayon.enabled", None)
    if crayon_enabled is None:
        crayon_enabled = num_ansi_colors() > 1

    def cat_(*parts):
        _cat_stderr(*parts)

    def erase_progress_bar():
        cat_("\r", " " * int(_option_width()), "\r")

    def redraw_progress_bar(ratio, message, spin=" "):
        stop_if_not(ratio >= 0, ratio <= 1)
        if crayon_enabled:
            _push_cli(**{"crayon.enabled": True})
        bar = pbcol(
            fraction=ratio,
            msg=message,
            adjust=adjust,
            pad=pad,
            complete=complete,
            incomplete=incomplete,
            spin=spin,
        )
        cat_("\r", bar)

    spin_state = {"n": 0}

    def _ratio(config, state):
        if config["max_steps"] == 0:
            return 1
        return state["step"] / config["max_steps"]

    def _spin():
        return _SPINNER[spin_state["n"]]

    def initiate(config, state, **_unused):
        if not state["enabled"] or config["times"] <= 2:
            return
        redraw_progress_bar(_ratio(config, state), state["message"], spin=_spin())

    def reset(**_unused):
        erase_progress_bar()

    def hide(**_unused):
        erase_progress_bar()

    def unhide(config, state, **_unused):
        if not state["enabled"] or config["times"] <= 2:
            return
        redraw_progress_bar(_ratio(config, state), state["message"], spin=_spin())

    def interrupt(config, state, progression, **_unused):
        if not state["enabled"] or config["times"] <= 2:
            return
        erase_progress_bar()
        redraw_progress_bar(_ratio(config, state), state["message"], spin=_spin())
        msg = condition_message(progression)
        cat_("\n", msg, "\n")

    def update(config, state, progression, **_unused):
        if not state["enabled"] or config["times"] <= 2:
            return
        if state["delta"] < 0:
            return
        spin_state["n"] = (spin_state["n"] + 1) % len(_SPINNER)
        redraw_progress_bar(_ratio(config, state), state["message"], spin=_spin())

    def finish(config, state, progression, **_unused):
        if config["clear"]:
            erase_progress_bar()
        else:
            redraw_progress_bar(1, state["message"], spin=" ")
            sys.stderr.write("\n")

    reporter = {
        "initiate": initiate,
        "reset": reset,
        "hide": hide,
        "unhide": unhide,
        "interrupt": interrupt,
        "update": update,
        "finish": finish,
    }
    return make_progression_handler(
        "pbcol",
        reporter,
        intrusiveness=intrusiveness,
        target=target,
        **extra,
    )


def _handler_progress(*args, **kwargs):
    import sys as _sys

    for mod_name, mod in list(_sys.modules.items()):
        if mod is None:
            continue
        if mod_name == "progressr" or mod_name.startswith("progressr."):
            found = getattr(mod, "handler_progress", None)
            if callable(found):
                return found(*args, **kwargs)
    raise ProgressrError("object 'handler_progress' not found")


def handler_tutorial(*args, spec=_SPEC_CHOICES, type="time", clear=False, **kwargs):
    """Select the progress or cli handler. spec matches a unique prefix."""
    spec = _match_arg(spec, _SPEC_CHOICES)
    if not _namespace_available(spec):
        raise ProgressrError(f"Please install package: {squote(spec)}")
    if spec == "cli":
        return handler_cli(*args, type=type, clear=clear, **kwargs)
    return _handler_progress(*args, type=type, clear=clear, **kwargs)
