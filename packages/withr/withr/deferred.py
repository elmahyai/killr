"""defer, defer_parent, deferred_clear, deferred_run, global_defer (R's defer.R)."""

from __future__ import annotations

import atexit
import sys

from ._scope import GLOBAL, callable_or_raise, current, enclosing

_ATEXIT_REGISTERED = False


def _message(text: str) -> None:
    print(text, file=sys.stderr)


def defer(expr, envir=None, priority: str = "first") -> None:
    """Run ``expr`` (a zero-argument callable) when ``envir`` exits.

    ``envir`` is a ``scope()``; without one, the innermost scope (or GLOBAL).
    ``priority="first"`` runs before handlers already attached; ``"last"`` after.
    """
    current(envir).add(callable_or_raise(expr), priority)


def defer_parent(expr, priority: str = "first") -> None:
    """Attach ``expr`` to the frame that called the current one."""
    enclosing().add(callable_or_raise(expr), priority)


def deferred_clear(envir=None) -> None:
    """Drop the handlers of ``envir`` without running them."""
    current(envir).exits = []


def deferred_run(envir=None) -> None:
    """Run and clear the handlers of ``envir`` now, then report how many ran."""
    frame = current(envir)
    handlers, frame.exits = frame.exits, []
    total = len(handlers)
    if total == 0:
        _message("No deferred expressions to run")
        return None
    done = 0
    try:
        for handler in handlers:
            handler()
            done += 1
    finally:
        _message(f"Ran {done}/{total} deferred expressions")
    return None


def global_defer(expr, priority: str = "first") -> None:
    """Attach ``expr`` to the global frame; it runs on deferred_run() or at exit."""
    global _ATEXIT_REGISTERED
    if not GLOBAL.exits and not _ATEXIT_REGISTERED:
        atexit.register(lambda: deferred_run(GLOBAL))
        _ATEXIT_REGISTERED = True
    GLOBAL.add(callable_or_raise(expr), priority)
