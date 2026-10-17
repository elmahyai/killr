"""Pillar shafts: the formatted data of one column.

``new_pillar_shaft`` is the virtual constructor. ``new_pillar_shaft_simple``
truncates a finished character vector. ``pillar_shaft`` chooses a method
from the vector type. Numbers follow ``split_decimal``: significant digits,
a shared decimal column, and scientific notation when the decimal form is
wider than ``pillar.max_dec_width``.
"""

from __future__ import annotations

import math
from typing import Any

from lifecycle import LifecycleError, deprecate_stop

from pillar._color import grey_0_6, underline
from pillar._layout import defunct_message, ellipsis, option, str_trunc
from pillar._text import is_na, paste_atom
from pillar._vec import NULL, Factor, List
from pillar._width import display_extent
from pillar.extent import align, get_max_extent, new_ornament
from pillar.styles import style_na, style_neg, style_num, style_subtle, style_subtle_num
from pillar.summary import obj_sum

_EPS2 = 2 * 2.220446049250313e-16
_LOG10 = math.log(10)


class PillarShaft:
    """One shaft. ``classes[0]`` selects ``format``."""

    def __init__(
        self,
        data: Any,
        *,
        width: int | None,
        min_width: int | None,
        classes: list[str],
        attrs: dict[str, Any] | None = None,
    ):
        self.data = data
        self.width = width
        self.min_width = width if min_width is None else min_width
        self.classes = list(classes)
        self.attrs = dict(attrs or {})
        if "type" in self.attrs:
            self.type = self.attrs["type"]

    def format(self, width: Any = None, **_ignored: Any) -> Any:
        kind = self.classes[0] if self.classes else "pillar_shaft"
        if kind == "pillar_shaft_simple":
            return _format_simple(self, width)
        if kind == "pillar_shaft_decimal":
            return _format_decimal(self, width)
        if kind == "pillar_rif_shaft":
            return _format_rif(self, width)
        if kind == "pillar_continuation_shaft":
            return _format_continuation(self, width)
        if kind == "pillar_shaft":
            raise ValueError(
                "Please implement a format() method for class " + kind
            )
        raise ValueError("Please implement a format() method for class " + kind)


def _require_class(class_: Any) -> list[str]:
    if isinstance(class_, str):
        names = [class_]
    elif isinstance(class_, list) and class_ and all(isinstance(item, str) for item in class_):
        names = list(class_)
    else:
        raise ValueError("is.character(class) is not TRUE")
    if not names:
        raise ValueError("length(class) > 0 is not TRUE")
    return names


def _require_width(width: Any) -> int:
    if isinstance(width, bool) or not isinstance(width, (int, float)):
        raise ValueError("is_bare_numeric(width, 1) is not TRUE")
    if isinstance(width, float) and (math.isnan(width) or math.isinf(width)):
        raise ValueError("is_bare_numeric(width, 1) is not TRUE")
    return int(width)


def new_pillar_shaft(
    x: Any,
    *args: Any,
    width: Any = None,
    min_width: Any = None,
    type_sum: Any = None,
    class_: Any = None,
    subclass: Any = None,
    **attrs: Any,
) -> PillarShaft:
    """Build a shaft. ``class_`` is the subclass name, stored ahead of ``pillar_shaft``."""

    if args:
        raise TypeError("unused arguments")
    if subclass is not None:
        try:
            deprecate_stop("1.4.0", "pillar::new_pillar_shaft(subclass = )", "new_pillar_shaft(class = )")
        except LifecycleError:
            raise LifecycleError(
                defunct_message(
                    "1.4.0",
                    "pillar::new_pillar_shaft(subclass = )",
                    "new_pillar_shaft(class = )",
                )
            ) from None
    if class_ is None and "class" in attrs:
        class_ = attrs.pop("class")
    names = _require_class(class_)
    if width is None and min_width is None:
        raise ValueError("is_bare_numeric(width, 1) is not TRUE")
    stored = _require_width(width if width is not None else min_width)
    minimum = stored if min_width is None else _require_width(min_width)
    extra = dict(attrs)
    if type_sum is not None:
        from pillar.parts import new_pillar_type

        extra["type"] = new_pillar_type(type_sum)
    if "pillar_shaft" not in names:
        names = names + ["pillar_shaft"]
    return PillarShaft(x, width=stored, min_width=minimum, classes=names, attrs=extra)


