"""label from xtable 1.8-8 (``label.xtable``).

Retrieves the ``label`` attribute from an ``xtable`` object.
"""

from __future__ import annotations

from xtable.caption_replacement import Xtable


def label_attr(x: Xtable) -> object:
    """Same as R ``attr(x, \"label\", exact = TRUE)`` for checks."""
    if "label" not in x.attrs:
        return None
    return x.attrs["label"]


def label(x: object, *_args: object, **_kwargs: object) -> object:
    if isinstance(x, Xtable):
        return label_attr(x)
    kind = type(x).__name__
    raise ValueError(
        f"no applicable method for 'label' applied to an object of class \"{kind}\""
    )
