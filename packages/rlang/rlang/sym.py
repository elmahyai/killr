"""Create a symbol from a string (``sym``)."""

from __future__ import annotations

from typing import Any

from rlang import is_string
from rlang.as_label import MISSING
from rlang.as_string import Symbol, _abort_coercion
from rlang.is_symbol import is_symbol


def sym(x: Any) -> Any:
    if is_symbol(x):
        return x
    if x == "":
        return MISSING
    if not is_string(x):
        _abort_coercion(x, "a symbol")
    return Symbol(x)