def new_pillar_shaft_simple(
    formatted: Any,
    *args: Any,
    width: Any = None,
    align: str = "left",
    min_width: Any = None,
    na: Any = None,
    na_indent: int = 0,
    shorten: Any = None,
    short_formatted: Any = None,
    **kwargs: Any,
) -> PillarShaft:
    """A shaft whose text is already formatted and is cut with an ellipsis."""

    if args:
        raise TypeError("unused arguments")
    if isinstance(formatted, str) or is_na(formatted):
        items: list[Any] = [formatted]
    else:
        items = [None if is_na(item) else paste_atom(item) if not isinstance(item, str) else item for item in formatted]
    if width is None:
        width = get_max_extent(items) if items else 0
    if na is None:
        na = style_na("NA")
    if short_formatted is not None and min_width is None:
        shorts = short_formatted if isinstance(short_formatted, list) else [short_formatted]
        min_width = get_max_extent(shorts)
    # A missing shorten stays unset. An explicit value is matched later.
    return new_pillar_shaft(
        [items],
        width=width,
        min_width=min_width,
        align=align,
        na=na,
        na_indent=int(na_indent),
        shorten=shorten,
        short_formatted=short_formatted,
        class_="pillar_shaft_simple",
        **kwargs,
    )


def _format_simple(shaft: PillarShaft, width: Any) -> Any:
    if width is None:
        raise TypeError('argument "width" is missing, with no default')
    side = shaft.attrs.get("align", "left")
    shorten = shaft.attrs.get("shorten")
    short_formatted = shaft.attrs.get("short_formatted")
    desired = shaft.width if shaft.width is not None else 0
    rows = list(shaft.data[0])
    if width < desired:
        if short_formatted is None:
            rows = str_trunc(rows, width, shorten if shorten is not None else "back")
        else:
            shorts = list(short_formatted)
            for index, item in enumerate(rows):
                if not is_na(item) and display_extent(item) > width:
                    rows[index] = shorts[index]
    na = shaft.attrs.get("na", style_na("NA"))
    indent = int(shaft.attrs.get("na_indent") or 0)
    for index, item in enumerate(rows):
        if is_na(item):
            rows[index] = (" " * indent) + paste_atom(na)
    return new_ornament(rows, width=width, align=side)


def _values(x: Any) -> list[Any]:
    if x is NULL:
        return []
    if isinstance(x, List):
        return list(x.items)
    if isinstance(x, Factor):
        return list(x.values)
    if isinstance(x, (str, bool, int, float)) or x is None or is_na(x):
        return [x]
    if isinstance(x, (list, tuple)):
        return list(x)
    return [x]


def _kind(values: list[Any]) -> str:
    kinds: set[str] = set()
    for item in values:
        if item is None or is_na(item):
            continue
        if isinstance(item, bool):
            kinds.add("lgl")
        elif isinstance(item, int):
            kinds.add("int")
        elif isinstance(item, float):
            kinds.add("dbl")
        elif isinstance(item, str):
            kinds.add("chr")
        else:
            kinds.add("other")
    if not kinds or kinds == {"lgl"}:
        return "lgl"
    if "chr" in kinds:
        return "chr"
    if "dbl" in kinds or "int" in kinds:
        return "dbl" if "dbl" in kinds else "int"
    return "other"


def pillar_shaft(x: Any, **kwargs: Any) -> PillarShaft:
    """Turn a vector into a shaft. Unknown types are formatted and wrapped."""

    if isinstance(x, Factor):
        return pillar_shaft([None if is_na(item) else str(item) for item in x.values], **kwargs)
    from datetime import date, datetime

    if isinstance(x, datetime):
        return _shaft_posix([x], **kwargs)
    if isinstance(x, date):
        return _shaft_date([x], **kwargs)
    if isinstance(x, List):
        return _shaft_list(x.items, **kwargs)
    if isinstance(x, list) and x and isinstance(x[0], datetime):
        return _shaft_posix(x, **kwargs)
    if isinstance(x, list) and x and isinstance(x[0], date) and not isinstance(x[0], datetime):
        return _shaft_date(x, **kwargs)
    values = _values(x)
    kind = _kind(values)
    if kind == "lgl":
        return _shaft_logical(values)
    if kind in {"int", "dbl"}:
        return _shaft_numeric(values, kwargs.get("sigfig"))
    if kind == "chr":
        return _shaft_character(values, kwargs.get("min_width"))
    rendered = [paste_atom(item) for item in values]
    return pillar_shaft(rendered)


