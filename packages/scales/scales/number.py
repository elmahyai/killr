"""Low-level numeric formatter from scales 1.4.0 (R/label-number.R).

``number`` rounds to an accuracy, then prints with R's fixed ``format``
(``scientific = FALSE``), thousands marks, and sign styles. ``scale_cut``
is the named break vector that ``cut_short_scale`` and the other cut
helpers return; this module does not export those helpers.
"""

import math
import warnings
from decimal import ROUND_HALF_EVEN, Context, Decimal, localcontext

try:
    import numpy as _np
except ImportError:  # pragma: no cover
    _np = None

_EPS = sys_float_eps = float(math.ulp(1.0)) if hasattr(math, "ulp") else 2.220446049250313e-16


class _NAType:
    def __repr__(self):
        return "NA"


_NA = _NAType()


class CharacterVector(list):
    """Character results that still carry R names."""

    def __init__(self, values, names=None):
        super().__init__(values)
        self.names = names


def _is_na(value):
    return value is None or value is _NA


def _is_nan(value):
    return isinstance(value, float) and math.isnan(value)


def _unwrap(value):
    if _np is not None and isinstance(value, _np.generic):
        return value.item()
    return value


def _nearbyint(x):
    """R ``round`` / nearbyint for one finite quotient (digits = 0)."""
    if math.isnan(x) or math.isinf(x) or x == 0.0:
        if x == 0.0:
            return math.copysign(0.0, x)
        return x
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


def _recycle(values, size):
    if size == 0:
        return []
    if len(values) == size:
        return list(values)
    if len(values) == 0:
        raise ValueError("replacement has length zero")
    if len(values) != 1 and size % len(values) != 0:
        warnings.warn(
            "longer object length is not a multiple of shorter object length",
            RuntimeWarning,
            stacklevel=3,
        )
    return [values[i % len(values)] for i in range(size)]


def _as_text(value):
    if value is None or value is _NA:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, float):
        if math.isnan(value):
            return "NaN"
        if math.isinf(value):
            return "Inf" if value > 0 else "-Inf"
        if value.is_integer():
            return str(int(value))
    return str(value)


def _flatten(x):
    """Return ``(values, names)``. A scalar is a length-1 vector. ``[]`` is empty."""
    if x is None:
        return [_NA], None
    if isinstance(x, str):
        raise TypeError("non-numeric argument to binary operator")
    if isinstance(x, dict):
        return [_coerce_number(value) for value in x.values()], list(x.keys())
    if _np is not None and isinstance(x, _np.ndarray):
        if x.dtype.kind in ("U", "S", "O"):
            # Object arrays may still be numeric. Fall through elementwise.
            raw = list(_np.asarray(x).ravel(order="F"))
            if raw and all(isinstance(_unwrap(value), str) for value in raw):
                raise TypeError("non-numeric argument to binary operator")
            return [_coerce_number(value) for value in raw], None
        return [_coerce_number(value) for value in _np.asarray(x).ravel(order="F")], None
    if isinstance(x, (list, tuple)):
        return [_coerce_number(value) for value in x], None
    return [_coerce_number(x)], None


def _coerce_number(value):
    value = _unwrap(value)
    if value is None or value is _NA:
        return _NA
    if isinstance(value, bool):
        raise TypeError(
            "no applicable method for 'round_any' applied to an object of class \"logical\""
        )
    if isinstance(value, str):
        raise TypeError("non-numeric argument to binary operator")
    if isinstance(value, int):
        return float(value)
    if isinstance(value, float):
        return value
    raise TypeError("non-numeric argument to binary operator")


def _floor_log10(value):
    """``floor(log10(value))`` for a positive finite double, matching libm on powers of ten."""
    logged = math.log10(value)
    nearest = round(logged)
    if abs(logged - nearest) < 1e-10:
        logged = float(nearest)
    return int(math.floor(logged))


def _nsmall_one(accuracy):
    if accuracy is _NA or _is_nan(accuracy):
        raise ValueError("invalid 'nsmall' argument")
    accuracy = float(accuracy)
    if accuracy < 0:
        warnings.warn("NaNs produced", RuntimeWarning, stacklevel=4)
        raise ValueError("invalid 'nsmall' argument")
    if accuracy == 0:
        logged = float("-inf")
    else:
        logged = math.log10(accuracy)
        nearest = round(logged)
        if abs(logged - nearest) < 1e-10:
            logged = float(nearest)
    small = -math.floor(logged)
    if math.isnan(small):
        raise ValueError("invalid 'nsmall' argument")
    if math.isinf(small):
        small = 20 if small > 0 else 0
    small = int(small)
    if small < 0:
        small = 0
    if small > 20:
        small = 20
    return small


