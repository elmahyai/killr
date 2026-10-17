"""align from xtable 1.8-8 (``align.xtable``).

Retrieves the ``align`` attribute from an ``xtable`` object.
"""

from __future__ import annotations

from xtable.align_replacement import align_attr
from xtable.caption_replacement import Xtable


def align(x: object, *_args: object, **_kwargs: object) -> object:
    if isinstance(x, Xtable):
        return align_attr(x)
    kind = type(x).__name__
    raise ValueError(
        f"no applicable method for 'align' applied to an object of class \"{kind}\""
    )
