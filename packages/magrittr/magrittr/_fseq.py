"""Functional sequence created by a pipe that starts with the dot.

Other modules import this class. Do not give it a second definition.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence


class FSeq:
    def __init__(self, function_list: Sequence[Callable]):
        self._function_list = list(function_list)

    def __call__(self, value):
        steps = self._function_list
        if not steps:
            return value
        for fn in steps[:-1]:
            value = fn(value)
        return steps[-1](value)
