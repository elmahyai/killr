"""xtableMatharray from xtable 1.8-8."""

from __future__ import annotations

from xtable.caption_replacement import Xtable
from xtable.xtable_main import xtable_matrix


def xtable_matharray(
    x: list[list[object]],
    caption=None,
    label=None,
    align=None,
    digits=None,
    display=None,
    auto: bool = False,
    **_kwargs: object,
) -> Xtable:
    xtbl = xtable_matrix(
        x,
        caption=caption,
        label=label,
        align=align,
        digits=digits,
        display=display,
        auto=auto,
    )
    xtbl.classes = ("xtableMatharray", "xtable", "data.frame")
    return xtbl
