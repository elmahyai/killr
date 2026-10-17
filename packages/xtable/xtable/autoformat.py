"""autoformat from xtable 1.8-8."""

from __future__ import annotations

from xtable.align_replacement import align_replacement
from xtable.caption_replacement import Xtable
from xtable.digits_replacement import digits_replacement
from xtable.display_replacement import display_replacement
from xtable.xalign import xalign
from xtable.xdigits import xdigits
from xtable.xdisplay import xdisplay

_DEFAULT_ZAP = 7


def autoformat(xtab: Xtable, zap: int | float | None = None) -> Xtable:
    if zap is None:
        zap = _DEFAULT_ZAP
    xtab = align_replacement(xtab, xalign(xtab))
    xtab = digits_replacement(xtab, xdigits(xtab, zap=zap))
    xtab = display_replacement(xtab, xdisplay(xtab))
    return xtab
