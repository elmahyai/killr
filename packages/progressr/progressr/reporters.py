"""Text, bell, file-size, and slowdown progression handlers."""

from __future__ import annotations

import math
import os
import sys
import time
from datetime import datetime, timedelta

from progressr.condition import condition_message
from progressr.condition import message as signal_message
from progressr.factory import make_progression_handler
from progressr.options import ProgressrError, file_test_f, get_option, stop_if_not


def _clock():
    return datetime.now().astimezone()


def _cat(file, text):
    """R cat(). A stream is written as it stands. A path is opened and truncated."""
    if hasattr(file, "write") and not isinstance(file, (str, bytes, os.PathLike)):
        file.write(text)
        flush = getattr(file, "flush", None)
        if flush is not None:
            flush()
        return
    path = os.fspath(file)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def _as_path(file):
    if isinstance(file, (str, bytes, os.PathLike)):
        return os.fspath(file)
    name = getattr(file, "name", None)
    if isinstance(name, (str, bytes)) and not str(name).startswith("<"):
        return str(name)
    return None


def _logical_text(value) -> str:
    if value is True:
        return "TRUE"
    if value is False:
        return "FALSE"
    return "" if value is None else str(value)


def _paste_message(message) -> str:
    """paste(c(message, ''), collapse = '')."""
    if message is None or message == () or message == []:
        return ""
    if isinstance(message, (list, tuple)):
        return "".join("" if piece is None else str(piece) for piece in message)
    return str(message)


def _plus_g(value) -> str:
    """R sprintf('%+g', value)."""
    number = float(value)
    if number == 0.0:
        return "+0" if math.copysign(1.0, number) > 0 else "-0"
    return format(number, "+.6g")


def _format_now(moment) -> str:
    """R now(): '[%H:%M:%OS3] '."""
    if moment.tzinfo is None:
        moment = moment.astimezone()
    milliseconds = int(round(moment.microsecond / 1000.0))
    if milliseconds == 1000:
        moment = moment + timedelta(seconds=1)
        milliseconds = 0
        moment = moment.astimezone()
    return moment.strftime("[%H:%M:%S.") + f"{milliseconds:03d}] "


def _r_true(value) -> bool:
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        if isinstance(value, float) and math.isnan(value):
            return False
        return value != 0
    return bool(value)


def _duration_length(duration) -> int:
    if duration is None:
        return 0
    if isinstance(duration, (str, bytes, bool)) or isinstance(duration, (int, float)):
        return 1
    if isinstance(duration, (list, tuple)):
        return len(duration)
    return 1


def _check_duration(duration) -> float:
    """R stopifnot(length == 1, is.numeric, is.finite, duration >= 0)."""
    if _duration_length(duration) != 1:
        raise ProgressrError("length(duration) == 1L is not TRUE")
    if isinstance(duration, bool) or not isinstance(duration, (int, float)):
        raise ProgressrError("is.numeric(duration) is not TRUE")
    if not math.isfinite(float(duration)):
        raise ProgressrError("is.finite(duration) is not TRUE")
    if duration < 0:
        raise ProgressrError("duration >= 0 is not TRUE")
    return float(duration)


def handler_void(intrusiveness=0, target="void", enable=False, **extra):
    """Progression handler that reports nothing."""

    def initiate(config, state, progression, **kwargs):
        return None

    def update(config, state, progression, **kwargs):
        return None

    def finish(config, state, progression, **kwargs):
        return None

    reporter = {"initiate": initiate, "update": update, "finish": finish}
    return make_progression_handler(
        "void",
        reporter,
        intrusiveness=intrusiveness,
        target=target,
        enable=enable,
        **extra,
    )


