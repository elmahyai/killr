"""label<- from xtable 1.8-8 (``label<-.xtable``).

Sets the ``label`` attribute on an ``xtable`` object. The replacement
value must have R ``length`` 1 or be empty.
"""

from __future__ import annotations

from xtable.caption_replacement import Xtable, _r_length, _store_value


def label_replacement(x: object, value: object) -> Xtable:
    if not isinstance(x, Xtable):
        raise ValueError(
            f"no applicable method for 'label<-' applied to an object of class "
            f'"{type(x).__name__}"'
        )
    if _r_length(value) > 1:
        raise ValueError('"label" must have length 1')
    x.attrs["label"] = _store_value(value)
    return x