def _precision(values):
    finite = []
    for value in values:
        if value is _NA or not isinstance(value, float) or not math.isfinite(value):
            continue
        if any(value == seen for seen in finite):
            continue
        finite.append(value)
    if len(finite) <= 1:
        return 1.0
    finite.sort()
    smallest = min(finite[i + 1] - finite[i] for i in range(len(finite) - 1))
    if smallest < math.sqrt(_EPS):
        return 1.0
    prec = 10.0 ** (_floor_log10(smallest) - 1)
    if all(_nearbyint(value / prec) % 10 == 0 for value in finite):
        prec *= 10.0
    return min(prec, 1.0)


def _round_any(value, accuracy):
    if value is _NA:
        return _NA
    if _is_nan(value) or _is_nan(accuracy):
        return float("nan")
    accuracy = float(accuracy)
    if accuracy == 0.0:
        if value == 0.0:
            return float("nan")
        return _nearbyint(value / accuracy) * accuracy
    return _nearbyint(value / accuracy) * accuracy


def _arg_match(value, choices, arg):
    if isinstance(value, (list, tuple)):
        raise ValueError(f"`{arg}` must be length 1")
    if not isinstance(value, str):
        raise ValueError(f"`{arg}` must be a string")
    if value in choices:
        return value
    prefixes = [choice for choice in choices if choice.startswith(value)]
    suggestion = ""
    if len(prefixes) == 1:
        suggestion = f'\nℹ Did you mean "{prefixes[0]}"?'
    else:
        # A unique closest choice, the way rlang suggests "plus" for "plu".
        ranked = sorted(
            choices,
            key=lambda choice: (_edit_distance(value, choice), choices.index(choice)),
        )
        if ranked and _edit_distance(value, ranked[0]) <= 2:
            suggestion = f'\nℹ Did you mean "{ranked[0]}"?'
    if len(choices) == 1:
        listed = f'"{choices[0]}"'
    else:
        listed = ", ".join(f'"{choice}"' for choice in choices[:-1]) + f', or "{choices[-1]}"'
    raise ValueError(f'`{arg}` must be one of {listed}, not "{value}".{suggestion}')


def _edit_distance(left, right):
    if left == right:
        return 0
    prev = list(range(len(right) + 1))
    for i, ch_left in enumerate(left, 1):
        cur = [i]
        for j, ch_right in enumerate(right, 1):
            cur.append(
                min(
                    prev[j] + 1,
                    cur[j - 1] + 1,
                    prev[j - 1] + (ch_left != ch_right),
                )
            )
        prev = cur
    return prev[-1]


def _fixed(magnitude, places):
    """Fixed decimal text of a non-negative finite magnitude, ``places`` digits."""
    places = int(places)
    if places < 0:
        places = 0
    if magnitude == 0.0:
        if places == 0:
            return "0"
        return "0." + ("0" * places)
    prec = max(80, places + 20)
    if magnitude >= 1:
        prec = max(prec, _floor_log10(magnitude) + places + 8)
    ctx = Context(prec=prec, rounding=ROUND_HALF_EVEN)
    with localcontext(ctx):
        dec = Decimal(magnitude)
        quant = Decimal(1).scaleb(-places)
        rounded = dec.quantize(quant)
        text = format(rounded, "f")
    if places == 0:
        if "." in text:
            text = text.split(".", 1)[0]
        return text
    if "." not in text:
        text = text + "." + ("0" * places)
    whole, frac = text.split(".", 1)
    if len(frac) < places:
        frac = frac + ("0" * (places - len(frac)))
    elif len(frac) > places:
        frac = frac[:places]
    return whole + "." + frac


def _kpower(magnitude):
    if magnitude == 0.0:
        return 0
    return _floor_log10(magnitude)


def _natural_parts(value, nsmall, digits):
    """Stripped fixed form and its decimal count. Non-finite values have count ``None``."""
    if value is _NA:
        return "NA", None
    if _is_nan(value):
        return "NaN", None
    if math.isinf(value):
        return ("Inf" if value > 0 else "-Inf"), None
    negative = value < 0.0
    magnitude = abs(value)
    if magnitude == 0.0:
        places = nsmall
    else:
        sig = digits - _kpower(magnitude) - 1
        if sig < 0:
            sig = 0
        places = max(nsmall, sig)
    text = _fixed(magnitude, places)
    if "." in text:
        whole, frac = text.split(".", 1)
        while len(frac) > nsmall and frac.endswith("0"):
            frac = frac[:-1]
    else:
        whole, frac = text, ""
    body = ("-" if negative else "") + whole
    return (body, frac), len(frac)


