"""Extract names from symbols (``as_name``)."""

from __future__ import annotations

from typing import Any

from rlang.as_label import Quosure
from rlang.as_string import as_string


def as_name(x: Any) -> str:
    if isinstance(x, Quosure):
        x = x.expr
    return as_string(x)
