"""Process-wide options, hooks, and the active evaluation sink.

These stand in for the R package environment and for base ``options``,
``setHook``, and ``Sys.getenv``.
"""

from __future__ import annotations

import os
from contextlib import contextmanager


class State:
    def __init__(self) -> None:
        self.inject: dict = {}
        self.console_flusher = None
        self.hooks: dict[str, list] = {}
        self.handlers: list[dict] = []
        self.stack: list = []
        self.watcher = None
        self.devices: list = []
        self.options = {
            "prompt": "> ",
            "continue": "+ ",
            "width": 80,
            "warn": 0,
            "crayon.enabled": False,
            "cli.width": 80,
            "cli.condition_width": 80,
            "cli.num_colors": 1,
            "cli.hyperlink": False,
            "cli.hyperlink_run": False,
            "cli.hyperlink_help": False,
            "cli.hyperlink_vignette": False,
            "cli.unicode": False,
            "cli.dynamic": False,
            "useFancyQuotes": False,
            "rlang_interactive": False,
            "rlang_trace_top_env": None,
        }


STATE = State()

_SENTINEL_TEXT = "eval(expr, envir)"


class Sentinel:
    def __init__(self, text: str = _SENTINEL_TEXT) -> None:
        self.text = text


SENTINEL = Sentinel()


def option(name: str, default=None):
    if name in STATE.options:
        return STATE.options[name]
    return default


def get_hook(name: str) -> list:
    return list(STATE.hooks.get(name, []))


def run_hooks(name: str) -> None:
    for fn in list(STATE.hooks.get(name, [])):
        fn()


def env_var_is_true(name: str) -> bool:
    value = os.environ.get(name, "false")
    return str(value).lower() in {"true", "t"}


@contextmanager
def push_handlers(tables: list[dict]):
    STATE.handlers = list(tables) + STATE.handlers
    try:
        yield
    finally:
        STATE.handlers = STATE.handlers[len(tables) :]


def dev_cur():
    return STATE.devices[-1] if STATE.devices else None
