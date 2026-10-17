"""Quarterly yearqtr values from zoo.

A yearqtr is a numeric vector. Quarter 1 of year y is y, quarter 2 is y + 1/4,
and so on. ``yearqtr`` stores ``floor(4 * x + 0.001) / 4``.
"""

from __future__ import annotations

import datetime as dt
import math
import warnings
from typing import Any

import numpy as np

from zoo.yearmon import (
    RDate,
    Yearmon,
    _MONTH_ABBR,
    _MONTH_FULL,
    _external_error,
    _foreign_class,
    _is_character,
    _is_integer_input,
    _plain_numeric,
    _recycle,
    _reject_external,
    as_date_from_year_fraction,
    as_numeric,
    as_yearmon,
    civil_from_days,
    yearmon,
)


class Yearqtr:
    """Numeric vector with class yearqtr."""

    r_class = "yearqtr"

    def __init__(self, values: Any, names: Any = None):
        self.value = np.asarray(values, dtype=np.float64).reshape(-1).copy()
        if names is None:
            self.names = None
        else:
            named = list(names)
            self.names = named if len(named) == self.value.size else None

    def __len__(self) -> int:
        return int(self.value.size)

    def __repr__(self) -> str:
        return f"yearqtr({self.value.tolist()})"

    def __str__(self) -> str:
        if self.value.size == 0:
            return "yearqtr of length 0"
        parts = ["NA" if item is None else item for item in format_yearqtr(self)]
        return " ".join(parts)

    def __array__(self, dtype: Any = None, copy: bool | None = None) -> np.ndarray:
        if dtype is None:
            return self.value
        return self.value.astype(dtype)

    def __iter__(self):
        for item in self.value:
            yield float(item)

    def __getitem__(self, key: Any) -> Yearqtr:
        taken = self.value[key]
        return Yearqtr(np.atleast_1d(taken))

    def __setitem__(self, key: Any, value: Any) -> None:
        coerced = as_yearqtr(value).value
        self.value[key] = coerced if coerced.size != 1 else coerced[0]

    def __neg__(self) -> np.ndarray:
        return -self.value

    def __pos__(self) -> Any:
        raise TypeError('argument "e2" is missing, with no default')

    def __add__(self, other: Any) -> Yearqtr:
        return _ops(self, other, np.add)

    def __radd__(self, other: Any) -> Yearqtr:
        return _ops(other, self, np.add)

    def __sub__(self, other: Any) -> Any:
        if isinstance(other, Yearqtr):
            left, right = _recycle(self.value, other.value)
            return left - right
        if _foreign_class(other) or isinstance(other, Yearmon):
            raise TypeError(
                "can only subtract yearqtr objects and numbers from yearqtr objects"
            )
        left, right = _recycle(self.value, _plain_numeric(other))
        return yearqtr(left - right)

    def __rsub__(self, other: Any) -> Any:
        raise TypeError("Can only subtract from yearqtr objects")

    def __mul__(self, other: Any) -> Yearqtr:
        return _ops(self, other, np.multiply)

    def __rmul__(self, other: Any) -> Yearqtr:
        return _ops(other, self, np.multiply)

    def __truediv__(self, other: Any) -> Yearqtr:
        return _ops(self, other, np.divide)

    def __rtruediv__(self, other: Any) -> Yearqtr:
        return _ops(other, self, np.divide)

    def __floordiv__(self, other: Any) -> Yearqtr:
        return _ops(self, other, np.floor_divide)

    def __rfloordiv__(self, other: Any) -> Yearqtr:
        return _ops(other, self, np.floor_divide)

    def __mod__(self, other: Any) -> Yearqtr:
        return _ops(self, other, np.remainder)

    def __rmod__(self, other: Any) -> Yearqtr:
        return _ops(other, self, np.remainder)

    def __pow__(self, other: Any) -> Yearqtr:
        return _ops(self, other, np.power)

    def __rpow__(self, other: Any) -> Yearqtr:
        return _ops(other, self, np.power)

    def __eq__(self, other: Any) -> np.ndarray:
        return _compare(self, other, lambda a, b: a == b)

    def __ne__(self, other: Any) -> np.ndarray:
        return _compare(self, other, lambda a, b: a != b)

    def __lt__(self, other: Any) -> np.ndarray:
        return _compare(self, other, lambda a, b: a < b)

    def __le__(self, other: Any) -> np.ndarray:
        return _compare(self, other, lambda a, b: a <= b)

    def __gt__(self, other: Any) -> np.ndarray:
        return _compare(self, other, lambda a, b: a > b)

    def __ge__(self, other: Any) -> np.ndarray:
        return _compare(self, other, lambda a, b: a >= b)

    __hash__ = None


