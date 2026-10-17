"""R helpers shared by the prettyunits translation.

`r_round` follows R 4.5 `fround` (`src/nmath/fround.c`).
"""

import math
from fractions import Fraction

DBL_DIG = 15
DBL_MAX_10_EXP = 308
MAX_DIGITS = DBL_MAX_10_EXP + DBL_DIG
LOG10_2 = math.log10(2.0)
DOUBLE_EPS = 2.220446049250313e-16


def _logb(x):
    """C `logb` for a positive finite value. `frexp` uses [0.5, 1)."""
    _mantissa, exponent = math.frexp(x)
    return float(exponent - 1)


def r_round(x, digits=0):
    """R `round(x, digits)` for one real value. None stays None."""
    if x is None:
        return None
    x = float(x)
    digits = float(digits)
    if math.isnan(x) or math.isnan(digits):
        return x + digits
    if math.isinf(x):
        return x
    if digits > MAX_DIGITS or x == 0.0:
        return math.copysign(0.0, x) if x == 0.0 else x
    if digits < -DBL_MAX_10_EXP:
        return 0.0
    if digits == 0.0:
        return _nearbyint(x)

    dig = int(math.floor(digits + 0.5))
    sign = -1.0 if x < 0.0 else 1.0
    magnitude = abs(x)
    log10x = LOG10_2 * (0.5 + _logb(magnitude))
    if log10x + dig > DBL_DIG:
        return sign * magnitude
    if dig <= DBL_MAX_10_EXP:
        pow10 = r_pow_di(10.0, dig)
        scaled = magnitude * pow10
        down_scaled = math.floor(scaled)
        down = down_scaled / pow10
        up = math.ceil(scaled) / pow10
    else:
        extra = dig - DBL_MAX_10_EXP
        pow10 = r_pow_di(10.0, DBL_MAX_10_EXP)
        finer = r_pow_di(10.0, extra)
        scaled = (magnitude * pow10) * finer
        down_scaled = math.floor(scaled)
        down = down_scaled / pow10 / finer
        up = math.ceil(scaled) / pow10 / finer
    distance_up = up - magnitude
    distance_down = magnitude - down
    odd = math.fmod(down_scaled, 2.0) == 1.0
    choose_up = distance_up < distance_down or (odd and distance_up == distance_down)
    return sign * (up if choose_up else down)


def r_pow_di(x, n):
    """R `R_pow_di(x, n)`: repeated squaring, and 1 / x^|n| for a negative n.

    The result is not always the correctly rounded power, so `r_round` uses it
    instead of `10.0 ** n`.
    """
    if math.isnan(x):
        return x
    if n == 0:
        return 1.0
    if math.isinf(x):
        return x ** n
    is_negative = n < 0
    n = -n if is_negative else n
    power = 1.0
    while True:
        if n & 1:
            power *= x
        n >>= 1
        if n:
            x *= x
        else:
            break
    return 1.0 / power if is_negative else power


def _extended(value):
    """Round an exact Fraction to a 64-bit significand, as C `long double` does on x86."""
    if value == 0:
        return value
    magnitude = abs(value)
    exponent = magnitude.numerator.bit_length() - magnitude.denominator.bit_length()
    if magnitude < Fraction(2) ** exponent:
        exponent -= 1
    scale = Fraction(2) ** (63 - exponent)
    scaled = magnitude * scale
    rounded = round(scaled)  # Fraction rounds half to even.
    result = Fraction(rounded) / scale
    return -result if value < 0 else result


def r_mod(x1, x2):
    """R `x1 %% x2` for doubles (arithmetic.c `myfmod`).

    R takes the remainder in long double, then subtracts once more. For
    example `-8.9e-31 %% 24` is `0`, not `24`, because the long double sum
    is exactly 24.
    """
    x1 = float(x1)
    x2 = float(x2)
    if math.isnan(x1) or math.isnan(x2):
        return x1 + x2
    if x2 == 0.0 or math.isinf(x1):
        return math.nan
    quotient = x1 / x2
    floor_q = math.floor(quotient)
    divisor = Fraction(x2)
    tmp = _extended(Fraction(x1) - floor_q * divisor)
    step = math.floor(_extended(tmp / divisor))
    return float(_extended(tmp - step * divisor))


def _nearbyint(x):
    if math.isnan(x) or math.isinf(x) or x == 0.0:
        return math.copysign(0.0, x) if x == 0.0 else x
    magnitude = abs(x)
    down = math.floor(magnitude)
    fraction = magnitude - down
    if fraction > 0.5:
        rounded = down + 1.0
    elif fraction < 0.5:
        rounded = down
    elif math.fmod(down, 2.0) == 0.0:
        rounded = down
    else:
        rounded = down + 1.0
    if rounded == 0.0:
        return math.copysign(0.0, x)
    return math.copysign(rounded, x)


