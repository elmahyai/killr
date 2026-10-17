"""Required values, from shiny 1.14.0 `R/utils.R`."""

from __future__ import annotations

from shiny.truthy import isTruthy
from shiny.values import Vector, WithClass


class SilentError(Exception):
    """The silent condition `req` raises when a value is not truthy."""

    def __init__(self, classes, message: str = "") -> None:
        super().__init__(message)
        self.classes = tuple(classes)
        self.message = message


class MissingDotError(Exception):
    """A missing element of `...`, as in ``req(1, )``."""

    def __init__(self, index: int) -> None:
        message = f'argument "..{index}" is missing, with no default'
        super().__init__(message)
        self.classes = (
            "evalError",
            "missingArgError",
            "error",
            "condition",
        )
        self.message = message


class MissingArg:
    """One missing `...` argument. R writes this as ``req(1, )``."""


class Delayed:
    """An R promise. Forced once, the first time `req` reaches it."""

    def __init__(self, fn) -> None:
        self._fn = fn
        self._forced = False
        self._value = None

    def force(self):
        if not self._forced:
            self._value = self._fn()
            self._forced = True
        return self._value


def req(*args, cancelOutput=False):
    """Return the first value when every value is truthy.

    A value that is not truthy stops the call. The default failure is a
    silent validation error. ``cancelOutput=True`` leaves an output as it
    was, and ``cancelOutput="progress"`` keeps that output recalculating.
    ``cancelOutput`` is exact: a shorter name is another value, not this
    argument. A :class:`Delayed` value is forced only when the check reaches
    it, and only once. No values returns ``None``.
    """
    for index, arg in enumerate(args, start=1):
        item = _force(arg, index)
        if not isTruthy(item):
            _reject(cancelOutput)
    if not args:
        return None
    return _force(args[0], 1)


def _force(arg, index: int):
    if isinstance(arg, MissingArg):
        raise MissingDotError(index)
    if isinstance(arg, Delayed):
        return arg.force()
    return arg


def _reject(cancel_output) -> None:
    if _is_true(cancel_output):
        raise SilentError(
            (
                "shiny.silent.error",
                "shiny.output.cancel",
                "error",
                "condition",
            )
        )
    if _identical_progress(cancel_output):
        raise SilentError(
            (
                "shiny.silent.error",
                "shiny.output.progress",
                "error",
                "condition",
            )
        )
    raise SilentError(
        ("shiny.silent.error", "validation", "error", "condition")
    )


def _is_true(value) -> bool:
    """R's ``isTRUE``: one non-missing logical TRUE. Names and class stay."""
    if isinstance(value, WithClass):
        value = value.value
    if isinstance(value, bool):
        return value is True
    if (
        isinstance(value, Vector)
        and value.mode == "logical"
        and len(value.data) == 1
    ):
        return value.data[0] is True
    return False


def _identical_progress(value) -> bool:
    """R's ``identical(cancelOutput, "progress")``. Attributes are not it."""
    if isinstance(value, WithClass):
        return False
    if isinstance(value, str):
        return value == "progress"
    if isinstance(value, Vector):
        if value.classes or getattr(value, "names", None) is not None:
            return False
        if value.mode != "character" or len(value.data) != 1:
            return False
        item = value.data[0]
        return isinstance(item, str) and item == "progress"
    return False
