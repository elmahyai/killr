"""Progression conditions and the calling-handler stack."""

from __future__ import annotations

import contextvars
import sys
import traceback
from datetime import datetime, timedelta

from progressr.options import ProgressrError, stop_if_not
from progressr.uuid import session_uuid


_HANDLERS = contextvars.ContextVar("progressr_calling_handlers", default=())
_RESTARTS = contextvars.ContextVar("progressr_restarts", default=())


class Condition(dict):
    """A named list with a class vector, like an R condition."""

    def __init__(self, data, classes):
        super().__init__(data)
        self.classes = tuple(classes)

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError as exc:
            raise AttributeError(name) from exc

    def __repr__(self) -> str:
        shown = ", ".join(f"{key}={value!r}" for key, value in self.items())
        return f"Condition({shown}, classes={self.classes!r})"


class _Muffle(Exception):
    def __init__(self, name, condition):
        self.name = name
        self.condition = condition


def inherits(obj, classes) -> bool:
    if isinstance(classes, str):
        wanted = (classes,)
    else:
        wanted = tuple(classes)
    own = getattr(obj, "classes", None)
    if not own:
        return False
    return any(name in own for name in wanted)


def signal_condition(condition) -> None:
    """Walk calling handlers from the inside out. An unhandled progression does not raise."""
    stack = _HANDLERS.get()
    for frame in reversed(stack):
        for class_name, handler in frame:
            if class_name == "condition" or inherits(condition, class_name):
                handler(condition)


def with_calling_handlers(fn, **handlers):
    pairs = tuple(handlers.items())
    token = _HANDLERS.set(_HANDLERS.get() + (pairs,))
    try:
        return fn()
    finally:
        _HANDLERS.reset(token)


def invoke_restart(name, condition=None):
    for restart_name, _func in reversed(_RESTARTS.get()):
        if restart_name == name:
            raise _Muffle(name, condition)
    raise ProgressrError(f"restart {name} not found")


def muffle_matching(condition, prefix="muffle") -> bool:
    """Invoke the first restart whose name starts with prefix, if one is active."""
    for name, _func in reversed(_RESTARTS.get()):
        if name and name.startswith(prefix):
            invoke_restart(name, condition)
            return True
    return False


def try_invoke_restart(name, condition=None) -> bool:
    if not any(restart_name == name for restart_name, _func in _RESTARTS.get()):
        return False
    invoke_restart(name, condition)
    return True


def with_restarts(fn, **restarts):
    items = tuple(restarts.items())
    token = _RESTARTS.set(_RESTARTS.get() + items)
    try:
        return fn()
    except _Muffle as exc:
        for name, func in items:
            if name == exc.name:
                return func(exc.condition)
        raise
    finally:
        _RESTARTS.reset(token)


def _sys_calls():
    stack = traceback.extract_stack()[:-2]
    return tuple(frame.name for frame in stack)


def format_progression_time(value) -> str:
    """R format '%F %H:%M:%OS3 %z': three fractional digits and a numeric offset."""
    if isinstance(value, str):
        return value
    if not isinstance(value, datetime):
        raise ProgressrError("progression_time must be a datetime or a character string")
    if value.tzinfo is None:
        value = value.astimezone()
    else:
        value = value.astimezone()
    milliseconds = int(round(value.microsecond / 1000.0))
    if milliseconds == 1000:
        value = value + timedelta(seconds=1)
        milliseconds = 0
        value = value.astimezone()
    offset = value.strftime("%z") or "+0000"
    return f"{value.strftime('%Y-%m-%d %H:%M:%S')}.{milliseconds:03d} {offset}"


def _as_posixct(value):
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.astimezone()
        return value.astimezone()
    if isinstance(value, str):
        text = value.strip()
        # Accept the formatted progression time, or an ISO string.
        for parser in (
            lambda item: datetime.strptime(item, "%Y-%m-%d %H:%M:%S.%f %z"),
            lambda item: datetime.fromisoformat(item),
        ):
            try:
                parsed = parser(text)
            except ValueError:
                continue
            if parsed.tzinfo is None:
                return parsed.astimezone()
            return parsed.astimezone()
        raise ProgressrError("character string is not in a standard unambiguous format")
    raise ProgressrError("time must be a datetime or a character string")


def _as_numeric(value) -> float:
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        return float(value)
    raise ProgressrError("amount must be numeric")


def _empty_character(message) -> bool:
    if message is None:
        return True
    if isinstance(message, (list, tuple)) and len(message) == 0:
        return True
    return False