def r_as_integer(x):
    """R `as.integer` for one real. Out of range and non-finite become None."""
    if x is None:
        return None
    x = float(x)
    if math.isnan(x) or math.isinf(x):
        return None
    if x > 2147483647 or x < -2147483647:
        return None
    return float(math.trunc(x))


def na_subscript_positions(mask):
    """Positions that R's `res[mask] <- a` and `res[!mask] <- b` assign to.

    `mask` holds True, False, or None (R's NA). An NA subscript skips its
    position, but R refuses the whole assignment when the value has more than
    one element and the subscript holds an NA.
    """
    true_at = [i for i, flag in enumerate(mask) if flag is True]
    false_at = [i for i, flag in enumerate(mask) if flag is False]
    missing = [i for i, flag in enumerate(mask) if flag is None]
    if missing and len(true_at) + len(missing) > 1:
        raise ValueError("NAs are not allowed in subscripted assignments")
    if missing and len(false_at) + len(missing) > 1:
        raise ValueError("NAs are not allowed in subscripted assignments")
    return true_at, false_at


def format_numeric(values):
    """R `format(x, scientific = FALSE)` for a vector, with 7 significant digits.

    R uses one number of decimals and one width for the whole vector. The
    decimals come from the element that needs the most, so a tiny value makes
    every element print that many zeros. NA, NaN, and Inf are right-justified
    to the same width.
    """
    rgt = 0
    left = 1
    for value in values:
        if _is_finite_number(value):
            neg = 1 if value < 0 else 0
            kp, nsig = _sig_exponent(value)
            left = max(left, neg + (kp + 1 if kp >= 0 else 1))
            rgt = max(rgt, nsig - kp - 1)
    width = left + (rgt + 1 if rgt > 0 else 0)
    tokens = []
    for value in values:
        if value is None:
            tokens.append("NA")
        elif math.isnan(value):
            tokens.append("NaN")
        elif math.isinf(value):
            tokens.append("Inf" if value > 0 else "-Inf")
        else:
            tokens.append(f"{value:.{max(rgt, 0)}f}")
    special = [token for value, token in zip(values, tokens) if not _is_finite_number(value)]
    width = max([width] + [len(token) for token in special])
    return [token.rjust(width) for token in tokens]


def _is_finite_number(value):
    return value is not None and not math.isnan(value) and not math.isinf(value)


def _sig_exponent(value):
    """Decimal exponent and count of significant digits, after 7-digit rounding."""
    if value == 0.0:
        return 0, 1
    mantissa, exponent_text = f"{abs(value):.6e}".split("e")
    digits = mantissa.replace(".", "").rstrip("0") or "0"
    return int(exponent_text), len(digits)


def justify_right(values):
    """R `format(x, justify = "right")` for character values."""
    if not values:
        return []
    width = max(len(value) for value in values)
    return [value.rjust(width) for value in values]


MAX_F_DIGITS = 324


def format_fixed(x, digits):
    """R `formatC(x, format = "f", digits = digits)` for one already-rounded value.

    formatC maps a negative `digits` to 6 and caps it at 324. A non-finite value
    is right-justified to `digits + 1` characters, so `Inf` with digits 5 is
    `"   Inf"`.
    """
    digits = int(digits)
    if digits < 0:
        digits = 6
    digits = min(digits, MAX_F_DIGITS)
    if x is None:
        return "NA".rjust(digits + 1)
    x = float(x)
    if math.isnan(x):
        return "NaN".rjust(digits + 1)
    if math.isinf(x):
        return ("Inf" if x > 0 else "-Inf").rjust(digits + 1)
    return f"{x:.{digits}f}"


def format_integer(x):
    """R `formatC(x, format = "d")` for one integer."""
    return str(int(x))


def match_arg(arg, choices):
    """R `match.arg` with a unique prefix. A full copy of `choices` selects the first."""
    if arg is None:
        return choices[0]
    if isinstance(arg, (list, tuple)):
        if list(arg) == list(choices):
            return choices[0]
        raise ValueError("arg must be of length 1")
    if not isinstance(arg, str):
        raise ValueError("arg must be NULL or a character vector")
    if arg in choices:
        return arg
    matches = [choice for choice in choices if choice.startswith(arg)]
    if len(matches) == 1:
        return matches[0]
    if not matches:
        quoted = ", ".join(repr(choice) for choice in choices)
        raise ValueError(f"arg should be one of {quoted}")
    raise ValueError("there is more than one match in match.arg")
