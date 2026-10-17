"""Argument checks corresponding to VAL_IN_ENV in R/internal.R."""

from __future__ import annotations

from fansi._const import (
    VALID_CTL,
    VALID_ROUND,
    VALID_TERM_CAP,
    VALID_TYPES,
    WARN_ERROR,
    WARN_MANGLED,
    WARN_UTF8,
    ctl_as_int,
)

OPTIONS = {
    "fansi.warn": True,
    "fansi.term.cap": None,
    "fansi.normalize": False,
    "fansi.carry": False,
    "fansi.terminate": True,
    "fansi.tab.stops": 8,
    "fansi.tabs.as.spaces": False,
    "fansi.html.esc": "<>&'\"",
    "fansi.css": None,
    "fansi.style": None,
}


class FansiError(ValueError):
    """An R stop() from fansi, with the same message text."""


def option(name, default=None):
    if name in OPTIONS and OPTIONS[name] is not None:
        return OPTIONS[name]
    return default


def warn_mask_worst():
    return WARN_MANGLED | WARN_UTF8


def pmatch(value, choices):
    if not isinstance(value, str):
        return None
    exact = [i for i, choice in enumerate(choices) if choice == value]
    if len(exact) == 1:
        return exact[0]
    hits = [i for i, choice in enumerate(choices) if choice.startswith(value)]
    if len(hits) == 1:
        return hits[0]
    return None


def exact_match(values, choices):
    found = []
    for value in values:
        if not isinstance(value, str) or value not in choices:
            found.append(None)
        else:
            found.append(choices.index(value) + 1)
    return found


def as_character(value):
    """Coerce one R object the way the string functions coerce `x`."""
    if isinstance(value, str):
        return [value]
    if value is None:
        return [None]
    if isinstance(value, bool):
        return ["TRUE" if value else "FALSE"]
    if isinstance(value, int):
        return [str(value)]
    if isinstance(value, float):
        if value != value:
            return [None]
        return [str(value) if not value.is_integer() else str(int(value))]
    if isinstance(value, (list, tuple)):
        out = []
        for item in value:
            if item is None:
                out.append(None)
            elif isinstance(item, str):
                out.append(item)
            elif isinstance(item, bool):
                out.append("TRUE" if item else "FALSE")
            elif isinstance(item, int):
                out.append(str(item))
            elif isinstance(item, float):
                if item != item:
                    out.append(None)
                else:
                    out.append(str(item) if not item.is_integer() else str(int(item)))
            else:
                raise FansiError(
                    f"Argument `x` must be character, is {type(item).__name__}."
                )
        return out
    raise FansiError(f"Argument `x` must be character, is {type(value).__name__}.")


def _logical(value, name):
    if isinstance(value, bool):
        return value
    if value is None:
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if isinstance(value, float) and value != value:
            return None
        if value == 0:
            return False
        if value == 1:
            return True
    if isinstance(value, str) and value in ("TRUE", "FALSE"):
        return value == "TRUE"
    raise FansiError(f"Argument `{name}` must be TRUE or FALSE.")