def _shaft_logical(values: list[Any]) -> PillarShaft:
    out: list[Any] = []
    for item in values:
        if item is None or is_na(item):
            out.append(None)
        elif item:
            out.append("TRUE")
        else:
            out.append("FALSE")
    return new_pillar_shaft_simple(out, width=5, align="left")


def _ambiguous(text: str) -> bool:
    return text == "" or text.startswith(" ") or text.endswith(" ") or "\\" in text or '"' in text


def _shaft_character(values: list[Any], min_width: Any) -> PillarShaft:
    texts = [None if item is None or is_na(item) else str(item) for item in values]
    needs = [index for index, item in enumerate(texts) if item is not None and _ambiguous(item)]
    na_indent = 0
    if needs:
        for index in needs:
            texts[index] = str(texts[index]).replace('"', '\\"')
        quote = style_subtle('"')
        for index, item in enumerate(texts):
            if item is not None:
                texts[index] = quote + item + quote
        na_indent = 1
    min_chars = min_width if min_width is not None else option("pillar.min_chars", 3)
    return _shaft_glue(texts, min_chars, na_indent, None)


def _shaft_glue(texts: list[Any], min_width: Any, na_indent: int, shorten: Any) -> PillarShaft:
    minimum = max(int(min_width) if min_width is not None else 3, 3)
    width = get_max_extent(texts) if texts else 0
    na = "<NA>" if _one_color() else style_na("NA")
    # Brackets only when color is off. style_na("NA") is the colored form.
    if not _one_color():
        na = style_na("NA")
    else:
        na = "<NA>"
    indent = na_indent if width > display_extent(paste_atom(na)) else 0
    return new_pillar_shaft_simple(
        texts,
        width=width,
        align="left",
        min_width=min(width, minimum) if width else minimum,
        na=na,
        na_indent=indent,
        shorten=shorten,
    )


def _one_color() -> bool:
    from cli.num_ansi_colors import num_ansi_colors

    return num_ansi_colors() <= 1


def _shaft_list(items: list[Any], **_kwargs: Any) -> PillarShaft:
    summary = [obj_sum(item) for item in items]
    formatted = ["<" + str(item) + ">" for item in summary]
    short = []
    for item, full in zip(summary, formatted):
        brief = getattr(item, "short", None)
        short.append("<" + brief + ">" if brief is not None else full)
    styled = style_subtle(formatted)
    short_styled = style_subtle(short)
    if isinstance(styled, str):
        styled = [styled]
    if isinstance(short_styled, str):
        short_styled = [short_styled]
    width = get_max_extent(styled) if styled else 0
    minimum = get_max_extent(short_styled) if short_styled else 0
    return new_pillar_shaft_simple(
        styled,
        width=width,
        align="left",
        min_width=minimum,
        short_formatted=short_styled,
    )


def _shaft_date(values: list[Any], **_kwargs: Any) -> PillarShaft:
    shown = []
    for item in values:
        if item is None or is_na(item):
            shown.append(None)
        else:
            shown.append(item.strftime("%Y-%m-%d"))
    return new_pillar_shaft_simple(shown, width=10, align="left")


def _shaft_posix(values: list[Any], **_kwargs: Any) -> PillarShaft:
    digits = int(option("digits.secs", 0) or 0)
    width = 19
    if digits > 0:
        width += min(digits, 6) + 1
    shown = []
    for item in values:
        if item is None or is_na(item):
            shown.append(None)
            continue
        date = item.strftime("%Y-%m-%d")
        time = item.strftime("%H:%M:%S")
        shown.append(date + " " + style_subtle(time))
    return new_pillar_shaft_simple(shown, width=width, align="left")


def _finite(value: Any) -> bool:
    if value is None or is_na(value) or isinstance(value, bool):
        return False
    if isinstance(value, (int, float)):
        return math.isfinite(float(value))
    return False


def _number(value: Any) -> float | None:
    if value is None or is_na(value):
        return None
    if isinstance(value, bool):
        return float(value)
    return float(value)


