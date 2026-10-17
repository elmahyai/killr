"""vctrs unique name repair, the repair readr 2 applies to column names."""

from __future__ import annotations

import keyword
import warnings

_R_RESERVED = {
    "if", "else", "repeat", "while", "function", "for", "in", "next", "break",
    "TRUE", "FALSE", "NULL", "Inf", "NaN", "NA", "NA_integer_", "NA_real_",
    "NA_complex_", "NA_character_", "...", "..1", "..2", "..3",
}


def suffix_pos(name: str) -> int:
    """Index where a trailing ``...digits`` suffix starts, or -1."""
    suffix_end = None
    in_dots = 0
    in_digits = False
    index = len(name) - 1
    while index >= 0:
        character = name[index]
        if in_digits:
            if character == ".":
                in_digits = False
                in_dots = 1
                index -= 1
                continue
            if character.isdigit():
                index -= 1
                continue
            break
        if in_dots == 0:
            if character.isdigit():
                in_digits = True
                index -= 1
                continue
            break
        if in_dots in (1, 2):
            if character == ".":
                in_dots += 1
                index -= 1
                continue
            break
        if in_dots == 3:
            suffix_end = index + 1
            if character.isdigit():
                in_dots = 0
                in_digits = True
                index -= 1
                continue
            break
        break
    if suffix_end is None:
        return -1
    return suffix_end


def _is_dotdotint(name: str) -> bool:
    if len(name) < 3 or name[0] != "." or name[1] != ".":
        return False
    rest = name[3:] if len(name) > 2 and name[2] == "." else name[2:]
    if not rest:
        return False
    index = 0
    if rest[0] in "+-":
        index = 1
    if index >= len(rest) or not rest[index].isdigit():
        return False
    value = 0
    while index < len(rest) and rest[index].isdigit():
        value = value * 10 + int(rest[index])
        index += 1
    return value != 0


def _needs_suffix(name: str | None) -> bool:
    if name is None or name in ("", "..."):
        return True
    return _is_dotdotint(name)


def _duplicated(names: list[str]) -> list[bool]:
    counts: dict[str, int] = {}
    for name in names:
        counts[name] = counts.get(name, 0) + 1
    return [counts[name] > 1 for name in names]


def _describe(old: list[str], new: list[str]) -> None:
    lines = ["New names:"]
    for before, after in zip(old, new):
        if before != after:
            lines.append(f"• `{before}` -> `{after}`")
    if len(lines) > 1:
        warnings.warn("\n".join(lines), stacklevel=4)


def repair_unique(names: list[str], quiet: bool = False) -> list[str]:
    """Suffix every duplicate, blank, and ``..n`` name with its position."""
    original = [("" if name is None else name) for name in names]
    if original and not any(_needs_suffix(name) for name in original) and not any(
        suffix_pos(name) >= 0 for name in original
    ) and len(set(original)) == len(original):
        return list(original)
    stripped: list[str] = []
    for name in original:
        if _needs_suffix(name):
            stripped.append("")
            continue
        position = suffix_pos(name)
        stripped.append(name[:position] if position >= 0 else name)
    marked = _duplicated(stripped)
    repaired = []
    for index, name in enumerate(stripped):
        if name != "" and not marked[index]:
            repaired.append(name)
        else:
            repaired.append(f"{name}...{index + 1}")
    if not quiet and repaired != original:
        _describe(original, repaired)
    return repaired


def _make_syntactic(name: str) -> str:
    if name is None:
        name = ""
    cleaned = []
    for character in name:
        if character.isalnum() or character in "._":
            cleaned.append(character)
        else:
            cleaned.append(".")
    text = "".join(cleaned)
    if not text or text[0].isdigit():
        text = "X" + text
    if text in _R_RESERVED or keyword.iskeyword(text):
        text = text + "."
    return text


def repair_names(names: list[str], repair: str | object = "unique") -> list[str]:
    """Apply a vctrs name-repair strategy."""
    values = [("" if name is None else str(name)) for name in names]
    if callable(repair):
        result = repair(values)
        return ["" if name is None else str(name) for name in result]
    if repair in ("minimal",):
        return values
    if repair in ("unique", "unique_quiet"):
        return repair_unique(values, quiet=repair == "unique_quiet")
    if repair in ("universal", "universal_quiet"):
        syntactic = [_make_syntactic(name) for name in values]
        return repair_unique(syntactic, quiet=str(repair).endswith("quiet"))
    if repair == "check_unique":
        if any(name == "" for name in values) or len(set(values)) != len(values):
            raise ValueError("Column names must be unique and non-empty.")
        return values
    raise ValueError(
        "name_repair must be minimal, unique, universal, check_unique, "
        "unique_quiet, universal_quiet, or a function."
    )
