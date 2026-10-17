"""Write a value to the system clipboard."""

from __future__ import annotations

import platform
from typing import Any

from clipr._clipboard import require_access, write_clipboard
from clipr._render import match_object_type, render_object


def write_clip(
    content: Any,
    object_type: str = "auto",
    breaks: str | None = None,
    eos: str | None = None,
    return_new: bool = False,
    allow_non_interactive: Any = None,
    **options: Any,
) -> Any:
    """Write content to the clipboard.

    A dict of equal-length columns, a Frame, a Matrix, or a rectangular list
    of rows is written as a table, in the same shape as R's write.table.
    Anything else is coerced to text and joined with breaks. return_new
    returns the rendered text instead of the original object.
    """

    require_access(allow_non_interactive)
    chosen = match_object_type(object_type)
    if breaks is None:
        breaks = "\r\n" if platform.system() == "Windows" else "\n"
    dots = dict(options)
    if dots.get("sep") is None:
        dots["sep"] = "\t"
    rendered = render_object(content, chosen, breaks, dots)
    payload = rendered.encode("utf-8")
    if eos is not None:
        payload += str(eos).encode("utf-8") + b"\0"
    write_clipboard(payload)
    if return_new:
        return rendered
    return content
