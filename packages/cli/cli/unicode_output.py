"""UTF-8 output detection from cli's is_utf8_output."""

from __future__ import annotations

import locale
import os

from cli._options import get_option


def _locale_is_utf8() -> bool:
    encoding = locale.getpreferredencoding(False) or ""
    folded = encoding.lower().replace("-", "")
    if "utf8" in folded:
        return True
    lang = os.environ.get("LC_ALL") or os.environ.get("LC_CTYPE") or os.environ.get("LANG") or ""
    return "utf8" in lang.lower().replace("-", "") or "utf-8" in lang.lower()


def is_latex_output() -> bool:
    """cli asks knitr, and only when that namespace is loaded. It is not."""

    return False


def is_utf8_output() -> bool:
    """Whether cli emits UTF-8 characters.

    ``cli.unicode`` TRUE or FALSE wins. Otherwise the locale is UTF-8 and
    output is not LaTeX.
    """

    opt = get_option("cli.unicode", None)
    if opt is not None:
        return opt is True
    return _locale_is_utf8() and not is_latex_output()