def _within(left: float, right: float) -> bool:
    if not math.isfinite(left) or not math.isfinite(right):
        return False
    if left == right:
        return True
    try:
        l2x = round(math.log2(left)) if left > 0 else None
        l2y = round(math.log2(right)) if right > 0 else None
    except ValueError:
        return False
    if l2x is None or l2y is None or l2x != l2y:
        return False
    return abs((left - right) * 2 ** (-l2x)) <= _EPS2


def _signif(value: float, digits: int) -> float:
    if value == 0 or not math.isfinite(value):
        return value
    power = math.floor(math.log10(abs(value)))
    scale = 10 ** (digits - 1 - power)
    return round(value * scale) / scale


def _rhs_digits(value: float | None, sigfig: int, offset: float = 0.0) -> int:
    if value is None or not math.isfinite(value):
        return 0
    if value == 0:
        exp = math.inf
    else:
        exp = math.floor(math.log10(abs(value)))
    if isinstance(value, float) and value == math.trunc(value) and offset == 0 and abs(value - math.trunc(value)) == 0 and float(value).is_integer():
        # Integers still grow rhs digits and then the loop strips them.
        pass
    digits = 0
    if exp <= sigfig:
        digits = sigfig - 1 - int(exp if math.isfinite(exp) else 0)
    while digits > 0:
        val = (value + offset) * 10 ** (digits - 1)
        if _within(val, round(val)):
            digits -= 1
        else:
            break
    return digits


def _lhs_token(value: float | None) -> str:
    if value is None:
        return "NA"
    if isinstance(value, float) and math.isnan(value):
        return "NaN"
    if value == math.inf or value == -math.inf:
        return "Inf"
    return str(int(math.trunc(abs(value))))


def _split(values: list[float | None], sigfig: int, sci: bool) -> dict[str, Any]:
    num = [_finite(item) for item in values]
    neg = []
    absolute = []
    for item in values:
        if item is None or (isinstance(item, float) and math.isnan(item)):
            neg.append(False)
            absolute.append(None)
        elif isinstance(item, float) and math.isinf(item):
            neg.append(item < 0)
            absolute.append(abs(item))
        elif isinstance(item, (int, float)) and math.isfinite(float(item)):
            neg.append(float(item) < 0)
            absolute.append(abs(float(item)))
        else:
            neg.append(False)
            absolute.append(None)
    mnt: list[float | None] = list(absolute)
    exp_display: list[int | None] = [None] * len(values)
    if sci:
        offset = math.log1p(-5 * 10 ** (-sigfig - 1)) / _LOG10
        exp: list[int | None] = [None] * len(values)
        for index, item in enumerate(mnt):
            if item is not None and item != 0 and math.isfinite(item):
                exp[index] = int(math.floor(math.log10(item) - offset))
                mnt[index] = 10 ** (math.log10(item) - exp[index])
        exp_display = list(exp)
    round_mnt: list[float | None] = []
    rhs_digits: list[int] = []
    for item in mnt:
        if item is None or not math.isfinite(item):
            round_mnt.append(None if item is None else item)
            rhs_digits.append(0)
            continue
        min_sig = int(math.floor(math.log10(abs(item)))) + 1 if item != 0 else 0
        rounded = _signif(float(item), max(sigfig, min_sig))
        round_mnt.append(rounded)
        rhs_digits.append(_rhs_digits(float(item), sigfig))
    dec = list(num)
    lhs_values: list[float | None] = []
    rhs_values: list[float | None] = []
    for index, rounded in enumerate(round_mnt):
        if rounded is None or (isinstance(rounded, float) and math.isnan(rounded)):
            lhs_values.append(None if rounded is None else float("nan"))
            rhs_values.append(0.0)
            dec[index] = False
            continue
        if isinstance(rounded, float) and math.isinf(rounded):
            lhs_values.append(rounded)
            rhs_values.append(0.0)
            dec[index] = False
            continue
        whole = math.trunc(rounded)
        frac = rounded - whole
        lhs_values.append(whole)
        rhs_values.append(frac)
        original = absolute[index]
        exponent = exp_display[index] or 0
        if original is None or original == 0 or (
            frac == 0 and _within(float(whole) * (10 ** exponent), float(original))
        ):
            dec[index] = False
    lhs = []
    for index, item in enumerate(lhs_values):
        raw = values[index]
        if raw is None:
            lhs.append("NA")
        elif isinstance(raw, float) and math.isnan(raw):
            lhs.append("NaN")
        elif isinstance(raw, float) and math.isinf(raw):
            lhs.append("Inf")
        else:
            lhs.append(_lhs_token(item))
    return {
        "sigfig": sigfig,
        "num": num,
        "neg": neg,
        "lhs": lhs,
        "lhs_zero": [item == 0 for item in lhs_values],
        "rhs": rhs_values,
        "rhs_digits": rhs_digits,
        "dec": dec,
        "exp": exp_display,
        "si": False,
        "width": 0,
    }


