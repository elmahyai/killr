"""display<- from xtable 1.8-8."""

from __future__ import annotations

from xtable.caption_replacement import Xtable

_DISPLAY_ALLOWED = frozenset({"d", "f", "e", "E", "g", "G", "fg", "s"})


def display_replacement(x: object, value: object) -> Xtable:
    if not isinstance(x, Xtable):
        raise ValueError(
            f"no applicable method for 'display<-' applied to an object of class "
            f'"{type(x).__name__}"'
        )
    if isinstance(value, str):
        vec = [value]
    else:
        vec = list(value)
    need = x.ncol + 1
    if len(vec) != need:
        raise ValueError(
            f'"display" must have length equal to {need} ( ncol(x) + 1 )'
        )
    if not all(v in _DISPLAY_ALLOWED for v in vec):
        raise ValueError(
            '"display" must be in {"d","f","e","E","g","G", "fg", "s"}'
        )
    x.attrs["display"] = vec
    return x