def _pad_decimals(parts, count, common, mark):
    body, frac = parts
    if common <= 0:
        return body
    if len(frac) < common:
        frac = frac + ("0" * (common - len(frac)))
    return body + mark + frac


def _insert_from_right(text, mark, interval):
    if not mark or interval < 1 or not text:
        return text
    rev = text[::-1]
    mark_rev = mark[::-1]
    out = []
    digits = 0
    for i, ch in enumerate(rev):
        out.append(ch)
        if ch.isdigit():
            digits += 1
            if digits == interval and i + 1 < len(rev) and rev[i + 1].isdigit():
                out.append(mark_rev)
                digits = 0
        else:
            digits = 0
    return "".join(out)[::-1]


def _insert_from_left(text, mark, interval):
    if not mark or interval < 1 or not text:
        return text
    out = []
    digits = 0
    for i, ch in enumerate(text):
        out.append(ch)
        if ch.isdigit():
            digits += 1
            if digits == interval and i + 1 < len(text) and text[i + 1].isdigit():
                out.append(mark)
                digits = 0
        else:
            digits = 0
    return "".join(out)


def _string_number(text, decimal_mark, big_mark):
    probe = text.strip()
    if big_mark:
        probe = probe.replace(big_mark, "")
    if decimal_mark and decimal_mark != ".":
        probe = probe.replace(decimal_mark, ".")
    try:
        return float(probe)
    except ValueError:
        return None


def _apply_zero_print(text, zero_print, decimal_mark, big_mark):
    if zero_print is None:
        return text
    if isinstance(zero_print, bool):
        zero_print = "0" if zero_print else " "
    if not isinstance(zero_print, str):
        raise ValueError("'zero.print' must be character, logical or NULL")
    numeric = _string_number(text, decimal_mark, big_mark)
    if numeric is None or numeric != 0.0 or math.isnan(numeric):
        return text
    ind0 = text.find("0")
    if ind0 < 0:
        return text
    ind0_r = ind0 + 1
    nz = len(zero_print)
    nc = len(text)
    i2 = min(nc, nz - 1 + ind0_r)
    i1 = max(1, i2 - nz + 1)
    chars = list(text)
    replacement = list(zero_print)
    # substr assignment writes min(len) chars and does not grow the string.
    span = i2 - i1 + 1
    for offset in range(min(span, len(replacement))):
        chars[i1 - 1 + offset] = replacement[offset]
    if nc > i2:
        for pos in range(i2, nc):
            chars[pos] = " "
    return "".join(chars)


def _pretty(
    original,
    big_mark,
    big_interval,
    small_mark,
    small_interval,
    decimal_mark,
    trim,
    zero_print,
    drop0trailing,
):
    if (
        big_mark == ""
        and small_mark == ""
        and zero_print is None
        and not drop0trailing
    ):
        return list(original)
    if big_mark == decimal_mark and big_mark != "":
        warnings.warn(
            f"'big.mark' and 'decimal.mark' are both '{big_mark}', which could be confusing",
            RuntimeWarning,
            stacklevel=4,
        )
    updated = []
    for text in original:
        if decimal_mark and decimal_mark in text:
            left, right = text.split(decimal_mark, 1)
        else:
            left, right = text, ""
        left = _insert_from_right(left, big_mark, big_interval)
        right = _insert_from_left(right, small_mark, small_interval)
        if drop0trailing and right:
            while right.endswith("0"):
                right = right[:-1]
        if right:
            merged = left + decimal_mark + right
        else:
            merged = left
        merged = _apply_zero_print(merged, zero_print, decimal_mark, big_mark)
        updated.append(merged)
    if trim:
        out = []
        for old, new in zip(original, updated):
            growth = len(new) - len(old)
            if growth > 0:
                drop = 0
                while drop < growth and drop < len(new) and new[drop] == " ":
                    drop += 1
                new = new[drop:]
            out.append(new)
        return out
    if any(len(new) > len(old) for old, new in zip(original, updated)):
        width = max(len(text) for text in updated)
        return [text.rjust(width) for text in updated]
    return updated


