"""caption from xtable 1.8-8 (``caption.xtable``).

Retrieves the ``caption`` attribute from an ``xtable`` object.
"""

from __future__ import annotations

from xtable.caption_replacement import Xtable, caption_attr


def caption(x: object, *_args: object, **_kwargs: object) -> object:
    if isinstance(x, Xtable):
        return caption_attr(x)
    kind = type(x).__name__
    raise ValueError(
        f"no applicable method for 'caption' applied to an object of class \"{kind}\""
    )
