"""Is object a symbol?"""

from __future__ import annotations

from collections.abc import Sequence

from rlang import is_null
from rlang.as_string import Symbol, as_string


def is_symbol(x: object, name: str | Sequence[str] | None = None) -> bool:
    if not isinstance(x, Symbol):
        return False
    if is_null(name):
        return True
    text = as_string(x)
    if isinstance(name, str):
        return text in (name,)
    return text in name
