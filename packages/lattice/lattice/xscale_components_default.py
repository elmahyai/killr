"""Default x-axis scale components (``xscale.components.default`` in lattice 0.23-1)."""

from __future__ import annotations

import math
import sys
from decimal import ROUND_HALF_EVEN, Decimal, localcontext
from typing import Any

import numpy as np

from lattice.lattice_get_option import lattice_get_option

_EPS = sys.float_info.epsilon
_DBL_MIN = sys.float_info.min
_DBL_MAX = sys.float_info.max
_ROUNDING_EPS = 1e-10


def xscale_components_default(
    lim,
    packet_number: int = 0,
    packet_list=None,
    top: bool = True,
    **kwargs: Any,
):
    """Build bottom tick/label components for the x scale of one panel."""
    del packet_number, packet_list
    comps = _calculate_axis_components(lim, **kwargs)
    return {
        "num.limit": comps["num.limit"],
        "bottom": {
            "ticks": {"at": comps["at"], "tck": 1},
            "labels": {
                "at": comps["at"],
                "labels": comps["labels"],
                "check.overlap": comps["check.overlap"],
            },
        },
        "top": top,
    }


def _calculate_axis_components(x, **kwargs: Any) -> dict[str, Any]:
    if _all_na(x):
        return {
            "at": [],
            "labels": [],
            "check.overlap": True,
            "num.limit": [0.0, 1.0],
        }
    ans = _formatted_ticks_and_labels(x, **kwargs)
    rng = [min(ans["num.limit"]), max(ans["num.limit"])]
    at = np.asarray(ans["at"], dtype=float)
    ok = (at >= rng[0]) & (at <= rng[1])
    labels = list(ans["labels"])
    at_list = at[ok].tolist()
    labels = [labels[i] for i in range(len(labels)) if ok[i]]
    abbreviate = kwargs.get("abbreviate")
    minlength = kwargs.get("minlength", 4)
    if abbreviate is True:
        labels = [_abbreviate(label, minlength) for label in labels]
    return {
        "at": at_list,
        "labels": labels,
        "check.overlap": ans["check.overlap"],
        "num.limit": ans["num.limit"],
    }


def _formatted_ticks_and_labels(x, **kwargs: Any) -> dict[str, Any]:
    values = _as_sequence(x)
    if values and all(isinstance(v, str) for v in values):
        return _formatted_ticks_and_labels_character(values, **kwargs)
    return _formatted_ticks_and_labels_default(values, **kwargs)


def _formatted_ticks_and_labels_default(x, **kwargs: Any) -> dict[str, Any]:
    at = kwargs.get("at", False)
    labels = kwargs.get("labels", False)
    logsc = kwargs.get("log", kwargs.get("logsc", False))
    num_limit = kwargs.get("num.limit")
    equispaced_log = kwargs.get("equispaced.log", True)

    numeric = [float(v) for v in x if _is_finite_number(v)]
    rng = (
        [float(x[0]), float(x[1])]
        if len(x) == 2
        else [min(numeric), max(numeric)] if numeric else [0.0, 1.0]
    )

    if logsc is True:
        logsc = 10
    have_log = not (logsc is False or logsc is None)
    logbase: float | None = None
    logpaste = ""
    if have_log:
        if isinstance(logsc, (int, float)):
            logbase = float(logsc)
        elif logsc == "e":
            logbase = math.exp(1)
        else:
            raise ValueError("Invalid value of 'log'")
        logpaste = f"{logsc}^"

    check_overlap = bool(
        (at is False or at is None or (isinstance(at, bool) and not at))
        and (labels is False or labels is None or (isinstance(labels, bool) and not labels))
    )

    at_is_logical = at is False or at is None or (isinstance(at, bool) and not at)
    labels_is_logical = labels is False or labels is None or (isinstance(labels, bool) and not labels)

    if at_is_logical:
        finite_x = [float(v) for v in x if _is_finite_number(v)]
        if have_log and not equispaced_log:
            if logbase is None:
                raise ValueError("Invalid value of 'log'")
            usr = [math.log10(logbase ** rng[0]), math.log10(logbase ** rng[1])]
            at_vals = _axis_ticks(usr, log=True, **kwargs)
        else:
            at_vals = _pretty(finite_x, **kwargs)
    elif have_log and len(at) > 0:
        if logbase is None:
            raise ValueError("Invalid value of 'log'")
        if labels_is_logical:
            labels = [str(v) for v in at]
        at_vals = [math.log(float(v), logbase) for v in at]
    else:
        at_vals = [float(v) for v in at]

    if labels_is_logical:
        if have_log and not equispaced_log:
            label_vals = [str(v) for v in at_vals]
            if logbase is None:
                raise ValueError("Invalid value of 'log'")
            at_vals = [math.log(float(v), logbase) for v in at_vals]
        else:
            label_vals = [f"{logpaste}{text}" for text in _format_trim(at_vals)]
    else:
        label_vals = [str(v) for v in labels]

    return {
        "at": at_vals,
        "labels": label_vals,
        "check.overlap": check_overlap,
        "num.limit": rng,
    }


