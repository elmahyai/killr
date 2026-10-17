"""Pure-Python ports of htmlTable's small R-side helpers.

The JavaScript part of ``interactiveTable`` is intentionally not represented
here; this module only prepares the HTML fragments and script attributes.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Any, Iterable


def prepGroupCounts(x: Iterable[Any]) -> dict[str, list[Any]]:
    values = list(x)
    if not values:
        return {"n": [], "idx": [], "names": []}
    names: list[Any] = [values[0]]
    counts = [1]
    for value in values[1:]:
        equal = (value == names[-1]) if value is not None else names[-1] is None
        if equal:
            counts[-1] += 1
        else:
            names.append(value)
            counts.append(1)
    total = 0
    idx = []
    for count in counts:
        total += count
        idx.append(total)
    return {"n": counts, "idx": idx, "names": names}


def _roman(number: int) -> str:
    pairs = ((1000, "M"), (900, "CM"), (500, "D"), (400, "CD"),
             (100, "C"), (90, "XC"), (50, "L"), (40, "XL"),
             (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I"))
    result = []
    for value, glyph in pairs:
        quotient, number = divmod(number, value)
        result.append(glyph * quotient)
    return "".join(result)


def tblNoLast(roman: bool = False, table_counter: Any = None) -> Any:
    if table_counter is None or isinstance(table_counter, bool):
        raise ValueError("You cannot call the get last figure number when there has been no prior figure registered.")
    return _roman(int(table_counter)) if roman else table_counter


def tblNoNext(roman: bool = False, table_counter: Any = None) -> Any:
    if table_counter is False:
        raise ValueError("You cannot call the get last figure number when fig_cap_no is false.")
    next_no = (0 if table_counter is None or isinstance(table_counter, bool) else table_counter) + 1
    return _roman(int(next_no)) if roman else next_no


def vector2string(
    x: Iterable[Any], quotation_mark: str = "'", collapse: str | None = None
) -> str:
    if collapse is None:
        collapse = f"{quotation_mark}, {quotation_mark}"
    escaped = [str(value).replace(quotation_mark, "\\" + quotation_mark) for value in x]
    return quotation_mark + collapse.join(escaped) + quotation_mark


def txtInt(
    x: Any, language: str = "en", html: bool = True, **kwargs: Any
) -> Any:
    if isinstance(x, (list, tuple)):
        return [txtInt(value, language=language, html=True, **kwargs) for value in x]
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return ""
    value = float(x)
    digits = kwargs.get("digits")
    if language == "en":
        text = f"{value:,.{digits}f}" if digits is not None else f"{value:,.0f}"
    elif abs(value) >= 10**4:
        text = f"{value:,.{digits}f}" if digits is not None else f"{value:,.0f}"
        text = text.replace(",", "&nbsp;" if html else " ")
    else:
        text = f"{value:.{digits}f}" if digits is not None else f"{value:.0f}"
    return text


def txtPval(
    pvalues: Iterable[Any], lim_2dec: float = 10**-2,
    lim_sig: float = 10**-4, html: bool | str = True, **_: Any
) -> list[str]:
    less = "&lt; " if html is True else "< " if html is False else str(html)
    result = []
    for raw in pvalues:
        try:
            value = float(raw)
        except (TypeError, ValueError):
            result.append(str(raw))
            continue
        if value < lim_sig:
            result.append(less + f"{lim_sig:.{max(0, -int(math.floor(math.log10(lim_sig))))}f}")
        elif value > lim_2dec:
            decimals = max(0, -math.floor(math.log10(value)) + 1)
            result.append(f"{value:.{decimals}f}")
        else:
            result.append(f"{value:.{max(0, -int(math.floor(math.log10(value))))}f}")
    return result


def txtRound(
    x: Any, digits: int = 0, digits_nonzero: Any = math.nan,
    txt_NA: str = "", dec: str = ".", scientific: bool | None = None,
    txtInt_args: Any = None, **_: Any
) -> Any:
    if isinstance(x, (list, tuple)):
        ds = digits if isinstance(digits, (list, tuple)) else [digits] * len(x)
        return [txtRound(v, digits=d, digits_nonzero=digits_nonzero, txt_NA=txt_NA,
                         dec=dec, scientific=scientific, txtInt_args=txtInt_args)
                for v, d in zip(x, ds)]
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return txt_NA
    value = float(str(x).replace(dec, ".").replace(" ", "")) if isinstance(x, str) else float(x)
    if not (isinstance(digits_nonzero, float) and math.isnan(digits_nonzero)):
        position = math.floor(math.log10(abs(value))) if value else 0
        if position < -digits and position >= -int(digits_nonzero):
            digits = -position
    rounded = round(value, int(digits))
    if rounded == 0:
        rounded = 0
    if scientific:
        return f"{rounded:.{int(digits)}e}"
    text = f"{rounded:.{int(digits)}f}"
    if dec != ".":
        text = text.replace(".", dec)
    if txtInt_args is not None:
        # Keep the decimal portion from sprintf while applying txtInt to the
        # integer portion, matching the R helper's useful common case.
        integer, point, fraction = text.partition(dec)
        args = dict(txtInt_args) if isinstance(txtInt_args, dict) else {}
        integer = txtInt(int(integer), **args)
        text = integer + (point + fraction if point else "")
    return text


def txtMergeLines(*lines: Any, html: int | bool = 5) -> str:
    values: list[str] = []
    for item in lines:
        if isinstance(item, (list, tuple)):
            values.extend(str(value) for value in item)
        else:
            values.append(str(item))
    if not values:
        return ""
    if len(values) == 1:
        values = re.split(r"\n[ ]*", values[0])
    if len(values) == 1:
        return values[0]
    if html is not False:
        joiner = "<br>\n" if html == 5 else "<br />\n"
        return joiner.join(values)
    return r"\vbox{" + "".join(r"\hbox{\strut " + value + "}" for value in values) + "}"


def interactiveTable(
    x: str, txt_maxlen: int = 20, button: bool = False,
    minimized_columns: Any = None, js_scripts: Iterable[str] = ()
) -> dict[str, Any]:
    """Prepare R-side HTML and script attributes; JS runtime is not ported."""
    scripts = list(js_scripts)
    if button:
        scripts.append(f'/* htmlTable button runtime; txt.maxlen={txt_maxlen} */')
    else:
        scripts.append(f'/* htmlTable toggler runtime; txt.maxlen={txt_maxlen} */')
    return {"html": x, "javascript": scripts, "class": ["interactiveTable", "htmlTable"]}


def tidyHtmlTable(x: Any, value: Any = None, header: Any = None, **kwargs: Any) -> Any:
    """Minimal R-side mapping; full tidyverse data manipulation is routed."""
    if not isinstance(x, (list, tuple, dict)):
        raise TypeError("x must be of class data.frame")
    return x


__all__ = [
    "interactiveTable", "prepGroupCounts", "tblNoLast", "tblNoNext",
    "tidyHtmlTable", "txtInt", "txtMergeLines", "txtPval", "txtRound",
    "vector2string",
]