def handler_newline(
    symbol="\n",
    file=None,
    intrusiveness=None,
    target="terminal",
    **extra,
):
    """Write a symbol on initiate, update, and finish. Interrupt writes a framed message."""
    if file is None:
        file = sys.stderr
    if intrusiveness is None:
        intrusiveness = get_option("progressr.intrusiveness.debug", 0)

    def hide(*args, **kwargs):
        return None

    def unhide(*args, **kwargs):
        return None

    def interrupt(config, state, progression, **kwargs):
        msg = condition_message(progression)
        _cat(file, "\n".join(("", msg, "")))
        return None

    def initiate(*args, **kwargs):
        _cat(file, symbol)
        return None

    def update(*args, **kwargs):
        _cat(file, symbol)
        return None

    def finish(*args, **kwargs):
        _cat(file, symbol)
        return None

    reporter = {
        "hide": hide,
        "unhide": unhide,
        "interrupt": interrupt,
        "initiate": initiate,
        "update": update,
        "finish": finish,
    }
    return make_progression_handler(
        "newline",
        reporter,
        intrusiveness=intrusiveness,
        target=target,
        **extra,
    )


def handler_debug(
    interval=None,
    intrusiveness=None,
    target="terminal",
    uuid=False,
    **extra,
):
    """Write one debug line for each reported progression."""
    if interval is None:
        interval = get_option("progressr.interval", 0)
    if intrusiveness is None:
        intrusiveness = get_option("progressr.intrusiveness.debug", 0)
    t_init = {"value": None}

    def add_to_log(config, state, progression, **kwargs):
        moment = _clock()
        if t_init["value"] is None:
            t_init["value"] = moment
        dt = (moment - t_init["value"]).total_seconds()
        started = progression.get("time")
        if isinstance(started, datetime):
            if started.tzinfo is None:
                started = started.astimezone()
            delay = (moment - started).total_seconds()
        else:
            delay = 0.0
        status = progression.get("status")
        status_text = "" if status is None else str(status)
        line = (
            f"{_format_now(moment)}({dt:.3f}s => +{delay:.3f}s) {progression.get('type')}: "
            f"{float(state.get('step')):.0f}/{float(config.get('max_steps')):.0f} "
            f"({_plus_g(state.get('delta'))}) '{_paste_message(state.get('message'))}' "
            f"{{clear={_logical_text(config.get('clear'))}, "
            f"enabled={_logical_text(state.get('enabled'))}, status={status_text}}}"
        )
        if _r_true(uuid):
            line = (
                f"{line} [progressor={progression.get('progressor_uuid')}, "
                f"owner={progression.get('owner_session_uuid')}]"
            )
        signal_message(line)
        return None

    def reset(*args, **kwargs):
        t_init["value"] = None
        return None

    def hide(*args, **kwargs):
        return None

    def unhide(*args, **kwargs):
        return None

    def interrupt(config, state, progression, **kwargs):
        return add_to_log(config, state, progression)

    def initiate(config, state, progression, **kwargs):
        return add_to_log(config, state, progression)

    def update(config, state, progression, **kwargs):
        return add_to_log(config, state, progression)

    def finish(config, state, progression, **kwargs):
        return add_to_log(config, state, progression)

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
        "debug",
        reporter,
        interval=interval,
        intrusiveness=intrusiveness,
        target=target,
        **extra,
    )


def handler_slowdown(
    duration=10.0,
    intrusiveness=0,
    target="void",
    enable=None,
    **extra,
):
    """Sleep amount * duration / max_steps on each enabled update."""
    duration = _check_duration(duration)
    if enable is None:
        enable = get_option("progressr.enable", True)

    def initiate(config, state, progression, **kwargs):
        return None

    def update(config, state, progression, **kwargs):
        if not state["enabled"]:
            return None
        delta = duration / config["max_steps"]
        time.sleep(progression["amount"] * delta)
        return None

    def finish(config, state, progression, **kwargs):
        return None

    reporter = {"initiate": initiate, "update": update, "finish": finish}
    return make_progression_handler(
        "slowdown",
        reporter,
        intrusiveness=intrusiveness,
        target=target,
        enable=enable,
        **extra,
    )