def _exp_digits(exp: list[int | None], si: bool) -> int:
    finite = [item for item in exp if item is not None]
    if si:
        return 1 if any(item != 0 for item in finite) else 0
    if not finite:
        return 0
    negative = 1 if any(item < 0 for item in finite) else 0
    logged = [2 + int(math.trunc(math.log10(abs(item) + 0.5))) for item in finite]
    span = max(0, max(logged))
    return negative + span


def _decimal_width(parts: dict[str, Any]) -> int:
    lhs_width = 0
    for flag, text in zip(parts["neg"], parts["lhs"]):
        lhs_width = max(lhs_width, int(bool(flag)) + len(text))
    fractional = max([0, *parts["rhs_digits"]])
    point = 1 if any(parts["dec"]) else 0
    return lhs_width + point + fractional + _exp_digits(parts["exp"], parts["si"])


def _underline_back(chars: list[str]) -> list[str]:
    length = len(chars)
    out = []
    for index, char in enumerate(chars):
        if math.trunc((index - length) / 3) % 2 == 1:
            out.append(underline(char))
        else:
            out.append(char)
    return out


def _underline_forward(chars: list[str]) -> list[str]:
    out = []
    for index, char in enumerate(chars):
        if math.trunc(index / 3) % 2 == 1:
            out.append(underline(char))
        else:
            out.append(char)
    return out


def _format_lhs_row(parts: dict[str, Any], index: int) -> str:
    if not parts["num"][index]:
        body = style_na(parts["lhs"][index])
    else:
        chars = _underline_back(list(parts["lhs"][index]))
        sig_n = min(len(chars), parts["sigfig"])
        sig = "".join(chars[:sig_n])
        rest = "".join(chars[sig_n:])
        zero = parts["lhs_zero"][index]
        body = style_num(sig, parts["neg"][index], not zero) + (
            style_subtle_num(rest, parts["neg"][index]) if rest else ""
        )
    sign = "-" if parts["neg"][index] else ""
    return sign + body


def _format_dec_row(parts: dict[str, Any], index: int) -> str:
    if not any(parts["dec"]):
        return ""
    if parts["dec"][index]:
        return style_num(".", parts["neg"][index], not parts["lhs_zero"][index])
    return " "


def _format_rhs_row(parts: dict[str, Any], index: int, rhs_width: int) -> str:
    if not parts["dec"][index]:
        text = ""
    else:
        digits = parts["rhs_digits"][index]
        frac = parts["rhs"][index] or 0.0
        raw = "" if digits <= 0 else f"{abs(round(frac * 10**digits)):.0f}"
        if raw == "0":
            raw = ""
        zeros = max(0, digits - len(raw))
        chars = _underline_forward(list(("0" * zeros) + raw))
        zero_part = "".join(chars[:zeros])
        num_part = "".join(chars[zeros:digits])
        text = style_num(zero_part, parts["neg"][index], not parts["lhs_zero"][index]) + style_num(
            num_part, parts["neg"][index]
        )
    if rhs_width <= 0:
        return text
    padded = align(text, width=rhs_width, align="left")
    return padded if isinstance(padded, str) else padded[0]


def _format_exp(exp: list[int | None]) -> list[str]:
    finite = [item is not None for item in exp]
    if not any(finite):
        return [""] * len(exp)
    negative = [bool(flag and item is not None and item < 0) for flag, item in zip(finite, exp)]
    if any(negative):
        signs = []
        for flag, item in zip(finite, exp):
            if not flag:
                signs.append(" ")
            elif item is not None and item < 0:
                signs.append("-")
            else:
                signs.append("+")
    else:
        signs = [""] * len(exp)
    digits = ["" if not flag or item is None else str(abs(item)) for flag, item in zip(finite, exp)]
    width = max((len(item) for item in digits), default=0)
    padded = [item.rjust(width) for item in digits]
    out = []
    for flag, sign, body, is_neg in zip(finite, signs, padded, negative):
        mark = style_subtle("e") if flag else " "
        out.append(mark + style_num(sign + body, is_neg))
    return out


