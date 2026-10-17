"""Small R helpers pillar uses: missing values, match.arg, and strrep."""

from __future__ import annotations

from typing import Any

NA = object()


def is_na(value: Any) -> bool:
    return value is None or value is NA


def paste_atom(value: Any) -> str:
    """paste0 of one atom. A missing value becomes the letters NA."""

    if is_na(value):
        return "NA"
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, str):
        return value
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        from glue._text import r_character_double

        return r_character_double(value)
    return str(value)


def match_arg(arg: Any, choices: tuple[str, ...]) -> str:
    """match.arg. A unique prefix selects the choice."""

    if not isinstance(arg, str) or arg == "":
        raise ValueError(
            "'arg' must be of length 1"
        )
    exact = [choice for choice in choices if choice == arg]
    if exact:
        return exact[0]
    hits = [choice for choice in choices if choice.startswith(arg)]
    if len(hits) == 1:
        return hits[0]
    if not hits:
        listed = ", ".join(choices)
        raise ValueError(f"'{arg}' should be one of {listed}")
    listed = ", ".join(hits)
    raise ValueError(f"'{arg}' matches more than one of {listed}")


def strrep(space: str, times: int) -> str:
    if times <= 0:
        return ""
    return space * times
