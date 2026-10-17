"""Report whether the system clipboard can be read and written."""

from __future__ import annotations

import os
import warnings
from typing import Any

from clipr._clipboard import CLIPR_ALLOW_BLOCK, as_logical, is_interactive
from clipr.read_clip import read_clip
from clipr.write_clip import write_clip


def clipr_available(**options: Any) -> bool:
    """Return True when the clipboard can be read and written.

    A non-interactive session returns False unless CLIPR_ALLOW is a true
    value. The check reads the clipboard and writes that same value back.
    """

    return _results_ok(_handler(**options))


def _handler(**options: Any) -> dict[str, Any]:
    if not is_interactive():
        allow = os.environ.get("CLIPR_ALLOW", "FALSE")
        if not as_logical(allow):
            return {"write_error": RuntimeError(CLIPR_ALLOW_BLOCK), "read_error": None}
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            read_value = read_clip(**options)
            read_error = None
        except Exception as exc:
            read_value = None
            read_error = exc
        try:
            write_clip(read_value, **options)
            write_error = None
        except Exception as exc:
            write_error = exc
    return {"read_error": read_error, "write_error": write_error}


def _results_ok(result: dict[str, Any]) -> bool:
    if result.get("write_error") is not None:
        return False
    if result.get("read_error") is not None:
        return False
    return True
