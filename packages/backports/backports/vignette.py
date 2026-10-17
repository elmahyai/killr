"""vignetteInfo, ported from the tools namespace rather than imported at runtime."""

from __future__ import annotations

import os
import re

from backports._values import trimws

__all__ = ["vignetteInfo"]

_SPACE = r"[ \t\n\r\f\v]"


def vignetteInfo(file):
    with open(file, encoding="utf-8", errors="replace") as handle:
        lines = handle.read().splitlines()
    title = _metadata(lines, "IndexEntry")
    title = title[0] if title else ""
    depends = _metadata(lines, "Depends")
    if depends:
        depends = re.split(r", *", depends[0])
    keywords = _metadata(lines, "Keywords")
    if keywords:
        keywords = re.split(r", *", keywords[0])
    else:
        keywords = _metadata(lines, "Keyword")
    engine = _engine(lines)
    return {
        "file": os.path.basename(file),
        "title": title,
        "depends": depends,
        "keywords": keywords,
        "engine": engine,
    }


def _metadata(lines, tag):
    pattern = re.compile(
        rf"{_SPACE}*%+{_SPACE}*\\Vignette{tag}\{{([^}}]*(\{{[^}}]*\}})*[^}}]*)\}}.*"
    )
    found = []
    for line in lines:
        match = pattern.search(line)
        if match:
            found.append(match.group(1))
    cleaned = trimws(found) if found else []
    if isinstance(cleaned, str):
        return [cleaned]
    return list(cleaned)


def _engine(lines):
    found = _metadata(lines, "Engine")
    if found:
        return found[0]
    return "utils::Sweave"
