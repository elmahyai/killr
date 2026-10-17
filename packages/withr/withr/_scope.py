"""Exit-handler scopes: the Python stand-in for R's frame exit hooks.

R runs a deferred expression when the frame it is attached to exits. Python
has no such hook, so the frame is an explicit scope::

    with scope():
        defer(lambda: print("runs when the block ends"))

Handlers are zero-argument callables. Without an explicit scope a handler goes
to the innermost active scope, or to ``GLOBAL`` when none is active (R's
``globalenv()``).
"""

from __future__ import annotations

import contextlib
from typing import Callable, Iterator


class Scope:
    """An ordered list of exit handlers, the counterpart of R's on.exit list."""

    def __init__(self, name: str = "frame") -> None:
        self.name = name
        self.exits: list[Callable[[], object]] = []

    def add(self, handler: Callable[[], object], priority: str = "first") -> None:
        if priority == "first":
            self.exits.insert(0, handler)
        elif priority == "last":
            self.exits.append(handler)
        else:
            raise ValueError('`priority` must be "first" or "last"')

    def run_exits(self) -> None:
        """Run and clear the handlers in list order.

        As with on.exit, every handler runs even when an earlier one fails;
        the first failure is re-raised afterwards.
        """
        handlers, self.exits = self.exits, []
        failure: BaseException | None = None
        for handler in handlers:
            try:
                handler()
            except BaseException as exc:  # noqa: BLE001 - re-raised below
                if failure is None:
                    failure = exc
        if failure is not None:
            raise failure


GLOBAL = Scope("global")
_STACK: list[Scope] = []


@contextlib.contextmanager
def scope() -> Iterator[Scope]:
    """Open a frame: handlers added inside it run when the block exits."""
    frame = Scope()
    _STACK.append(frame)
    try:
        yield frame
    finally:
        try:
            frame.run_exits()
        finally:
            _STACK.pop()


@contextlib.contextmanager
def private_scope() -> Iterator[Scope]:
    """A frame that is not on the stack, so defer() in the block cannot reach it."""
    frame = Scope()
    try:
        yield frame
    finally:
        frame.run_exits()


def current(envir: Scope | None = None) -> Scope:
    """The frame named by ``envir``; the innermost scope when it is None."""
    if envir is None:
        return _STACK[-1] if _STACK else GLOBAL
    if isinstance(envir, Scope):
        return envir
    raise TypeError("envir must be a scope() or GLOBAL")


def enclosing() -> Scope:
    """The frame one level above the innermost one (R's parent.frame(2))."""
    return _STACK[-2] if len(_STACK) >= 2 else GLOBAL


def callable_or_raise(code):
    if not callable(code):
        raise TypeError(
            "expected a zero-argument callable; R evaluates code lazily, "
            "so pass lambda: ... in Python"
        )
    return code


def force(code):
    """Evaluate ``code``: R forces a lazy argument, Python calls a callable."""
    return callable_or_raise(code)()
