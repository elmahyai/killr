"""Pipes translated from magrittr 2.0.5.

A callable step is invoked with the current value. A step
``(function, args, kwargs)`` inserts that value first unless ``DOT`` is
one of the args or kwargs, in which case ``DOT`` is replaced and the
value is not also inserted first.
"""

from __future__ import annotations

import inspect
import operator

from magrittr._fseq import FSeq


class _Placeholder:
    def __repr__(self) -> str:
        return "DOT"


DOT = _Placeholder()


class _Lazy:
    """Value that runs the previous pipe step the first time it is used."""

    def __init__(self, thunk):
        self._thunk = thunk
        self._ready = False
        self._value = None

    def force(self):
        if self._ready:
            return self._value
        self._ready = True
        value = self._thunk()
        while isinstance(value, _Lazy):
            value = value.force()
        self._value = value
        return self._value

    def __getattr__(self, name):
        return getattr(self.force(), name)

    def __iter__(self):
        return iter(self.force())

    def __len__(self):
        return len(self.force())

    def __getitem__(self, key):
        return self.force()[key]

    def __bool__(self):
        return bool(self.force())

    def __int__(self):
        return int(self.force())

    def __float__(self):
        return float(self.force())

    def __index__(self):
        return operator.index(self.force())

    def __str__(self):
        return str(self.force())

    def __repr__(self):
        return repr(self.force())


def _force(value):
    if isinstance(value, _Lazy):
        return value.force()
    return value


def _binary(op):
    def method(self, other):
        return op(_force(self), _force(other))

    return method


def _reflected(op):
    def method(self, other):
        return op(_force(other), _force(self))

    return method


for _name, _op in (
    ("__add__", operator.add),
    ("__sub__", operator.sub),
    ("__mul__", operator.mul),
    ("__truediv__", operator.truediv),
    ("__floordiv__", operator.floordiv),
    ("__mod__", operator.mod),
    ("__pow__", operator.pow),
    ("__eq__", operator.eq),
    ("__ne__", operator.ne),
    ("__lt__", operator.lt),
    ("__le__", operator.le),
    ("__gt__", operator.gt),
    ("__ge__", operator.ge),
):
    setattr(_Lazy, _name, _binary(_op))

for _name, _op in (
    ("__radd__", operator.add),
    ("__rsub__", operator.sub),
    ("__rmul__", operator.mul),
    ("__rtruediv__", operator.truediv),
    ("__rfloordiv__", operator.floordiv),
    ("__rmod__", operator.mod),
    ("__rpow__", operator.pow),
):
    setattr(_Lazy, _name, _reflected(_op))

_Lazy.__hash__ = None


def _split(step):
    if not isinstance(step, tuple) or len(step) != 3:
        raise TypeError(
            "a pipe step must be a callable or (function, args, kwargs)"
        )
    fn, args, kwargs = step
    if isinstance(args, (str, bytes)):
        raise TypeError("pipe step args must be a sequence of arguments")
    return fn, tuple(args), dict(kwargs)


def _dot_count(args, kwargs) -> int:
    return sum(item is DOT for item in args) + sum(
        item is DOT for item in kwargs.values()
    )


def _apply(step, value):
    if not isinstance(step, tuple):
        return step(value)
    fn, args, kwargs = _split(step)
    if _dot_count(args, kwargs):
        args = tuple(value if item is DOT else item for item in args)
        kwargs = {
            key: value if item is DOT else item for key, item in kwargs.items()
        }
        return fn(*args, **kwargs)
    return fn(value, *args, **kwargs)


def _unary(step):
    if not isinstance(step, tuple):
        return step

    def call(value):
        return _apply(step, value)

    return call


def _as_sequence(lhs, steps):
    return FSeq([_unary(step) for step in steps])


def _lazy(lhs, steps):
    if lhs is DOT:
        return _as_sequence(lhs, steps)
    if not steps:
        return lhs

    def compute(index):
        if index < 0:
            return lhs
        delayed = _Lazy(lambda index=index: compute(index - 1))
        return _apply(steps[index], delayed)

    return _force(compute(len(steps) - 1))


def _eager(lhs, steps):
    if lhs is DOT:
        return _as_sequence(lhs, steps)
    value = lhs
    for step in steps:
        value = _apply(step, value)
    return value


def _tee(lhs, steps):
    if lhs is DOT:
        wrapped = []
        for step in steps:
            unary = _unary(step)

            def call(value, unary=unary):
                unary(value)
                return value

            wrapped.append(call)
        return FSeq(wrapped)
    if not steps:
        return lhs

    def run(index):
        if index < 0:
            return lhs
        # The brace evaluates the dot after the call, so earlier steps run
        # even when this step never uses its argument. The piped value stays
        # the input, not the call's return value.
        delayed = _Lazy(lambda index=index: run(index - 1))
        _apply(steps[index], delayed)
        return _force(delayed)

    return run(len(steps) - 1)


def _reject_multiple(steps):
    for step in steps:
        if isinstance(step, tuple):
            _, args, kwargs = _split(step)
            if _dot_count(args, kwargs) > 1:
                raise ValueError("Can't use multiple placeholders.")


def pipe(lhs, *steps):
    """R ``%>%``. Lazy: side effects run from the last step backward."""
    return _lazy(lhs, steps)


def pipe_lazy_masking(lhs, *steps):
    """Lazy pipe. Same observable result as ``pipe``."""
    return _lazy(lhs, steps)


def pipe_nested(lhs, *steps):
    """Nested pipe. Pure functions match ``pipe``.

    More than one top-level ``DOT`` in a step is an error. A chain that
    starts at ``DOT`` is still a functional sequence.
    """
    if lhs is not DOT:
        _reject_multiple(steps)
    return _lazy(lhs, steps)


def pipe_eager_lexical(lhs, *steps):
    """Eager pipe. Each step runs immediately, so side effects run forward."""
    return _eager(lhs, steps)


eager = pipe_eager_lexical


def compound(value, *steps):
    """R ``%<>%``.

    ``compound(value, *steps)`` returns the piped value.
    ``compound(namespace, name, *steps)`` writes that result into the dict.
    """
    if isinstance(value, dict) and steps and isinstance(steps[0], str):
        name = steps[0]
        result = _lazy(value[name], steps[1:])
        value[name] = result
        return result
    return _lazy(value, steps)


def tee(lhs, *steps):
    """R ``%T>%``. Run the steps and return the original left-hand side."""
    return _tee(lhs, steps)


def exposition(mapping, fn):
    """R ``%$%``. Pass mapping entries whose names the function declares."""
    signature = inspect.signature(fn)
    positional = []
    keywords = {}
    for name, param in signature.parameters.items():
        if param.kind in (
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        ):
            continue
        if name not in mapping:
            continue
        if param.kind is inspect.Parameter.POSITIONAL_ONLY:
            positional.append(mapping[name])
        else:
            keywords[name] = mapping[name]
    return fn(*positional, **keywords)