def _ops(left: Any, right: Any, op: Any) -> Yearqtr:
    a = as_yearqtr(left).value
    b = as_yearqtr(right).value
    a, b = _recycle(a, b)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        return yearqtr(op(a, b))


def _compare(self: Yearqtr, other: Any, op: Any) -> np.ndarray:
    left, right = _recycle(as_yearqtr(self).value, as_yearqtr(other).value)
    out = np.empty(left.size, dtype=object)
    for i, (ai, bi) in enumerate(zip(left, right)):
        if np.isnan(ai) or np.isnan(bi):
            out[i] = None
        else:
            out[i] = bool(op(ai, bi))
    return out


def yearqtr(x: Any) -> Yearqtr:
    """Snap a numeric year fraction onto quarter boundaries."""
    if isinstance(x, Yearqtr):
        arr = x.value
        names = x.names
    else:
        arr = _plain_numeric(x)
        names = None
    snapped = np.floor(4.0 * arr + 0.001) / 4.0
    return Yearqtr(snapped, names)


def as_yearqtr_integer(x: Any, *args: Any, **kwargs: Any) -> Yearqtr:
    return Yearqtr(_plain_numeric(x))


def as_yearqtr_default(x: Any, *args: Any, **kwargs: Any) -> Yearqtr:
    """Coerce with as.numeric, then with the numeric method."""
    return as_yearqtr(as_numeric(x))


def _r_round(x: np.ndarray) -> np.ndarray:
    return np.round(x)


def as_yearqtr_character(x: Any, format: str | None = None, *args: Any, **kwargs: Any) -> Yearqtr:
    from zoo.yearmon import _character_items

    items = _character_items(x)
    present = [item for item in items if item is not None]
    if not present:
        return Yearqtr(np.full(len(items), np.nan))
    if format is None or format == "":
        if all("q" in item for item in present):
            format = "%Y q%q"
        elif all("Q" in item for item in present):
            format = "%Y Q%q"
        else:
            format = "%Y-%q"
    if len(format) and ("%q" in format or "%Q" in format):
        # sub() replaces the first %q only. %Q is left in place.
        rewritten = format.replace("%q", "%m", 1)
        parsed = as_yearmon(items, format=rewritten).value
        fractional = np.remainder(parsed, 1.0)
        m0 = _r_round(12.0 * fractional)
        years = np.floor(parsed)
        values = np.where(m0 > 3, np.nan, years + m0 / 4.0)
        values = np.where(np.isnan(parsed), np.nan, values)
    else:
        values = as_yearmon(items, format=format).value
    return yearqtr(values)


def as_yearqtr_yearqtr(x: Any, *args: Any, **kwargs: Any) -> Yearqtr:
    return x


def _through_yearmon(x: Any) -> Yearqtr:
    return yearqtr(as_yearmon(x).value)


def as_yearqtr(x: Any = None, *args: Any, **kwargs: Any) -> Yearqtr:
    """Dispatch as.yearqtr on the class of x."""
    if x is None:
        return Yearqtr(np.array([], dtype=np.float64))
    _reject_external(x, "as.yearqtr")
    if isinstance(x, Yearqtr):
        return x
    if isinstance(x, dt.datetime) or (
        isinstance(x, (list, tuple)) and x and isinstance(x[0], dt.datetime)
    ):
        return _through_yearmon(x)
    if isinstance(x, RDate) or (isinstance(x, dt.date) and not isinstance(x, dt.datetime)):
        return _through_yearmon(x)
    if isinstance(x, (list, tuple)) and x and isinstance(x[0], dt.date):
        return _through_yearmon(x)
    if isinstance(x, np.ndarray) and np.issubdtype(x.dtype, np.datetime64):
        return _through_yearmon(x)
    if isinstance(x, Yearmon):
        return as_yearqtr_default(x)
    if _is_character(x) or (
        isinstance(x, (list, tuple)) and any(isinstance(item, str) for item in x)
    ):
        if args:
            format = args[0]
        else:
            format = kwargs.get("format", None)
        return as_yearqtr_character(x, format=format)
    if isinstance(x, bool) or (
        isinstance(x, np.generic) and np.issubdtype(type(x), np.bool_)
    ):
        return as_yearqtr_default(x)
    if _is_integer_input(x):
        return as_yearqtr_integer(x)
    if isinstance(x, (float, np.floating, np.ndarray, list, tuple, int)):
        return yearqtr(x)
    return as_yearqtr_default(x)


def as_yearqtr_dates(x: Any = None, *args: Any, **kwargs: Any) -> Any:
    raise _external_error("as.yearqtr", "dates")


def as_yearqtr_mondate(x: Any = None, *args: Any, **kwargs: Any) -> Any:
    raise _external_error("as.yearqtr", "mondate")


def as_yearqtr_timeDate(x: Any = None, *args: Any, **kwargs: Any) -> Any:
    raise _external_error("as.yearqtr", "timeDate")