def handler_ascii_alert(
    symbol="\a",
    file=None,
    intrusiveness=None,
    target=("terminal", "audio"),
    **extra,
):
    """Write a symbol on a non-zero update. Interrupt writes the framed message."""
    if file is None:
        file = sys.stderr
    if intrusiveness is None:
        intrusiveness = get_option("progressr.intrusiveness.audio", 5.0)

    def hide(*args, **kwargs):
        return None

    def unhide(*args, **kwargs):
        return None

    def interrupt(config, state, progression, **kwargs):
        msg = condition_message(progression)
        _cat(file, "\n".join(("", msg, "")))
        return None

    def update(config, state, progression, **kwargs):
        if state["enabled"] and progression["amount"] != 0:
            _cat(file, symbol)
        return None

    reporter = {
        "hide": hide,
        "unhide": unhide,
        "interrupt": interrupt,
        "update": update,
    }
    return make_progression_handler(
        "ascii_alert",
        reporter,
        intrusiveness=intrusiveness,
        target=target,
        **extra,
    )


def _current_file_size(file):
    """file.size(). None stands for NA, which is a missing file."""
    path = _as_path(file)
    if path is None:
        return 0
    if not os.path.exists(path):
        return None
    try:
        return os.path.getsize(path)
    except OSError:
        return None


def _create_file(file):
    path = _as_path(file)
    if path is None:
        return
    try:
        descriptor = os.open(path, os.O_CREAT | os.O_WRONLY, 0o666)
    except OSError:
        return
    os.close(descriptor)


def _write_filesize(file, text):
    if hasattr(file, "write") and not isinstance(file, (str, bytes, os.PathLike)):
        if hasattr(file, "seek"):
            try:
                file.seek(0)
            except OSError:
                pass
        if hasattr(file, "truncate"):
            file.truncate(0)
        file.write(text)
        flush = getattr(file, "flush", None)
        if flush is not None:
            flush()
        return
    path = _as_path(file)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def handler_filesize(
    file="default.progress",
    intrusiveness=None,
    target="file",
    enable=None,
    **extra,
):
    """Report progress by the size of a file, from 0 to 100 bytes."""
    if intrusiveness is None:
        intrusiveness = get_option("progressr.intrusiveness.file", 5)
    if enable is None:
        enable = get_option("progressr.enable", True)

    def set_file_size(config, state, progression, message=None):
        if message is None:
            message = state.get("message")
        max_steps = config["max_steps"]
        stop_if_not(
            isinstance(max_steps, (int, float)) and not isinstance(max_steps, bool),
            max_steps == max_steps and math.isfinite(float(max_steps)) and float(max_steps) >= 0,
        )
        if max_steps == 0:
            ratio = 1.0
        else:
            ratio = state["step"] / max_steps
        size = int(round(100 * ratio))
        if _current_file_size(file) is None:
            _create_file(file)
        if size == 0:
            return
        if progression["amount"] == 0:
            return
        head = f"{format(float(state['step']), 'g')}/{format(float(max_steps), 'g')}: "
        tail = f" [{int(round(100 * ratio))}%]"
        mid = _paste_message(message)
        padding = size - (len(head) + len(mid) + len(tail))
        if padding <= 0:
            text = head + mid + tail
            if padding < 0:
                text = text[:size]
        else:
            mid = mid + " " + ("." * (padding - 1))
            text = head + mid + tail
        _write_filesize(file, text)

    def initiate(config, state, progression, **kwargs):
        if not state["enabled"]:
            return None
        set_file_size(config, state, progression)
        return None

    def interrupt(config, state, progression, **kwargs):
        if not state["enabled"]:
            return None
        set_file_size(config, state, progression, message=condition_message(progression))
        return None

    def update(config, state, progression, **kwargs):
        if not state["enabled"]:
            return None
        set_file_size(config, state, progression)
        return None

    def finish(config, state, progression, **kwargs):
        if not state["enabled"]:
            return None
        if config["clear"]:
            path = _as_path(file)
            if path is not None and file_test_f(path):
                os.remove(path)
        else:
            set_file_size(config, state, progression)
        return None

    reporter = {
        "initiate": initiate,
        "interrupt": interrupt,
        "update": update,
        "finish": finish,
    }
    return make_progression_handler(
        "filesize",
        reporter,
        intrusiveness=intrusiveness,
        target=target,
        enable=enable,
        **extra,
    )