def _formatted_ticks_and_labels_character(x, **kwargs: Any) -> dict[str, Any]:
    at = kwargs.get("at", False)
    labels = kwargs.get("labels", False)
    used_at = kwargs.get("used.at")
    num_limit = kwargs.get("num.limit")

    retain = True
    if used_at is not None and not any(_is_na(v) for v in _as_sequence(used_at)):
        retain = used_at

    if at is False or at is None or (isinstance(at, bool) and not at):
        if retain is True:
            at_vals = list(range(1, len(x) + 1))
        else:
            at_vals = [i + 1 for i, keep in enumerate(_as_sequence(retain)) if keep]
    else:
        at_vals = [float(v) for v in at]

    if labels is False or labels is None or (isinstance(labels, bool) and not labels):
        if all(a in range(1, len(x) + 1) for a in at_vals):
            label_vals = [x[int(a) - 1] for a in at_vals]
        else:
            label_vals = [str(a) for a in at_vals]
    else:
        label_vals = [str(v) for v in labels]

    factor_pad = float(lattice_get_option("axis.padding")["factor"])
    if num_limit is None or any(_is_na(v) for v in _as_sequence(num_limit)):
        base_limit = [1.0, float(len(x))]
    else:
        seq = _as_sequence(num_limit)
        base_limit = [float(seq[0]), float(seq[1])]
    limit = [-factor_pad + base_limit[0], factor_pad + base_limit[1]]

    return {
        "at": at_vals,
        "labels": label_vals,
        "check.overlap": False,
        "num.limit": limit,
    }


def _axis_ticks(usr, *, log: bool, **kwargs: Any) -> list[float]:
    """Minimal ``grDevices::axisTicks`` for log axes (``log = TRUE``)."""
    del kwargs
    lo, hi = float(usr[0]), float(usr[1])
    if not log:
        return _pretty([lo, hi])
    if lo > hi:
        lo, hi = hi, lo
    if lo == hi:
        return [lo]
    span = hi - lo
    raw = []
    tick = math.floor(lo)
    while tick <= hi + 1e-12:
        if lo - 1e-12 <= tick <= hi + 1e-12:
            raw.append(float(tick))
        tick += 1.0
    if len(raw) >= 2:
        return raw
    step = span / 5.0 if span else 1.0
    return [lo + i * step for i in range(6)]


def _abbreviate(text: str, minlength: int) -> str:
    text = str(text)
    if len(text) <= minlength:
        return text
    if minlength <= 1:
        return text[:1]
    return text[: minlength - 1] + "."


def _pretty(x, n=5, min_n=None, shrink_sml=0.75, high_u_bias=1.5, u5_bias=None, eps_correct=0, f_min=2**-20, **_extra):
    finite = [float(v) for v in x if _is_finite_number(v)]
    if not finite:
        return []
    if min_n is None:
        min_n = int(n) // 3
    if u5_bias is None:
        u5_bias = 0.5 + 1.5 * high_u_bias
    lo, up, ndiv, _unit = _r_pretty(
        min(finite),
        max(finite),
        int(n),
        int(min_n),
        float(shrink_sml),
        (float(high_u_bias), float(u5_bias), float(f_min)),
        int(eps_correct),
        True,
    )
    breaks = _seq_length(lo, up, ndiv + 1)
    if not eps_correct and ndiv:
        delta = abs(up - lo) / ndiv
        breaks = [0.0 if abs(v) < 1e-14 * delta else v for v in breaks]
    return breaks