def condition_message(condition) -> str:
    """Paste character pieces with an empty separator. A function is called with the condition."""
    message = condition["message"] if isinstance(condition, dict) else condition
    if callable(message):
        message = message(condition)
    if _empty_character(message):
        return ""
    if isinstance(message, (list, tuple)):
        return "".join("" if piece is None else str(piece) for piece in message)
    return "" if message is None else str(message)


_CALLS_OMITTED = object()


def progression(
    message=(),
    amount=1.0,
    step=None,
    time=None,
    type="update",
    class_=None,
    progressor_uuid=None,
    progression_index=None,
    progression_time=None,
    call=None,
    calls=_CALLS_OMITTED,
    owner_session_uuid=None,
    **extra,
):
    """A progression condition. `class_` is R's `class` argument."""
    amount = _as_numeric(amount)
    if progression_time is None:
        progression_time = datetime.now().astimezone()
    if time is None:
        time = progression_time
    time = _as_posixct(time)
    stop_if_not(isinstance(type, str))
    if isinstance(progression_time, datetime):
        progression_time = format_progression_time(progression_time)
    stop_if_not(isinstance(progression_time, str))
    if extra:
        names = list(extra)
        stop_if_not(all(isinstance(name, str) and name != "" for name in names))
        stop_if_not(len(set(names)) == len(names))
    if class_ is None:
        prefix = ()
    elif isinstance(class_, str):
        prefix = (class_,)
    else:
        prefix = tuple(class_)
    if calls is _CALLS_OMITTED:
        calls = _sys_calls()
    data = {
        "owner_session_uuid": owner_session_uuid,
        "progressor_uuid": progressor_uuid,
        "session_uuid": session_uuid(),
        "progression_index": progression_index,
        "progression_time": progression_time,
        "type": type,
        "message": message,
        "amount": amount,
        "step": None if step is None else _as_numeric(step),
        "time": time,
    }
    data.update(extra)
    data["call"] = call
    data["calls"] = calls
    classes = prefix + ("progression", "immediateCondition", "condition")
    return Condition(data, classes)


def control_progression(type="shutdown", **kwargs):
    """progression(..., class = 'control_progression')."""
    return progression(type=type, class_=kwargs.pop("class_", "control_progression"), **kwargs)


def message(text=""):
    """Signal a message condition. A muffleMessage restart swallows the print."""
    condition = Condition({"message": text}, ("message", "condition"))

    def go():
        signal_condition(condition)
        print(condition_message(condition), file=sys.stderr)

    return with_restarts(go, muffleMessage=lambda _condition: None)


def r_warning(text=""):
    """Signal a warning condition. A muffleWarning restart swallows it."""
    import warnings

    condition = Condition({"message": text}, ("warning", "condition"))

    def go():
        signal_condition(condition)
        warnings.warn(condition_message(condition), stacklevel=2)

    return with_restarts(go, muffleWarning=lambda _condition: None)


def _format_scalar(value) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, float):
        text = format(value, ".12g")
        return text
    return str(value)


def format_progression(condition) -> str:
    """Print method. The size line is local and is not compared to R."""
    classes = condition.classes
    lines = [f"{classes[0]}:"]
    call = condition.get("call")
    lines.append(f"- call: {call}")
    lines.append(f"- type: {condition.get('type')}")
    message_class = type(condition.get("message")).__name__
    lines.append(
        f"- message: [{message_class}] {squote_message(condition)}"
    )
    lines.append(f"- amount: {_format_scalar(condition.get('amount'))}")
    lines.append(f"- step: {_format_scalar(condition.get('step'))}")
    lines.append(f"- time: {condition.get('time')}")
    lines.append(f"- progressor_uuid: {condition.get('progressor_uuid')}")
    lines.append(f"- progression_index: {condition.get('progression_index')}")
    lines.append(f"- progression_time: {condition.get('progression_time')}")
    lines.append(f"- session_uuid: {condition.get('session_uuid')}")
    lines.append(f"- owner_session_uuid: {condition.get('owner_session_uuid')}")
    from progressr.options import squote

    quoted = ", ".join(squote(name) for name in classes)
    lines.append(f"- classes: {quoted}")
    lines.append(f"- size: {sys.getsizeof(condition)} bytes")
    return "\n".join(lines)


def squote_message(condition) -> str:
    from progressr.options import squote

    return squote(condition_message(condition))
