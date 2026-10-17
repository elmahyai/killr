"""Debug text formatting (gtools 3.9.5 ``scat``)."""

from __future__ import annotations

import math
from collections.abc import Sequence
from typing import Any

import numpy as np

_debug_option: bool | None = None
_MISSING = object()


class _RNaType:
    __slots__ = ()


R_NA = _RNaType()


def set_debug(value: bool | None) -> None:
    """Set the stand-in for ``options(DEBUG=...)`` (``None`` clears the option)."""
    global _debug_option
    _debug_option = value


def get_debug() -> bool | None:
    """Return the current DEBUG option value."""
    return _debug_option


def _debug_active(flag: Any) -> bool:
    if flag is None:
        return False
    if flag is False:
        return False
    if flag is True:
        return True
    return bool(flag)


def _expand_argument(arg: Any) -> list[Any]:
    if isinstance(arg, np.ndarray):
        if arg.ndim == 0:
            return [arg.item()]
        return list(arg.ravel(order="C"))
    if isinstance(arg, (str, bytes)):
        return [arg.decode("utf-8") if isinstance(arg, bytes) else arg]
    if isinstance(arg, Sequence):
        return list(arg)
    return [arg]


def _encode_scalar(item: Any) -> str | None:
    if item is None:
        return ""
    if item is R_NA:
        return "NA"
    if isinstance(item, bool):
        return "TRUE" if item else "FALSE"
    if isinstance(item, (np.bool_,)):
        return "TRUE" if bool(item) else "FALSE"
    if isinstance(item, (int, np.integer)) and not isinstance(item, (bool, np.bool_)):
        return str(int(item))
    if isinstance(item, (float, np.floating)):
        value = float(item)
        if math.isnan(value):
            return "NaN"
        if math.isinf(value):
            return "Inf" if value > 0 else "-Inf"
        return None
    if isinstance(item, complex):
        real = _cat_text([item.real], sep=" ")
        imag = _cat_text([item.imag], sep=" ")
        if item.imag >= 0:
            return f"{real}+{imag}i"
        return f"{real}{imag}i"
    if isinstance(item, (str, np.str_)):
        return str(item)
    return str(item)


def _cat_text(parts: list[Any], sep: str) -> str:
    encoded: list[str] = []
    pending_floats: list[float] = []
    pending_slots: list[int] = []

    def flush_floats() -> None:
        nonlocal pending_floats, pending_slots
        if not pending_floats:
            return
        rendered = _format_real(pending_floats)
        for slot, text in zip(pending_slots, rendered):
            encoded[slot] = text
        pending_floats = []
        pending_slots = []

    for item in parts:
        encoded.append("")
        slot = len(encoded) - 1
        scalar = _encode_scalar(item)
        if scalar is not None:
            encoded[slot] = scalar
            continue
        pending_slots.append(slot)
        pending_floats.append(float(item))
    flush_floats()
    return sep.join(encoded)


def _cat_argument(arg: Any, sep: str) -> str:
    return _cat_text(_expand_argument(arg), sep)


def scat(*args: Any, sep: str = " ", debug: Any = _MISSING) -> str:
    """Return the stderr debug line R ``scat`` would write when DEBUG is enabled."""
    flag = _debug_option if debug is _MISSING else debug
    if not _debug_active(flag):
        return ""
    body = sep.join(_cat_argument(arg, sep) for arg in args)
    return f"### {body} ###\n"


def _scientific(value: float, digits: int):
    negative = value < 0
    magnitude = abs(value)
    if magnitude == 0.0:
        return int(negative), 0, 1, False
    power = math.floor(math.log10(magnitude))
    scaled = magnitude / 10.0**power
    rounded = round(scaled, digits - 1)
    widens = False
    if rounded >= 10.0:
        rounded = 1.0
        power += 1
        widens = True
    text = f"{rounded:.{digits - 1}f}".replace(".", "").rstrip("0")
    significant = max(len(text), 1)
    return int(negative), power, significant, widens


def _format_real(values: list[float], digits: int = 7) -> list[str]:
    numbers = [float(value) for value in values]
    neg = 0
    mnl = 10**9
    mxl = rgt = mxsl = mxns = -(10**9)
    any_finite = False
    naflag = False
    nanflag = False
    for value in numbers:
        if not math.isfinite(value):
            if math.isnan(value):
                naflag = True
            continue
        any_finite = True
        neg_i, power, significant, widens = _scientific(value, digits)
        left = power + 1
        if widens:
            left -= 1
        sleft = neg_i + (1 if left <= 0 else left)
        right = significant - left
        if neg_i:
            neg = 1
        rgt = max(rgt, right)
        mxl = max(mxl, left)
        mnl = min(mnl, left)
        mxsl = max(mxsl, sleft)
        mxns = max(mxns, significant)
    if not any_finite:
        width = 2
        return ["NA".rjust(width) if math.isnan(value) else "Inf" for value in numbers]
    if digits == 0:
        rgt = 0
    if mxl < 0:
        mxsl = 1 + neg
    if rgt < 0:
        rgt = 0
    width_fixed = mxsl + rgt + (1 if rgt != 0 else 0)
    exponent_digits = 2 if (mxl > 100 or mnl <= -99) else 1
    decimals = mxns - 1
    width_scientific = neg + (1 if decimals > 0 else 0) + decimals + 4 + exponent_digits
    if width_fixed <= width_scientific:
        width = width_fixed
        places = rgt
        scientific = False
    else:
        width = width_scientific
        places = decimals
        scientific = True
    if naflag and width < 2:
        width = 2
    if nanflag and width < 3:
        width = 3
    rendered = []
    for value in numbers:
        if math.isnan(value):
            rendered.append("NA".rjust(width))
        elif scientific:
            rendered.append(f"{value:.{places}e}".rjust(width))
        else:
            rendered.append(f"{value:.{places}f}".rjust(width))
    return rendered
