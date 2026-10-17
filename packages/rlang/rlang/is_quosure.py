"""Test whether an object is a quosure."""

from __future__ import annotations

from rlang.as_label import Quosure


def is_quosure(x: object) -> bool:
    return isinstance(x, Quosure)
