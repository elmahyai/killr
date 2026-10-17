"""Whether the output connection can show ANSI styles or UTF-8."""

from __future__ import annotations

import locale
import os
import sys


def output_ansi() -> bool:
    """True when stdout is a terminal, or RStudio has enabled console color."""

    if sys.stdout.isatty():
        return os.environ.get("R_GUI") != "Rgui"
    color = os.environ.get("RSTUDIO_CONSOLE_COLOR", "")
    try:
        float(color)
    except ValueError:
        return False
    return color != "" and sys.stdout.fileno() == 1


def output_utf8() -> bool:
    """True when the character locale is UTF-8. The C locale is ASCII only."""

    name = locale.setlocale(locale.LC_CTYPE, None)
    if name == "C":
        return False
    if "UTF-8" in name.upper() or "UTF8" in name.upper():
        return True
    if sys.platform == "win32":
        return True
    return False