def _format_fixed(
    values,
    nsmall,
    digits,
    trim,
    width,
    decimal_mark,
    big_mark,
    big_interval,
    small_mark,
    small_interval,
    zero_print,
    drop0trailing,
):
    parts = []
    counts = []
    for value in values:
        part, count = _natural_parts(value, nsmall, digits)
        parts.append(part)
        counts.append(count)
    finite_counts = [count for count in counts if count is not None]
    common = max(finite_counts) if finite_counts else 0
    cores = []
    for part, count in zip(parts, counts):
        if count is None:
            cores.append(part if isinstance(part, str) else part)
        else:
            cores.append(_pad_decimals(part, count, common, decimal_mark))
    if width is None:
        field = 0
    else:
        field = int(width)
        if field < 0:
            field = 0
    if not trim:
        field = max([field, *(len(core) for core in cores)] or [field])
        cores = [core.rjust(field) for core in cores]
    elif field:
        cores = [core.rjust(field) if len(core) < field else core for core in cores]
    return _pretty(
        cores,
        big_mark,
        big_interval,
        small_mark,
        small_interval,
        decimal_mark,
        trim,
        zero_print,
        drop0trailing,
    )


def _as_breaks(scale_cut):
    if isinstance(scale_cut, str):
        raise ValueError(
            f'`scale_cut` must be a numeric vector, not the string "{scale_cut}".'
        )
    if scale_cut is None or scale_cut is _NA:
        raise ValueError("`scale_cut` must be a numeric vector, not `NA`.")
    if isinstance(scale_cut, dict):
        pairs = list(scale_cut.items())
    elif (
        isinstance(scale_cut, (list, tuple))
        and scale_cut
        and isinstance(scale_cut[0], (list, tuple))
        and len(scale_cut[0]) == 2
    ):
        pairs = [(str(name), value) for name, value in scale_cut]
    elif isinstance(scale_cut, (list, tuple)) and all(
        not isinstance(value, (list, tuple, dict)) for value in scale_cut
    ):
        # A bare numeric vector has no names. A single NA matches the type error.
        if len(scale_cut) == 1 and _is_na(scale_cut[0]):
            raise ValueError("`scale_cut` must be a numeric vector, not `NA`.")
        raise ValueError("`scale_cut` must have names")
    else:
        raise ValueError("`scale_cut` must be a numeric vector, not a list.")
    names = []
    values = []
    for name, value in pairs:
        value = _unwrap(value)
        if value is None or value is _NA or _is_nan(value):
            raise ValueError("`scale_cut` values must not be missing")
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("`scale_cut` must be a numeric vector.")
        names.append("" if name is None else str(name))
        values.append(float(value))
    order = sorted(range(len(values)), key=lambda i: values[i])
    names = [names[i] for i in order]
    values = [values[i] for i in order]
    for left, right in zip(values, values[1:]):
        if left == right:
            raise ValueError("'breaks' are not unique")
    return names, values


def _lookup_break(names, values, name):
    for label, value in zip(names, values):
        if label == name:
            return value
    return None


def _remainder_nonzero(numer, denom):
    if denom is None or denom == 0 or numer is _NA or _is_nan(numer):
        return False
    if not math.isfinite(numer):
        return False
    quot = numer / denom
    rem = quot % 1
    if math.isnan(rem):
        return False
    return rem != 0


def _is_power10(ratio):
    if ratio <= 0 or not math.isfinite(ratio):
        return False
    logged = math.log10(ratio)
    return abs(logged - round(logged)) < 1e-8 or (logged % 1 == 0)


def _locate_break(value, edges):
    """Left-closed interval index, or ``None`` when ``cut`` would return NA."""
    if value is _NA or _is_nan(value) or not math.isfinite(value):
        return None
    if value < edges[0]:
        return None
    # edges[-1] is +Inf, so the last finite edge is edges[-2].
    lo = 0
    hi = len(edges) - 2
    if value >= edges[hi]:
        return hi
    # Rightmost edge[i] <= value.
    left, right = 0, hi
    while left < right:
        mid = (left + right + 1) // 2
        if edges[mid] <= value:
            left = mid
        else:
            right = mid - 1
    return left