def _seq_length(from_, to, length_out):
    length_out = int(length_out)
    if length_out <= 0:
        return []
    if length_out == 1:
        return [float(from_)]
    if length_out == 2:
        return [float(from_), float(to)]
    if from_ == to:
        return [float(from_)] * length_out
    n1 = length_out - 1
    step = (to - from_) / n1
    middle = [from_ + i * step for i in range(1, length_out - 1)]
    return [float(from_), *[float(v) for v in middle], float(to)]


def _r_pretty(lo, up, ndiv, min_n, shrink_sml, high_u_fact, eps_correction, return_bounds):
    h, h5, f_min = high_u_fact
    lo_in = lo
    up_in = up
    span = up_in - lo_in
    if span == 0 and up_in == 0:
        cell = 1.0
        small = True
    else:
        cell = max(abs(lo_in), abs(up_in))
        unit_bound = 1 / (1 + h) if h5 >= 1.5 * h + 0.5 else 1.5 / (1 + h5)
        unit_bound = (1 + unit_bound) * max(1, ndiv) * _EPS
        small = span < cell * unit_bound * 3
    if small:
        if cell > 10:
            cell = 9 + cell / 10
        cell *= shrink_sml
        if min_n > 1:
            cell /= min_n
    else:
        cell = span
        if math.isfinite(span):
            if ndiv > 1:
                cell /= ndiv
        elif ndiv >= 2:
            cell = up_in / ndiv - lo_in / ndiv
    smallest = f_min * _DBL_MIN
    if smallest == 0:
        smallest = _DBL_MIN
    if cell < smallest:
        cell = smallest
    elif cell > _DBL_MAX / 1.25:
        cell = _DBL_MAX / 1.25
    base = 10.0 ** math.floor(math.log10(cell))
    unit = base
    candidate = 2 * base
    if candidate - cell < h * (cell - unit):
        unit = candidate
        candidate = 5 * base
        if candidate - cell < h5 * (cell - unit):
            unit = candidate
            candidate = 10 * base
            if candidate - cell < h * (cell - unit):
                unit = candidate
    ns = math.floor(lo_in / unit + _ROUNDING_EPS)
    nu = math.ceil(up_in / unit - _ROUNDING_EPS)
    if eps_correction and (eps_correction > 1 or not small):
        lo = lo * (1 - _EPS) if lo_in != 0 else -_DBL_MIN
        up = up * (1 + _EPS) if up_in != 0 else _DBL_MIN
    while ns * unit > lo + _ROUNDING_EPS * unit:
        ns -= 1
    while not math.isfinite(ns * unit):
        ns += 1
    while nu * unit < up - _ROUNDING_EPS * unit:
        nu += 1
    while not math.isfinite(nu * unit):
        nu -= 1
    intervals = int(0.5 + nu - ns)
    if intervals < min_n:
        extra = min_n - intervals
        if lo_in == 0 and ns == 0 and up_in != 0:
            nu += extra
        elif up_in == 0 and nu == 0 and lo_in != 0:
            ns -= extra
        elif ns >= 0:
            nu += extra // 2
            ns -= extra // 2 + extra % 2
        else:
            ns -= extra // 2
            nu += extra // 2 + extra % 2
        ndiv = min_n
    else:
        ndiv = intervals
    if return_bounds:
        if ns * unit < lo:
            lo = ns * unit
        if nu * unit > up:
            up = nu * unit
    else:
        lo = ns
        up = nu
    return lo, up, ndiv, unit


def _format_trim(values) -> list[str]:
    formatted = _format_numeric(values)
    return [text.strip() for text in formatted]


