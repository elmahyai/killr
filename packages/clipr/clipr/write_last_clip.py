"""Write one value to the clipboard.

R's write_last_clip writes .Last.value. Python has no last-expression
register, so the value is an argument.
"""

from __future__ import annotations

from typing import Any

from clipr.write_clip import write_clip


def write_last_clip(value: Any, **options: Any) -> Any:
    """Write value to the clipboard.

    This is write_clip(value). Pass the object that R would have stored in
    .Last.value.
    """

    return write_clip(value, **options)