def prepare(
    *,
    x=None,
    warn=None,
    term_cap=None,
    ctl=None,
    normalize=None,
    carry=None,
    terminate=None,
    tab_stops=None,
    tabs_as_spaces=None,
    strip_spaces=None,
    round_=None,
    type_=None,
    start=None,
    stop=None,
    keep_na=None,
    allow_na=None,
    valid_types=VALID_TYPES[:3],
    warn_mask=None,
    coerce_x=True,
):
    """Return normalized arguments. CTL indexes are 1-based match() results."""
    if warn_mask is None:
        warn_mask = WARN_MANGLED | WARN_UTF8
    out = {}
    if x is not None or coerce_x:
        if not coerce_x and not (
            isinstance(x, str) or (isinstance(x, (list, tuple)) and all(
                item is None or isinstance(item, str) for item in x
            ))
        ):
            kind = "NULL" if x is None else type(x).__name__
            raise FansiError(f"Argument `x` must be character, is {kind}.")
        out["x"] = as_character(x) if coerce_x else (
            [x] if isinstance(x, str) else list(x)
        )
    if warn is not None:
        flag = _logical(warn, "warn")
        if flag is None:
            raise FansiError("Argument `warn` must be TRUE or FALSE.")
        out["warn"] = flag
        out["warn_int"] = warn_mask if flag else (warn_mask & WARN_ERROR)
    if normalize is not None:
        flag = _logical(normalize, "normalize")
        if flag is None:
            raise FansiError("Argument `normalize` must be TRUE or FALSE.")
        out["normalize"] = flag
    if term_cap is not None:
        if isinstance(term_cap, str):
            term_cap = [term_cap]
        if not isinstance(term_cap, (list, tuple)) or not all(
            isinstance(item, str) for item in term_cap
        ):
            raise FansiError("Argument `term.cap` must be character.")
        indexes = exact_match(term_cap, VALID_TERM_CAP)
        if any(item is None for item in indexes):
            raise FansiError(
                "Argument `term.cap` may only contain values in "
                + _deparse(VALID_TERM_CAP)
            )
        out["term_cap"] = list(term_cap)
        out["term_cap_int"] = indexes
    if ctl is not None:
        if isinstance(ctl, str):
            ctl = [ctl]
        if not isinstance(ctl, (list, tuple)) or not all(
            isinstance(item, str) for item in ctl
        ):
            raise FansiError("Argument `ctl` must be character.")
        indexes = exact_match(list(ctl), VALID_CTL)
        if any(item is None for item in indexes):
            raise FansiError(
                "Argument `ctl` may contain only values in `"
                + _deparse(VALID_CTL)
                + "`"
            )
        out["ctl"] = list(ctl)
        out["ctl_int"] = indexes
        out["ctl_bits"] = ctl_as_int(indexes) if indexes else 0
    if carry is not None:
        if isinstance(carry, (list, tuple)):
            if len(carry) != 1:
                raise FansiError("Argument `carry` must be scalar.")
            carry = carry[0]
        if carry is None:
            raise FansiError("Argument `carry` may not be NA.")
        if not isinstance(carry, (bool, str)):
            raise FansiError("Argument `carry` must be logical or character.")
        if isinstance(carry, bool):
            carry = "" if carry else None
        out["carry"] = carry
    if terminate is not None:
        flag = _logical(terminate, "terminate")
        if flag is None:
            raise FansiError("Argument `terminate` must be TRUE or FALSE")
        out["terminate"] = flag
    if tab_stops is not None:
        stops = tab_stops if isinstance(tab_stops, (list, tuple)) else [tab_stops]
        if not stops:
            raise FansiError(
                "Argument `tab.stops` must be numeric, strictly positive, and "
                "representable as an integer."
            )
        converted = []
        for stop in stops:
            if isinstance(stop, bool) or not isinstance(stop, (int, float)):
                raise FansiError(
                    "Argument `tab.stops` must be numeric, strictly positive, and "
                    "representable as an integer."
                )
            if isinstance(stop, float) and stop != stop:
                raise FansiError(
                    "Argument `tab.stops` must be numeric, strictly positive, and "
                    "representable as an integer."
                )
            if stop < 1:
                raise FansiError(
                    "Argument `tab.stops` must be numeric, strictly positive, and "
                    "representable as an integer."
                )
            converted.append(int(stop))
        out["tab_stops"] = converted
    if tabs_as_spaces is not None:
        flag = _logical(tabs_as_spaces, "tabs.as.spaces")
        if flag is None:
            raise FansiError("Argument `tabs.as.spaces` must be TRUE or FALSE.")
        out["tabs_as_spaces"] = flag
    if strip_spaces is not None:
        flag = _logical(strip_spaces, "strip.spaces")
        if flag is None:
            raise FansiError("Argument `strip.spaces` must be TRUE or FALSE.")
        out["strip_spaces"] = flag
    if round_ is not None:
        index = pmatch(round_, VALID_ROUND)
        if index is None:
            raise FansiError(
                "Argument `round` must partial match one of " + _deparse(VALID_ROUND)
            )
        out["round"] = VALID_ROUND[index]
        out["round_int"] = index + 1
    if type_ is not None:
        index = pmatch(type_, valid_types)
        if index is None:
            raise FansiError(
                "Argument `type` must partial match one of " + _deparse(valid_types)
            )
        out["type"] = valid_types[index]
        out["type_int"] = index
    if start is not None or stop is not None:
        length = len(out.get("x", []))
        out["start"] = _recycle_int(start, length, "start")
        out["stop"] = _recycle_int(stop, length, "stop")
    if keep_na is not None:
        if isinstance(keep_na, (list, tuple)) and len(keep_na) != 1:
            raise FansiError(
                "Argument `keepNA` must be interpretable as a scalar logical."
            )
        flag = _logical(keep_na, "keepNA")
        out["keep_na"] = flag
    if allow_na is not None:
        if isinstance(allow_na, (list, tuple)) and len(allow_na) != 1:
            raise FansiError(
                "Argument `allowNA` must be interpretable as a scalar logical."
            )
        flag = _logical(allow_na, "allowNA")
        out["allow_na"] = bool(flag)
    return out


def _recycle_int(value, length, name):
    if isinstance(value, (list, tuple)):
        values = list(value)
    else:
        values = [value]
    if not values:
        raise FansiError(f"Argument `{name}` must be interpretable as an integer.")
    converted = []
    for item in values:
        if item is None or (isinstance(item, float) and item != item):
            converted.append(None)
            continue
        if isinstance(item, bool) or not isinstance(item, (int, float)):
            raise FansiError(f"Argument `{name}` must be interpretable as an integer.")
        converted.append(int(item))
    if length == 0:
        return []
    return [converted[i % len(converted)] for i in range(length)]


def _deparse(values):
    body = ", ".join(f'"{value}"' for value in values)
    return "c(" + body + ")"