def _scale_cut(values, breaks, scale, accuracy, suffix):
    names, edges = _as_breaks(breaks)
    size = len(values)
    cut_edges = edges + [math.inf]
    labels = []
    for index, value in enumerate(values):
        if value is _NA or _is_nan(value):
            magnitude = float("nan")
        else:
            magnitude = abs(value * scale[index])
        slot = _locate_break(magnitude, cut_edges)
        labels.append("" if slot is None else names[slot])
    bad = []
    for index, label in enumerate(labels):
        numer = values[index]
        if numer is _NA or _is_nan(numer):
            bad.append(False)
            continue
        bad.append(_remainder_nonzero(numer * scale[index], _lookup_break(names, edges, label)))
    if any(bad):
        for index, flag in enumerate(bad):
            if not flag:
                continue
            label = labels[index]
            try:
                pos = names.index(label)
            except ValueError:
                continue
            if pos == 0:
                continue
            lower_name = names[pos - 1]
            lower_value = edges[pos - 1]
            divisor = 1.0 if lower_value == 0 else lower_value
            numer = values[index]
            if numer is _NA or _is_nan(numer):
                continue
            if not _remainder_nonzero(numer * scale[index], divisor) and (
                numer * scale[index] / divisor
            ) % 1 == 0:
                current = edges[pos]
                if not _is_power10(current / divisor):
                    labels[index] = lower_name
    break_scale = []
    for index, label in enumerate(labels):
        found = _lookup_break(names, edges, label)
        if found is None or found == 0:
            scaled = scale[index]
        else:
            scaled = scale[index] / found
        if math.isinf(scaled) or math.isnan(scaled):
            scaled = scale[index]
        value = values[index]
        if value is not _NA and not _is_nan(value) and value == 0:
            scaled = 1.0
        if math.isnan(scaled):
            scaled = 1.0
        break_scale.append(scaled)
    suffixes = [labels[i] + suffix[i] for i in range(size)]
    if accuracy is None:
        groups = {}
        order = []
        for index, scaled in enumerate(break_scale):
            key = scaled
            if key not in groups:
                groups[key] = []
                order.append(key)
            groups[key].append(index)
        accuracy_out = [1.0] * size
        for key in order:
            members = groups[key]
            sample = []
            for index in members:
                value = values[index]
                if value is _NA or _is_nan(value):
                    sample.append(float("nan"))
                else:
                    sample.append(value * break_scale[index])
            prec = _precision(sample)
            for index in members:
                accuracy_out[index] = prec
        accuracy = accuracy_out
    return break_scale, suffixes, accuracy


def _pop(kwargs, *names):
    found = False
    value = None
    for name in names:
        if name in kwargs:
            value = kwargs.pop(name)
            found = True
            break
    return found, value


