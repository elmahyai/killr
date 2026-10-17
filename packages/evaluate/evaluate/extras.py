"""Hooks, injected functions, console flushing, and reproducible options."""

from __future__ import annotations

import locale
import os
from contextlib import contextmanager

from evaluate.state import STATE, get_hook, option


def set_hooks(hooks, action: str = "append"):
    action = _match_action(action)
    old = {}
    for name, value in hooks.items():
        old[name] = get_hook(name)
        fns = list(value) if isinstance(value, (list, tuple)) else [value]
        current = get_hook(name)
        if action == "replace":
            current = fns
        elif action == "prepend":
            current = fns + current
        else:
            current = current + fns
        STATE.hooks[name] = current
    return old


def remove_hooks(hooks) -> None:
    for name, value in hooks.items():
        fns = list(value) if isinstance(value, (list, tuple)) else [value]
        current = get_hook(name)
        STATE.hooks[name] = [fn for fn in current if not any(fn is item for item in fns)]


def _match_action(action: str) -> str:
    choices = ("replace", "append", "prepend")
    matches = [choice for choice in choices if choice.startswith(action)]
    if len(matches) != 1:
        raise ValueError('action must be "replace", "append", or "prepend"')
    return matches[0]


def inject_funs(*args, **kwargs):
    if len(args) == 1 and not kwargs and isinstance(args[0], dict):
        funs = args[0]
    else:
        if args:
            raise TypeError("inject_funs() takes named functions")
        funs = kwargs
    funs = {name: fn for name, fn in funs.items() if name and callable(fn)}
    old = dict(STATE.inject)
    STATE.inject = funs
    return old


def flush_console():
    flusher = STATE.console_flusher
    if flusher is not None:
        flusher()
    return None


def set_console_flusher(flusher):
    old = STATE.console_flusher
    STATE.console_flusher = flusher
    return old


@contextmanager
def local_reproducible_output(
    width: int = 80,
    color: bool = False,
    unicode: bool = False,
    hyperlinks: bool = False,
    rstudio: bool = False,
    frame=None,
):
    del frame
    saved_options = dict(STATE.options)
    names = [
        "NO_COLOR",
        "RSTUDIO",
        "RSTUDIO_SESSION_PID",
        "RSTUDIO_CHILD_PROCESS_PANE",
        "RSTUDIO_CLI_HYPERLINKS",
        "RSTUDIO_CONSOLE_WIDTH",
        "LC_COLLATE",
    ]
    saved_env = {name: os.environ.get(name) for name in names}
    saved_locale = None
    try:
        saved_locale = locale.setlocale(locale.LC_COLLATE)
    except locale.Error:
        saved_locale = None
    STATE.options["width"] = width
    STATE.options["crayon.enabled"] = bool(color)
    STATE.options["cli.width"] = width
    STATE.options["cli.condition_width"] = width
    STATE.options["cli.num_colors"] = 8 if color else 1
    STATE.options["cli.hyperlink"] = bool(hyperlinks)
    STATE.options["cli.hyperlink_run"] = bool(hyperlinks)
    STATE.options["cli.hyperlink_help"] = bool(hyperlinks)
    STATE.options["cli.hyperlink_vignette"] = bool(hyperlinks)
    STATE.options["cli.unicode"] = bool(unicode)
    STATE.options["cli.dynamic"] = False
    STATE.options["useFancyQuotes"] = bool(unicode)
    STATE.options["rlang_interactive"] = False
    _set_env("NO_COLOR", None if color else "1")
    _set_env("RSTUDIO", "1" if rstudio else None)
    _set_env("RSTUDIO_SESSION_PID", str(os.getpid()) if rstudio else None)
    _set_env("RSTUDIO_CHILD_PROCESS_PANE", "build" if rstudio else None)
    _set_env("RSTUDIO_CLI_HYPERLINKS", "1" if rstudio else None)
    _set_env("RSTUDIO_CONSOLE_WIDTH", str(width))
    _set_env("LC_COLLATE", "C")
    try:
        locale.setlocale(locale.LC_COLLATE, "C")
    except locale.Error:
        pass
    try:
        yield None
    finally:
        STATE.options.clear()
        STATE.options.update(saved_options)
        for name, value in saved_env.items():
            _set_env(name, value)
        if saved_locale is not None:
            try:
                locale.setlocale(locale.LC_COLLATE, saved_locale)
            except locale.Error:
                pass


def _set_env(name: str, value) -> None:
    if value is None:
        os.environ.pop(name, None)
    else:
        os.environ[name] = str(value)


def current_width() -> int:
    return int(option("width", 80))
