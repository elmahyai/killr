"""Rd2txt defaults, the bibstyle name, and print-via-format."""

from __future__ import annotations

import sys
from typing import Any

_RD2TXT = {
    "width": 80,
    "minIndent": 10,
    "extraIndent": 4,
    "sectionIndent": 5,
    "sectionExtra": 2,
    "itemBullet": "\u2022 ",
    "showURLs": False,
    "code_quote": True,
    "underline_titles": True,
}


def enum_format(n: int) -> str:
    """The default Rd2txt enumerator, sprintf('%d. ', n)."""
    return f"{n}. "


def rd2txt_options() -> dict[str, Any]:
    """The current Rd2txt rendering options."""
    options = dict(_RD2TXT)
    options["enumFormat"] = enum_format
    return options


def get_bibstyle(all_styles: bool = False) -> str | list[str]:
    """The default bibstyle name, or every registered name."""
    from tools.bibstyle import get_bibstyle as _get_bibstyle

    return _get_bibstyle(all_styles)


def print_via_format(x: Any) -> Any:
    """Write format(x) and return x, as .print.via.format does."""
    if isinstance(x, str):
        print(x)
    elif isinstance(x, (list, tuple)):
        for item in x:
            print(item)
    else:
        print(x)
    return x