def _format_numeric(values, digits: int = 7) -> list[str]:
    raw = []
    for value in values:
        if value is None or (isinstance(value, float) and math.isnan(value)):
            raw.append(None)
        else:
            raw.append(float(value))
    scientific = any(item is not None and _wants_scientific(item, digits) for item in raw)
    natural = []
    for item in raw:
        if item is None:
            natural.append("NA")
        elif scientific:
            natural.append(_natural_scientific(item, digits))
        else:
            natural.append(_natural_fixed(item, digits))
    places = max((_decimal_places(text) for text in natural if text != "NA"), default=0)
    padded = ["NA" if item is None else _pad_decimals(text, places) for item, text in zip(raw, natural)]
    width = max(len(text) for text in padded)
    return [text.rjust(width) for text in padded]


def _rounded_parts(value: float, digits: int = 7):
    number = Decimal(str(value))
    if number == 0:
        return "", "0", 0
    sign = "-" if number < 0 else ""
    number = abs(number)
    exponent = int(number.adjusted())
    quantum = Decimal(10) ** (exponent - digits + 1)
    rounded = number.quantize(quantum, rounding=ROUND_HALF_EVEN)
    if rounded == 0:
        return "", "0", 0
    exponent = int(rounded.adjusted())
    quantum = Decimal(10) ** (exponent - digits + 1)
    scaled = (rounded / quantum).to_integral_value(rounding=ROUND_HALF_EVEN)
    text = f"{int(scaled):0{digits}d}"
    return sign, text, exponent


def _is_pow10(value: float) -> bool:
    _sign, text, _exponent = _rounded_parts(value)
    return set(text[1:]) <= {"0"}


def _natural_fixed(value: float, digits: int = 7) -> str:
    sign, text, exponent = _rounded_parts(value, digits)
    if exponent >= 0:
        if exponent + 1 >= len(text):
            body = text + ("0" * (exponent + 1 - len(text)))
        else:
            body = text[: exponent + 1] + "." + text[exponent + 1 :]
    else:
        body = "0." + ("0" * (-exponent - 1)) + text
    if "." in body:
        body = body.rstrip("0").rstrip(".")
    return sign + (body or "0")


def _natural_scientific(value: float, digits: int = 7) -> str:
    if value == 0:
        return "0e+00"
    sign, text, exponent = _rounded_parts(value, digits)
    frac = text[1:].rstrip("0")
    body = text[0] if not frac else f"{text[0]}.{frac}"
    return f"{sign}{body}e{exponent:+03d}"


def _wants_scientific(value: float, digits: int = 7) -> bool:
    if not math.isfinite(value) or value == 0:
        return False
    magnitude = abs(value)
    if magnitude <= 1e-4 or (magnitude >= 1e5 and _is_pow10(magnitude)):
        return True
    return len(_natural_scientific(value, digits)) < len(_natural_fixed(value, digits))


def _decimal_places(text: str) -> int:
    if "e" in text or "E" in text:
        significand = text.split("e")[0].split("E")[0]
        if "." not in significand:
            return 0
        return len(significand.split(".", 1)[1])
    if "." not in text:
        return 0
    return len(text.split(".", 1)[1])


def _pad_decimals(text: str, places: int) -> str:
    if "e" in text or "E" in text:
        significand, exponent = text.split("e")
        sign = ""
        if significand.startswith("-"):
            sign = "-"
            significand = significand[1:]
        whole, _, frac = significand.partition(".")
        frac = frac[:places].ljust(places, "0")
        body = whole if places == 0 else f"{whole}.{frac}"
        return f"{sign}{body}e{exponent}"
    sign = ""
    if text.startswith("-"):
        sign = "-"
        text = text[1:]
    whole, _, frac = text.partition(".")
    if places == 0:
        return f"{sign}{whole}"
    frac = frac[:places].ljust(places, "0")
    return f"{sign}{whole}.{frac}"


def _as_sequence(x):
    if isinstance(x, np.ndarray):
        return x.tolist()
    if isinstance(x, (list, tuple)):
        return list(x)
    return [x]


def _is_finite_number(value) -> bool:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return False
    return math.isfinite(number)


def _is_na(value) -> bool:
    if value is None:
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    return False


def _all_na(x) -> bool:
    seq = _as_sequence(x)
    if not seq:
        return False
    return all(_is_na(v) for v in seq)
