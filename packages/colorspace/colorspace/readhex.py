"""Read hexadecimal colors from a file (colorspace 2.1-4)."""

from __future__ import annotations

import re
from pathlib import Path

from colorspace.hex2rgb import hex2RGB
from colorspace.readrgb import _as_class


def _scan_hex_file(path: str | Path) -> list[str]:
    text = Path(path).read_text(encoding="utf-8")
    return re.findall(r"\S+", text)


def readhex(file: str = "", class_: str = "RGB"):
    """Read ``#RRGGBB`` strings from ``file`` and return a color object."""
    if file == "":
        import sys

        text = sys.stdin.read()
        tokens = re.findall(r"\S+", text)
    else:
        tokens = _scan_hex_file(file)
    if not tokens:
        color = hex2RGB([])
        return _as_class(color, class_)
    color = hex2RGB(tokens)
    return _as_class(color, class_)
