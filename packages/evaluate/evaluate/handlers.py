"""Output handlers."""

from __future__ import annotations

import inspect

from evaluate.show import r_print
from evaluate.types import Invisible, Source


def identity(x):
    return x


def n_formals(fn) -> int:
    signature = inspect.signature(fn)
    return len(signature.parameters)


def match_fun(fn):
    if isinstance(fn, str):
        frame = inspect.currentframe()
        caller = frame.f_back.f_back if frame is not None and frame.f_back is not None else None
        found = None
        if caller is not None:
            found = caller.f_locals.get(fn, caller.f_globals.get(fn))
        if found is None:
            found = globals().get(fn)
        if found is None or not callable(found):
            raise ValueError(f"could not find function {fn!r}")
        fn = found
    if not callable(fn):
        raise TypeError("output handler must be a function")
    return fn


def render(value, visible, envir=None):
    if not visible:
        return Invisible(None)
    r_print(value)
    return Invisible(None)


def new_output_handler(
    source=None,
    text=None,
    graphics=None,
    message=None,
    warning=None,
    error=None,
    value=None,
    calling_handlers=None,
):
    source = identity if source is None else match_fun(source)
    text = identity if text is None else match_fun(text)
    graphics = identity if graphics is None else match_fun(graphics)
    message = identity if message is None else match_fun(message)
    warning = identity if warning is None else match_fun(warning)
    error = identity if error is None else match_fun(error)
    value = render if value is None else match_fun(value)
    for name, fn in (
        ("source", source),
        ("text", text),
        ("graphics", graphics),
        ("message", message),
        ("warning", warning),
        ("error", error),
        ("value", value),
    ):
        if n_formals(fn) < 1:
            raise ValueError(f"{name} output handler must accept at least one argument")
    if calling_handlers is None:
        calling_handlers = {}
    _check_handlers(calling_handlers)
    return {
        "source": source,
        "text": text,
        "graphics": graphics,
        "message": message,
        "warning": warning,
        "error": error,
        "value": value,
        "calling_handlers": calling_handlers,
    }


def _check_handlers(handlers) -> None:
    if not isinstance(handlers, dict):
        _bad_handlers()
    if not handlers:
        return
    for name, fn in handlers.items():
        if not isinstance(name, str) or name == "":
            _bad_handlers()
        if not callable(fn):
            _bad_handlers()


def _bad_handlers() -> None:
    raise ValueError("`calling_handlers` must be a named list of functions.")


def new_source(src, call, handler=None):
    source = Source(src if isinstance(src, str) else str(src))
    if handler is None:
        return source
    nargs = n_formals(handler)
    if nargs == 1:
        handler(source)
        return source
    if nargs == 2:
        return handler(source, call)
    raise ValueError("Source output handler must have one or two arguments")


def show_value(handler, visible: bool) -> bool:
    return bool(visible) or n_formals(handler["value"]) > 1


def handle_value(handler, value, visible, envir):
    fn = handler["value"]
    nargs = n_formals(fn)
    if nargs == 1:
        result = fn(value)
    elif nargs == 2:
        result = fn(value, visible)
    elif nargs == 3:
        result = fn(value, visible, envir)
    else:
        raise ValueError("Value output handler must have one or two arguments")
    if isinstance(result, Invisible):
        return result.value, False
    return result, True
