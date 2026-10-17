"""display from xtable 1.8-8 (``display.xtable``).

Retrieves the ``display`` attribute from an ``xtable`` object.
"""

from __future__ import annotations

from xtable.caption_replacement import Xtable


def display_attr(x: Xtable) -> object:
    """Same as R ``attr(x, \"display\", exact = TRUE)`` for checks."""
    if "display" not in x.attrs:
        return None
    return x.attrs["display"]


def display(x: object, *_args: object, **_kwargs: object) -> object:
    if isinstance(x, Xtable):
        return display_attr(x)
    kind = type(x).__name__
    raise ValueError(
        f"no applicable method for 'display' applied to an object of class \"{kind}\""
    )
