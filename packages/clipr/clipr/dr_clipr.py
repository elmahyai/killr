"""Print whether clipr can use the system clipboard."""

from __future__ import annotations

from typing import Any

from clipr._clipboard import AVAILABLE_MESSAGE, message
from clipr.clipr_available import _handler, _results_ok


def dr_clipr(**options: Any) -> str:
    """Print the clipboard status and return the same text.

    When the clipboard is usable the text says clipr has read/write access.
    Otherwise the text is the error from the write attempt.
    """

    result = _handler(**options)
    if _results_ok(result):
        text = AVAILABLE_MESSAGE
    else:
        error = result.get("write_error")
        text = str(error) if error is not None else ""
    message(text)
    return text
