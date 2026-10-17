"""Binary representation from bits.R."""

from __future__ import annotations

import math

import numpy as np

from pracma._util import PracmaError
from pracma.elementary import nextpow2
from pracma.util_support import is_numeric, require, whole_number


def bits(x, k=54, pos_sign=False, break0=False):
    require(is_numeric(x), "is.numeric(x) is not TRUE")
    require(np.asarray(x).size == 1, "length(x) == 1 is not TRUE")
    if not whole_number(k) or float(k) <= 0:
        raise PracmaError("Argument 'k' must be a (positive) integer.")
    digits = int(float(k))
    number = float(np.asarray(x, dtype=float).reshape(-1)[0])
    if number >= 0:
        text = "+" if pos_sign else ""
    else:
        text = "-"
        number = -number
    whole = float(math.trunc(number))
    fraction = number - whole
    if whole >= 1:
        power = int(np.asarray(nextpow2(whole), dtype=float).reshape(-1)[0])
        if 2.0**power > whole:
            power -= 1
        for exponent in range(power, -1, -1):
            step = 2.0**exponent
            if whole >= step:
                text += "1"
                whole -= step
            else:
                text += "0"
    else:
        text += "0"
    if fraction > 0:
        text += "."
        for exponent in range(1, digits + 1):
            step = 1.0 / 2.0**exponent
            if fraction >= step:
                text += "1"
                fraction -= step
                if break0 and fraction == 0:
                    break
            else:
                text += "0"
    return text
