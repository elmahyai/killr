"""Column names the way tibble 3.3.1 repairs them for readxl."""

from __future__ import annotations

import re
from collections import Counter


_DOTS = re.compile(r"^(.*)\.{3}[0-9]+$")
_INVALID = re.compile(r"[^A-Za-z0-9._]")


def _strip(name: str) -> str:
    matched = _DOTS.match(name)
    if matched is None:
        return name
    return matched.group(1)


def _syntactic(name: str) -> str:
    name = _INVALID.sub(".", name)
    if name == "...":
        return ""
    while name and (name[0].isdigit() or (name[0] == "." and len(name) > 1 and name[1].isdigit()) or name[0] not in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz."):
        name = "." + name
    return name


def repair(names: list[str], how="unique") -> list[str]:
    """``unique``, ``universal``, ``minimal``, or ``check_unique``."""

    cleaned = ["" if name is None else str(name) for name in names]
    if how == "minimal":
        return cleaned
    stripped = [_strip(name) for name in cleaned]
    if how == "universal":
        stripped = [_syntactic(name) for name in stripped]
    elif how != "unique" and how != "check_unique":
        raise ValueError('.name_repair must be "unique", "universal", "minimal", or "check_unique"')
    counts = Counter(stripped)
    if how == "check_unique":
        if any(name == "" or counts[name] > 1 for name in stripped):
            raise ValueError("column names must be unique and non-empty")
        return stripped
    out = []
    for index, name in enumerate(stripped, start=1):
        if name == "" or counts[name] > 1:
            out.append(f"{name}...{index}")
        else:
            out.append(name)
    return out
