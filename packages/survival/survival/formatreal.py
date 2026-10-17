"""R format() for a numeric vector, digits = 7."""

import math


def _scientific(value, digits):
    """Return neg, kpower, nsig, roundingwidens for one finite number."""
    negative = value < 0
    magnitude = abs(value)
    if magnitude == 0.0:
        return int(negative), 0, 1, False
    power = math.floor(math.log10(magnitude))
    scaled = magnitude / 10.0 ** power
    rounded = round(scaled, digits - 1)
    widens = False
    if rounded >= 10.0:
        rounded = 1.0
        power += 1
        widens = True
    text = f"{rounded:.{digits - 1}f}".replace(".", "").rstrip("0")
    significant = max(len(text), 1)
    return int(negative), power, significant, widens


def format_real(values, digits=7):
    """Format a numeric vector the way R's format() does at digits = 7."""
    numbers = [float(value) if value is not None else math.nan for value in values]
    neg = 0
    mnl = 10 ** 9
    mxl = rgt = mxsl = mxns = -(10 ** 9)
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
