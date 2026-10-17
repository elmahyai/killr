"""The operator %<~% (lazy assignment in the caller environment)."""

from __future__ import annotations

import sys
import types
from typing import Any, Callable

from rlang import caller_arg, inject


class _LazyBinding:
    """A caller binding that evaluates once, like base::delayedAssign."""

    __slots__ = ("_name", "_thunk", "_frame", "_value", "_ready")

    def __init__(self, name: str, thunk: Callable[[], Any], frame):
        self._name = name
        self._thunk = thunk
        self._frame = frame
        self._value = None
        self._ready = False

    def force(self) -> Any:
        if self._ready:
            return self._value
        value = self._thunk()
        self._ready = True
        self._value = value
        self._frame.f_locals[self._name] = value
        return value

    def __getattr__(self, name: str) -> Any:
        return getattr(self.force(), name)

    def __bool__(self) -> bool:
        return bool(self.force())

    def __int__(self) -> int:
        return int(self.force())

    def __float__(self) -> float:
        return float(self.force())

    def __index__(self) -> int:
        return self.force().__index__()

    def __str__(self) -> str:
        return str(self.force())

    def __repr__(self) -> str:
        return repr(self.force())

    def __len__(self) -> int:
        return len(self.force())

    def __iter__(self):
        return iter(self.force())

    def __getitem__(self, key):
        return self.force()[key]


def _lhs_name(lhs) -> str:
    if isinstance(lhs, str):
        return lhs
    return caller_arg(lhs)


def _rhs_thunk(frame, rhs) -> Callable[[], Any]:
    if isinstance(rhs, types.FunctionType):
        return lambda: rhs()

    def evaluate():
        return eval(
            compile(str(rhs), "<eager_pipe>", "eval"),
            frame.f_globals,
            dict(frame.f_locals),
        )

    if isinstance(rhs, str) and not rhs.isidentifier():
        return evaluate

    return lambda captured=rhs: captured


def eager_pipe(lhs, rhs):
    """Lazily bind ``rhs`` to ``lhs`` in the caller environment."""
    name = _lhs_name(lhs)
    frame = sys._getframe(1)

    def assign():
        frame.f_locals[name] = _LazyBinding(name, _rhs_thunk(frame, rhs), frame)

    inject(assign)
    return None


def force_lazy(value):
    """Return a forced lazy binding, or ``value`` unchanged."""
    if isinstance(value, _LazyBinding):
        return value.force()
    return value
