"""align<- from xtable 1.8-8 (``align<-.xtable``).

Sets the ``align`` attribute on an ``xtable`` object.
"""

from __future__ import annotations

import re
import warnings

from xtable.caption_replacement import Xtable

_ALIGN_ALLOWED = frozenset("lrpc|X")
_BRACE_END = re.compile(r"[^\\\]]}")


def _r_length(value: object) -> int:
    if value is None:
        return 0
    if isinstance(value, str):
        return 1
    if isinstance(value, (list, tuple)):
        return len(value)
    return 1


def _is_character(value: object) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return True
    if isinstance(value, (list, tuple)):
        return all(isinstance(item, str) for item in value)
    return False


def _character_element(value: object) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, (list, tuple)):
        return value[0]
    raise TypeError("expected character value")


def _align_string_to_vector(a_string: str) -> list[str]:
    align_parts: list[str] = []
    width_parts: list[str] = []
    w_string = a_string
    while len(w_string) > 0:
        align_parts.append(w_string[0])
        this_width = ""
        if len(w_string) > 1 and w_string[1] == "{":
            match = _BRACE_END.search(w_string)
            if match is None:
                raise ValueError("No closing } in align string")
            this_width = w_string[1 : match.end()]
            w_string = w_string[match.end() :]
        else:
            w_string = w_string[1:]
        width_parts.append(this_width)
    if any(part not in _ALIGN_ALLOWED for part in align_parts):
        warnings.warn("Nonstandard alignments in align string", RuntimeWarning, stacklevel=3)
    return [a + w for a, w in zip(align_parts, width_parts)]


def _c_value(value: object) -> list:
    if value is None:
        return []
    if isinstance(value, str):
        seq = [value]
    elif isinstance(value, (list, tuple)):
        seq = list(value)
    else:
        seq = [value]
    if any(item == "|" for item in seq):
        return [item for item in seq if item != "|"]
    return seq


def align_attr(x: Xtable) -> object:
    """Same as R ``attr(x, \"align\", exact = TRUE)`` for checks."""
    if "align" not in x.attrs:
        return None
    return x.attrs["align"]


def align_replacement(x: object, value: object) -> Xtable:
    if not isinstance(x, Xtable):
        raise ValueError(
            f"no applicable method for 'align<-' applied to an object of class "
            f'"{type(x).__name__}"'
        )
    stored: object = value
    if (
        value is not None
        and _is_character(value)
        and _r_length(value) == 1
        and len(_character_element(value)) > 1
    ):
        stored = _align_string_to_vector(_character_element(value))

    c_value = _c_value(stored)
    need = x.ncol + 1
    if len(c_value) != need:
        raise ValueError(
            f'"align" must have length equal to {need} ( ncol(x) + 1 )'
        )
    x.attrs["align"] = stored
    return x