def number(
    x,
    accuracy=None,
    scale=1,
    prefix="",
    suffix="",
    big_mark=None,
    decimal_mark=None,
    style_positive=None,
    style_negative=None,
    scale_cut=None,
    trim=True,
    **kwargs,
):
    """Format ``x`` the way scales 1.4.0 ``number`` does.

    Returns a list of strings. Missing values are ``None``. A named input
    (a dict) keeps its keys on ``CharacterVector.names``.
    """
    values, names = _flatten(x)
    if len(values) == 0:
        return CharacterVector([], names) if names is not None else []

    if big_mark is None:
        big_mark = " "
    else:
        big_mark = _as_text(big_mark)
    if decimal_mark is None:
        decimal_mark = "."
    else:
        decimal_mark = _as_text(decimal_mark)
    if style_positive is None:
        style_positive = "none"
    if style_negative is None:
        style_negative = "hyphen"
    style_positive = _arg_match(style_positive, ("none", "plus", "space"), "style_positive")
    style_negative = _arg_match(
        style_negative, ("hyphen", "minus", "parens"), "style_negative"
    )
    if not isinstance(trim, bool):
        raise TypeError("trim must be TRUE or FALSE")

    found, digits = _pop(kwargs, "digits")
    if not found or digits is None:
        digits = 7
    digits = int(digits)
    found, width = _pop(kwargs, "width")
    if not found:
        width = None
    found, big_interval = _pop(kwargs, "big_interval", "big.interval")
    big_interval = 3 if not found or big_interval is None else int(big_interval)
    found, small_mark = _pop(kwargs, "small_mark", "small.mark")
    small_mark = "" if not found or small_mark is None else _as_text(small_mark)
    found, small_interval = _pop(kwargs, "small_interval", "small.interval")
    small_interval = 5 if not found or small_interval is None else int(small_interval)
    found, zero_print = _pop(kwargs, "zero_print", "zero.print")
    if not found:
        zero_print = None
    found, drop0 = _pop(kwargs, "drop0trailing")
    drop0 = bool(drop0) if found and drop0 is not None else False
    _pop(kwargs, "justify", "na_encode", "na.encode")
    if "scientific" in kwargs:
        raise TypeError("formal argument \"scientific\" matched by multiple actual arguments")
    if kwargs:
        name = next(iter(kwargs))
        raise TypeError(f"unused argument ({name})")

    size = len(values)
    if isinstance(scale, (list, tuple)) or (_np is not None and isinstance(scale, _np.ndarray)):
        scale_values = [_coerce_number(value) for value in list(scale)]
    else:
        scale_values = [_coerce_number(scale)]
    scale_values = _recycle(scale_values, size)
    if any(value is _NA or _is_nan(value) for value in scale_values):
        raise ValueError("missing values are not allowed in scale")
    prefix_values = _recycle([_as_text(prefix)] if not isinstance(prefix, (list, tuple)) else [_as_text(v) for v in prefix], size)
    suffix_values = _recycle([_as_text(suffix)] if not isinstance(suffix, (list, tuple)) else [_as_text(v) for v in suffix], size)

    if accuracy is None:
        accuracy_values = None
    elif isinstance(accuracy, (list, tuple)) or (
        _np is not None and isinstance(accuracy, _np.ndarray)
    ):
        accuracy_values = [_coerce_number(value) for value in list(accuracy)]
    else:
        accuracy_values = [_coerce_number(accuracy)]

    if scale_cut is not None:
        if accuracy_values is not None:
            accuracy_values = _recycle(accuracy_values, size)
        scale_values, suffix_values, accuracy_values = _scale_cut(
            values, scale_cut, scale_values, accuracy_values, suffix_values
        )
    elif accuracy_values is None:
        product = []
        for value, factor in zip(values, scale_values):
            if value is _NA or _is_nan(value):
                product.append(float("nan"))
            else:
                product.append(value * factor)
        accuracy_values = [_precision(product)]

    # nsmall follows the accuracy vector before it is recycled to ``x``.
    nsmall_source = list(accuracy_values)
    nsmalls = [_nsmall_one(value) for value in nsmall_source]
    accuracy_full = _recycle(list(accuracy_values), size)

    # accuracy is measured on the scaled data, so the step on x is accuracy/scale.
    rounded = []
    for index in range(size):
        acc = accuracy_full[index]
        fac = scale_values[index]
        if acc is _NA or _is_nan(acc) or _is_nan(fac):
            divisor = float("nan")
        elif fac == 0.0:
            divisor = float("inf") if acc != 0 else float("nan")
        else:
            divisor = acc / fac
        rounded.append(_round_any(values[index], divisor))
    signs = []
    absolute = []
    for value in rounded:
        if value is _NA or _is_nan(value):
            signs.append(0)
            absolute.append(_NA if value is _NA else float("nan"))
        else:
            if value < 0:
                signs.append(-1)
            elif value > 0:
                signs.append(1)
            else:
                signs.append(0)
            absolute.append(abs(value))
    scaled = []
    for value, factor in zip(absolute, scale_values):
        if value is _NA:
            scaled.append(_NA)
        elif _is_nan(value):
            scaled.append(float("nan"))
        else:
            scaled.append(factor * value)

    nsmall_full = _recycle(nsmalls, size)
    rendered = [""] * size
    for small in dict.fromkeys(nsmalls):
        chosen = [index for index, value in enumerate(nsmall_full) if value == small]
        formatted = _format_fixed(
            [scaled[index] for index in chosen],
            small,
            digits,
            trim,
            width,
            decimal_mark,
            big_mark,
            big_interval,
            small_mark,
            small_interval,
            zero_print,
            drop0,
        )
        for index, text in zip(chosen, formatted):
            rendered[index] = text

    out = [
        prefix_values[i] + rendered[i] + suffix_values[i] for i in range(size)
    ]
    for index, value in enumerate(absolute):
        if value is not _NA and not _is_nan(value) and math.isinf(value):
            out[index] = "Inf" if value > 0 else "-Inf"
    for index, sign in enumerate(signs):
        if sign < 0:
            if style_negative == "hyphen":
                out[index] = "-" + out[index]
            elif style_negative == "minus":
                out[index] = "\u2212" + out[index]
            else:
                out[index] = "(" + out[index] + ")"
        elif sign > 0:
            if style_positive == "plus":
                out[index] = "+" + out[index]
            elif style_positive == "space":
                out[index] = "\u2007" + out[index]
    result = []
    for index, value in enumerate(absolute):
        if value is _NA or _is_nan(value):
            result.append(None)
        else:
            result.append(out[index])
    if names is None:
        return result
    return CharacterVector(result, names)