def as_yearqtr_jul(x: Any = None, *args: Any, **kwargs: Any) -> Any:
    raise _external_error("as.yearqtr", "jul")


def as_yearqtr_ti(x: Any = None, *args: Any, **kwargs: Any) -> Any:
    raise _external_error("as.yearqtr", "ti")


def as_yearqtr_date_package(x: Any = None, *args: Any, **kwargs: Any) -> Any:
    raise _external_error("as.yearqtr", "date")


def sys_yearqtr() -> Yearqtr:
    """Quarter of the local calendar today."""
    today = dt.date.today()
    return as_yearqtr(dt.date(today.year, today.month, today.day))


def as_date_yearqtr(x: Any, frac: Any = 0, *args: Any, **kwargs: Any) -> RDate:
    """Date frac of the way through each quarter. 0 is the first day."""
    if isinstance(x, Yearqtr):
        values = x.value
    else:
        values = _plain_numeric(x)
    return as_date_from_year_fraction(values, frac=frac, end_offset=100)


def _paste_number(value: float) -> str:
    if not np.isfinite(value):
        if np.isnan(value):
            return "NA"
        return "Inf" if value > 0 else "-Inf"
    if value == math.floor(value) and abs(value) < 2**53:
        return str(int(value))
    return format(value, ".15g")


def _gsub_vec(pattern: str, replacement: np.ndarray, texts: list[str]) -> list[str]:
    out = []
    for i, text in enumerate(texts):
        repl = replacement[i] if i < replacement.size else np.nan
        if text is None or (isinstance(text, float) and math.isnan(text)):
            out.append("NA")
            continue
        if not np.isfinite(repl):
            out.append(text.replace(pattern, "NA"))
            continue
        out.append(text.replace(pattern, _paste_number(float(repl))))
    return out


def format_yearqtr(x: Any, format: Any = "%Y Q%q", *args: Any, **kwargs: Any) -> list[str | None]:
    if isinstance(format, (list, tuple)) and len(format) != 1:
        raise ValueError("the condition has length > 1")
    if isinstance(format, (list, tuple)):
        format = format[0]
    if not isinstance(format, str):
        raise ValueError("the condition has length > 1")
    coerced = as_yearqtr(x)
    if len(coerced) == 0:
        return []
    values = coerced.value
    year = np.floor(values + 0.001)
    qtr = np.floor(4.0 * (values - year) + 1.0 + 0.5 + 0.001)
    if format == "%Y Q%q":
        texts = [
            f"{_paste_number(float(year[i]))} Q{_paste_number(float(qtr[i]))}"
            for i in range(values.size)
        ]
    else:
        texts = [format] * values.size
        texts = _gsub_vec("%q", qtr, texts)
        texts = _gsub_vec("%Y", year, texts)
        yy = np.empty(values.size, dtype=np.float64)
        century = np.empty(values.size, dtype=np.float64)
        for i, item in enumerate(year):
            if not np.isfinite(item):
                yy[i] = np.nan
                century[i] = np.nan
                continue
            mod = item % 100.0
            yy[i] = float(math.trunc(mod))
            century[i] = math.floor(item / 100.0)
        yy_text = [f"{int(item):02d}" if np.isfinite(item) else "NA" for item in yy]
        # gsub of %y uses sprintf("%02d"), already zero padded, so replace literally.
        texts = [texts[i].replace("%y", yy_text[i]) for i in range(len(texts))]
        texts = _gsub_vec("%C", century, texts)
    names = coerced.names
    result: list[str | None] = []
    for i, text in enumerate(texts):
        if np.isnan(values[i]):
            result.append(None)
        else:
            result.append(text)
    if names is not None:
        # Names are kept on the object; the returned list is positional.
        pass
    return result


def as_character_yearqtr(x: Any, *args: Any, **kwargs: Any) -> list[str | None]:
    return format_yearqtr(x, *args, **kwargs)


def as_numeric_yearqtr(x: Any, *args: Any, **kwargs: Any) -> np.ndarray:
    if not isinstance(x, Yearqtr):
        x = as_yearqtr(x)
    return x.value.copy()


def c_yearqtr(*args: Any) -> Yearqtr:
    if not args:
        return Yearqtr(np.array([], dtype=np.float64))
    parts = [as_numeric(arg) for arg in args]
    return as_yearqtr(np.concatenate(parts))


def cycle_yearqtr(x: Any, *args: Any, **kwargs: Any) -> np.ndarray:
    values = as_numeric_yearqtr(x)
    return np.round(4.0 * np.remainder(values, 1.0)) + 1.0


def is_numeric_yearqtr(x: Any) -> bool:
    return False


