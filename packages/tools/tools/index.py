"""read.00Index from tools 4.5.0."""

from __future__ import annotations

import re


def read_00index(path: str) -> list[tuple[str, str]]:
    """Item and description rows from a package 00Index file."""
    with open(path, encoding="utf-8") as handle:
        text = handle.read()
    if text.endswith("\n"):
        # readLines drops the trailing newline, and paste collapses with newline.
        text = text[:-1]
    rows: list[tuple[str, str]] = []
    for chunk in re.split(r"\n[ \t\n]*\n", text):
        if not re.search(r"(   |\t)", chunk):
            continue
        chunk = re.sub(r"\n[ \t]+", "\t", chunk)
        for line in chunk.split("\n"):
            parts = re.split(r"[ \t]", line)
            if not parts or parts[0] == "":
                continue
            description = " ".join(part for part in parts[1:] if part)
            rows.append((parts[0], description))
    return rows
