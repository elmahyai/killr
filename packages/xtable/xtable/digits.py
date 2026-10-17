"""digits from xtable 1.8-8 (``digits.xtable``).

Retrieves the ``digits`` attribute from an ``xtable`` object.
"""

from __future__ import annotations

from xtable.caption_replacement import Xtable


def digits_attr(x: Xtable) -> object:
    """Same as R ``attr(x, \"digits\", exact = TRUE)`` for checks."""
    if "digits" not in x.attrs:
        return None
    return x.attrs["digits"]


def digits(x: object, *_args: object, **_kwargs: object) -> object:
    if isinstance(x, Xtable):
        return digits_attr(x)
    kind = type(x).__name__
    raise ValueError(
        f"no applicable method for 'digits' applied to an object of class \"{kind}\""
    )