def mean_yearqtr(x: Any, na_rm: bool = False, *args: Any, **kwargs: Any) -> Yearqtr:
    values = as_numeric_yearqtr(x)
    if na_rm:
        values = values[~np.isnan(values)]
    if values.size == 0:
        return yearqtr(np.array([np.nan]))
    return yearqtr(np.array([float(np.mean(values))]))


def _summary_values(args: tuple[Any, ...]) -> np.ndarray:
    parts = [as_numeric_yearqtr(arg) for arg in args]
    if not parts:
        return np.array([], dtype=np.float64)
    return np.concatenate(parts)


def min_yearqtr(*args: Any, na_rm: bool = False) -> Yearqtr:
    values = _summary_values(args)
    if na_rm:
        values = values[~np.isnan(values)]
    if values.size == 0 or np.any(np.isnan(values)):
        return Yearqtr(np.array([np.nan]))
    return Yearqtr(np.array([np.min(values)]))


def max_yearqtr(*args: Any, na_rm: bool = False) -> Yearqtr:
    values = _summary_values(args)
    if na_rm:
        values = values[~np.isnan(values)]
    if values.size == 0 or np.any(np.isnan(values)):
        return Yearqtr(np.array([np.nan]))
    return Yearqtr(np.array([np.max(values)]))


def sum_yearqtr(*args: Any, **kwargs: Any) -> Any:
    raise TypeError("sum not defined for yearqtr objects")


def range_yearqtr(*args: Any, na_rm: bool = False) -> Yearqtr:
    values = _summary_values(args)
    if not na_rm and np.any(np.isnan(values)):
        return yearqtr(np.array([np.nan, np.nan]))
    if na_rm:
        values = values[~np.isnan(values)]
    if values.size == 0:
        return yearqtr(np.array([np.inf, -np.inf]))
    return yearqtr(np.array([np.min(values), np.max(values)]))


def unique_yearqtr(x: Any, *args: Any, **kwargs: Any) -> Yearqtr:
    values = as_numeric_yearqtr(x)
    kept: list[float] = []
    seen_nan = False
    for value in values:
        if np.isnan(value):
            if not seen_nan:
                seen_nan = True
                kept.append(np.nan)
            continue
        if any(value == previous for previous in kept if not np.isnan(previous)):
            continue
        kept.append(float(value))
    if not kept:
        return Yearqtr(np.array([], dtype=np.float64))
    return as_yearqtr(np.asarray(kept, dtype=np.float64))


def diff_yearqtr(x: Any, lag: int = 1, differences: int = 1, *args: Any, **kwargs: Any) -> np.ndarray:
    values = as_numeric_yearqtr(x)
    out = values
    for _ in range(int(differences)):
        if out.size <= lag:
            return np.array([], dtype=np.float64)
        out = out[lag:] - out[:-lag]
    return np.asarray(out, dtype=np.float64)


def match_yearqtr(x: Any, table: Any, nomatch: Any = None, *args: Any, **kwargs: Any) -> list[Any]:
    left = np.floor(4.0 * as_numeric_yearqtr(as_yearqtr(x)) + 0.001)
    right = np.floor(4.0 * as_numeric_yearqtr(as_yearqtr(table)) + 0.001)
    found: list[Any] = []
    for value in left:
        if np.isnan(value):
            found.append(None)
            continue
        index = None
        for j, other in enumerate(right):
            if other == value:
                index = j + 1
                break
        found.append(nomatch if index is None else index)
    return found


def months_yearqtr(x: Any, abbreviate: bool = False, *args: Any, **kwargs: Any) -> list[str | None]:
    dates = as_date_yearqtr(x if isinstance(x, Yearqtr) else as_yearqtr(x))
    names = _MONTH_ABBR if abbreviate else _MONTH_FULL
    out: list[str | None] = []
    for day in dates.days:
        if not np.isfinite(day):
            out.append(None)
            continue
        _year, month, _day = civil_from_days(math.trunc(float(day)))
        out.append(names[month - 1])
    return out


def quarters_yearqtr(x: Any, abbreviate: bool = False, *args: Any, **kwargs: Any) -> list[str | None]:
    dates = as_date_yearqtr(x if isinstance(x, Yearqtr) else as_yearqtr(x))
    out: list[str | None] = []
    for day in dates.days:
        if not np.isfinite(day):
            out.append(None)
            continue
        _year, month, _day = civil_from_days(math.trunc(float(day)))
        out.append(f"Q{(month - 1) // 3 + 1}")
    return out


def print_yearqtr(x: Any) -> str:
    if not isinstance(x, Yearqtr):
        x = as_yearqtr(x)
    if len(x) == 0:
        return "yearqtr of length 0"
    return str(x)


def axis_yearqtr(*args: Any, **kwargs: Any) -> Any:
    raise NotImplementedError("axis.yearqtr is not translated")


def xtfrm_yearqtr(x: Any) -> np.ndarray:
    return as_numeric_yearqtr(x)