def _assemble(parts: dict[str, Any]) -> list[str]:
    rhs_width = max([0, *parts["rhs_digits"]])
    exponents = _format_exp(parts["exp"]) if any(item is not None for item in parts["exp"]) else [""] * len(parts["lhs"])
    rows = []
    for index in range(len(parts["lhs"])):
        rows.append(
            _format_lhs_row(parts, index)
            + _format_dec_row(parts, index)
            + _format_rhs_row(parts, index, rhs_width)
            + exponents[index]
        )
    return rows


def _shaft_numeric(values: list[Any], sigfig: Any) -> PillarShaft:
    if sigfig is None:
        sigfig = option("pillar.sigfig", 3)
    sigfig = int(sigfig)
    if sigfig < 1:
        raise ValueError("Must show at least one significant figure")
    if sigfig > 15:
        raise ValueError("`sigfig` cannot be larger than 15.")
    numbers = [_number(item) for item in values]
    dec = _split(numbers, sigfig, sci=False)
    sci = _split(numbers, sigfig, sci=True)
    dec["width"] = _decimal_width(dec)
    sci["width"] = _decimal_width(sci)
    max_dec = int(option("pillar.max_dec_width", 13))
    if dec["width"] > max_dec:
        dec_part = None
    else:
        dec_part = dec
    chosen = dec_part if dec_part is not None else sci
    widths = [part["width"] for part in (dec_part, sci) if part is not None]
    return new_pillar_shaft(
        {"dec": dec_part, "sci": sci},
        width=chosen["width"],
        min_width=min(widths) if widths else 0,
        class_="pillar_shaft_decimal",
    )


def _format_decimal(shaft: PillarShaft, width: Any) -> Any:
    if width is None:
        raise TypeError('argument "width" is missing, with no default')
    dec = shaft.data["dec"]
    sci = shaft.data["sci"]
    if dec is None or width < dec["width"]:
        parts = sci
    else:
        parts = dec
    if not parts["num"] and not parts["lhs"]:
        return new_ornament([], width=width, align="right")
    if parts["lhs"] and width < shaft.min_width:
        raise ValueError(
            f"Need at least width {shaft.min_width}, requested {width}."
        )
    rows = _assemble(parts)
    used = get_max_extent(rows) if rows else 0
    pad = max(int(width) - used, 0)
    rows = [(" " * pad) + row for row in rows]
    return new_ornament(rows, width=width, align="right")


def _format_rif(shaft: PillarShaft, width: Any) -> Any:
    from pillar._color import grey_0_8

    ids = shaft.data["row_ids"]
    shown = []
    for item in ids:
        text = str(item)
        if width is not None and len(text) < int(width):
            text = " " * (int(width) - len(text)) + text
        shown.append(grey_0_8(text) if option("pillar.subtle", True) is True else text)
    return new_ornament(shown, width=width, align="right")


def new_empty_shaft(height: int = 1) -> PillarShaft:
    return new_pillar_shaft_simple([""] * height, width=0, align="left")


def new_continuation_shaft(parent: PillarShaft) -> PillarShaft:
    extra = display_extent(ellipsis()) + 1
    parent_width = parent.width or 0
    parent_min = parent.min_width if parent.min_width is not None else parent_width
    return new_pillar_shaft(
        [parent, extra],
        width=parent_width + extra,
        min_width=parent_min + extra,
        class_="pillar_continuation_shaft",
    )


def _format_continuation(shaft: PillarShaft, width: Any) -> Any:
    parent, extra = shaft.data
    parent_lines = parent.format(width=width - extra)
    rows = parent_lines.x if hasattr(parent_lines, "x") else parent_lines
    side = getattr(parent_lines, "align", "left")
    shown = [paste_atom(item) + " " + ellipsis() for item in rows]
    return new_ornament(shown, width=width, align=side)


def rif_shaft(n: int) -> PillarShaft:
    width = int(math.floor(math.log10(max(n, 1))) + 1)
    return new_pillar_shaft(
        {"row_ids": list(range(1, n + 1))},
        width=width,
        class_="pillar_rif_shaft",
    )
