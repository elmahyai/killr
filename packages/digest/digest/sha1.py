"""sha1(), sha1_attr_digest(), and sha1_digest() from digest 0.6.39.

Numbers are turned into the same text ``num2hex`` builds, attributes are copied
the way ``add_attributes`` does, and the result is hashed with ``digest``.
"""

from __future__ import annotations

import contextvars
import math
import re
import warnings
from datetime import datetime, timezone

import digest.hashing as hashing
import digest.serialize as ser
from digest.hashing import DigestError, digest, get_option
from digest.serialize import (
    NA,
    Obj,
    character,
    coerce,
    integer,
    logical,
    null,
    real,
    rlist,
    symbol,
)

_UNSET = object()
_DIGITS_HEX_FUDGE = 1e-10
_sym_table: contextvars.ContextVar = contextvars.ContextVar("digest_symbol_refs", default=None)


def _install_symbol_refs() -> None:
    """R writes a repeated symbol as ``255 | (index << 8)``.

    The shared serializer writes every symbol in full. ``names`` is repeated as
    soon as an object and a nested list both have a names attribute, so those
    hashes would not match. The index is 1-based in order of first appearance.
    """
    if getattr(ser._write_item, "_symbol_refs", False):
        return
    orig_write = ser._write_item
    orig_serialize = hashing.r_serialize

    def _write_item(obj, out):
        # The missing formal is MISSINGARG_SXP (251), not an empty symbol.
        if getattr(obj, "kind", None) == "missing":
            ser._i32(out, 251)
            return
        if getattr(obj, "kind", None) == "symbol":
            table = _sym_table.get()
            if table is not None:
                name = "" if obj.data is None else obj.data
                index = table.get(name)
                if index is None:
                    table[name] = len(table) + 1
                else:
                    ser._i32(out, 255 | (index << 8))
                    return
        return orig_write(obj, out)

    _write_item._symbol_refs = True

    def _serialize(value, version=2, ascii=False):
        token = _sym_table.set({})
        try:
            return orig_serialize(value, version=version, ascii=ascii)
        finally:
            _sym_table.reset(token)

    ser._write_item = _write_item
    hashing.r_serialize = _serialize


_install_symbol_refs()

_COMPONENT_NAMES = (
    "sec",
    "min",
    "hour",
    "mday",
    "mon",
    "year",
    "wday",
    "yday",
    "isdst",
    "zone",
    "gmtoff",
)


class _KeepNumeric:
    """num2hex returned the original numbers because every value was missing."""

    def __init__(self, data: list) -> None:
        self.data = data


def num2hex(x, digits: int = 14, zapsmall: int = 7):
    """Match ``digest:::num2hex``. All-missing input comes back numeric."""
    values = _numeric_values(x)
    digits = _coerce_count(digits, "digits")
    zapsmall = _coerce_count(zapsmall, "zapsmall")
    if len(values) == 0:
        return []
    if all(_is_missing(value) for value in values):
        return _KeepNumeric(list(values))
    threshold = _zap_threshold(zapsmall)
    output: list = [NA] * len(values)
    finite: list[int] = []
    for index, value in enumerate(values):
        if _is_missing(value):
            continue
        number = float(value)
        if math.isinf(number):
            output[index] = "Inf" if number > 0 else "-Inf"
            continue
        if abs(number) <= threshold:
            output[index] = "0"
            continue
        finite.append(index)
    if not finite:
        return output
    digits_hex = _digits_hex(digits)
    for index in finite:
        number = float(values[index])
        magnitude = abs(number)
        exponent = _floor_log2(magnitude)
        scaled = math.ldexp(magnitude, -exponent)
        text = _r_hex_float(scaled)
        start = 5 if text.startswith("0x1.") else 4
        stop = min(len(text) - 3, start + digits_hex - 1)
        mantissa = re.sub(r"0*$", "", _substring(text, start, stop))
        sign = "-" if number < 0 else ""
        output[index] = f"{sign}{mantissa} {exponent}"
    return output


def sha1(x, digits=_UNSET, zapsmall=_UNSET, algo: str = "sha1", **kwargs):
    """Hash ``x`` with the S3 method ``sha1`` would choose."""
    obj = _prepare(x)
    method = _resolve(obj)
    if digits is _UNSET:
        digits = 4 if method is _sha1_anova else 14
    if zapsmall is _UNSET:
        zapsmall = 7
    digits = _coerce_count(digits, "digits")
    zapsmall = _coerce_count(zapsmall, "zapsmall")
    return method(obj, digits, zapsmall, algo, kwargs)


def sha1_attr_digest(x, digits: int = 14, zapsmall: int = 7, algo: str = "sha1", **kwargs):
    """Attach ``digest::sha1`` and hash the object."""
    return _sha1_attr_digest(
        _prepare(x),
        _coerce_count(digits, "digits"),
        _coerce_count(zapsmall, "zapsmall"),
        algo,
        kwargs,
    )


def sha1_digest(x, digits: int = 14, zapsmall: int = 7, algo: str = "sha1", **kwargs):
    """Hash ``x`` without attaching an attribute. ``digits`` is unused, as in R."""
    del digits, zapsmall, kwargs
    return digest(_prepare(x), algo=algo)


def _sha1_numeric(x: Obj, digits: int, zapsmall: int, algo: str, kwargs: dict):
    converted = num2hex(x.data, digits, zapsmall)
    if isinstance(converted, _KeepNumeric):
        y = _clone(x)
    else:
        y = character(converted)
    y = add_attributes(x, y)
    y.attributes.append(("digest::sha1", _attr_sha1(x, digits, zapsmall, algo, kwargs)))
    return digest(y, algo=algo)


def _sha1_matrix(x: Obj, digits: int, zapsmall: int, algo: str, kwargs: dict):
    if x.kind != "real":
        return _sha1_attr_digest(x, digits, zapsmall, algo, kwargs)
    y = _hex_matrix(x, digits, zapsmall)
    y = add_attributes(x, y)
    y.attributes.append(("digest::sha1", _attr_sha1(x, digits, zapsmall, algo, kwargs)))
    return digest(y, algo=algo)


def _sha1_complex(x: Obj, digits: int, zapsmall: int, algo: str, kwargs: dict):
    pairs = [_pair(value) for value in x.data]
    dim = _attr(x, "dim")
    if dim is not None and dim.kind == "integer" and len(dim.data) == 2:
        nrow = int(dim.data[0])
        ncol = int(dim.data[1]) * 2
        real_parts = [_part(pair[0]) for pair in pairs]
        imag_parts = [_part(pair[1]) for pair in pairs]
        flat = real_parts + imag_parts
    else:
        nrow = len(pairs)
        ncol = 2
        flat = [_part(pair[0]) for pair in pairs] + [_part(pair[1]) for pair in pairs]
    y = Obj("real", flat, [("dim", integer([nrow, ncol]))])
    y = add_attributes(x, y)
    y.attributes.append(("digest::sha1", _attr_sha1(x, digits, zapsmall, algo, kwargs)))
    return sha1(y, digits=digits, zapsmall=zapsmall, algo=algo, **kwargs)


def _sha1_date(x: Obj, digits: int, zapsmall: int, algo: str, kwargs: dict):
    y = Obj("real", list(x.data), [])
    y = add_attributes(x, y)
    y.attributes.append(("digest::sha1", _attr_sha1(x, digits, zapsmall, algo, kwargs)))
    return sha1(y, digits=digits, zapsmall=zapsmall, algo=algo, **kwargs)


def _sha1_array(x: Obj, digits: int, zapsmall: int, algo: str, kwargs: dict):
    dim = _attr(x, "dim")
    y = rlist([dim, real(_as_double_list(x))], names=["dimension", "value"])
    y = add_attributes(x, y)
    y.attributes.append(("digest::sha1", _attr_sha1(x, digits, zapsmall, algo, kwargs)))
    return sha1(y, digits=digits, zapsmall=zapsmall, algo=algo, **kwargs)


def _sha1_data_frame(x: Obj, digits: int, zapsmall: int, algo: str, kwargs: dict):
    if len(x.data) == 0:
        y = _clone(x)
    else:
        hashes = [
            sha1(column, digits=digits, zapsmall=zapsmall, algo=algo, **kwargs)
            for column in x.data
        ]
        y = character(hashes)
        names = _attr(x, "names")
        if names is not None:
            y.attributes.append(("names", names))
    y = add_attributes(x, y)
    y.attributes.append(("digest::sha1", _attr_sha1(x, digits, zapsmall, algo, kwargs)))
    return digest(y, algo=algo)


def _sha1_list(x: Obj, digits: int, zapsmall: int, algo: str, kwargs: dict):
    if len(x.data) == 0:
        y = _clone(x)
    else:
        hashes = [
            sha1(item, digits=digits, zapsmall=zapsmall, algo=algo, **kwargs)
            for item in x.data
        ]
        y = character(hashes)
        names = _attr(x, "names")
        if names is not None:
            y.attributes.append(("names", names))
    y = add_attributes(x, y)
    y.attributes.append(("digest::sha1", _list_meta(x, digits, zapsmall, kwargs)))
    return digest(y, algo=algo)


def _sha1_posixlt(x: Obj, digits: int, zapsmall: int, algo: str, kwargs: dict):
    names = _character_values(_attr(x, "names")) or list(_COMPONENT_NAMES)
    columns = [_unlist(item) for item in x.data]
    sec_at = names.index("sec") if "sec" in names else 0
    converted = num2hex(columns[sec_at].data, digits, zapsmall)
    if isinstance(converted, _KeepNumeric):
        columns[sec_at] = real(converted.data)
    else:
        columns[sec_at] = character(converted)
    nrow = len(columns[0].data) if columns else 0
    y = Obj(
        "list",
        columns,
        [
            ("names", character(names)),
            ("row.names", integer(list(range(1, nrow + 1)))),
            ("class", character(["data.frame"])),
        ],
        object_bit=True,
    )
    y = add_attributes(x, y)
    y.attributes.append(("digest::sha1", _attr_sha1(x, digits, zapsmall, algo, kwargs)))
    return digest(y, algo=algo)


def _sha1_posixct(x: Obj, digits: int, zapsmall: int, algo: str, kwargs: dict):
    hashed = sha1(_posixct_as_lt(x), digits=digits, zapsmall=zapsmall, algo=algo, **kwargs)
    y = character([hashed])
    y = add_attributes(x, y)
    y.attributes.append(("digest::sha1", _attr_sha1(x, digits, zapsmall, algo, kwargs)))
    return digest(y, algo=algo)


def _sha1_anova(x: Obj, digits: int, zapsmall: int, algo: str, kwargs: dict):
    if digits > 4:
        warnings.warn(
            "Hash on 32 bit might be different from hash on 64 bit with digits > 4",
            stacklevel=3,
        )
    y = _anova_apply(x, digits, zapsmall)
    y = add_attributes(x, y)
    y.attributes.append(("digest::sha1", _attr_sha1(x, digits, zapsmall, algo, kwargs)))
    return digest(y, algo=algo)


def _sha1_pairlist(x: Obj, digits: int, zapsmall: int, algo: str, kwargs: dict):
    items, names = _pairlist_contents(x)
    hashes = [sha1(item, digits=digits, zapsmall=zapsmall, algo=algo, **kwargs) for item in items]
    y = character(hashes)
    if names is not None:
        y.attributes.append(("names", names if isinstance(names, Obj) else character(names)))
    y = add_attributes(x, y)
    y.attributes.append(("digest::sha1", _attr_sha1(x, digits, zapsmall, algo, kwargs)))
    return digest(y, algo=algo)


def _sha1_function(x: Obj, digits: int, zapsmall: int, algo: str, kwargs: dict):
    dots = dict(kwargs)
    if dots.get("environment", None) is None:
        dots["environment"] = True
    include_env = _is_true(dots["environment"])
    payload = x.data if isinstance(x.data, dict) else {}
    parts = [
        ("formals", payload.get("formals", Obj("pairlist", []))),
        ("body", _as_character_language(payload.get("body", character([])))),
    ]
    if include_env:
        env = payload.get("environment", Obj("globalenv"))
        parts.append(("environment", character([digest(env, algo=algo)])))
    child = {
        "environment": dots["environment"],
        "...": _named_list([(key, _coerce_value(value)) for key, value in dots.items()]),
    }
    hashes = [
        sha1(part, digits=digits, zapsmall=zapsmall, algo=algo, **child) for _, part in parts
    ]
    y = character(hashes)
    y.attributes.append(("names", character([name for name, _ in parts])))
    y = add_attributes(x, y)
    y.attributes.append(
        (
            "digest::sha1",
            _attr_sha1_extra(y, digits, zapsmall, algo, _named_list(
                [(key, _coerce_value(value)) for key, value in dots.items()]
            )),
        )
    )
    return digest(y, algo=algo)


def _sha1_formula(x: Obj, digits: int, zapsmall: int, algo: str, kwargs: dict):
    dots = dict(kwargs)
    if dots.get("environment", None) is None:
        dots["environment"] = True
    elements = list(x.data) if isinstance(x.data, list) else _language_elements(x)
    child = {"...": _named_list([(key, _coerce_value(value)) for key, value in dots.items()])}
    hashes = [
        sha1(element, digits=digits, zapsmall=zapsmall, algo=algo, **child) for element in elements
    ]
    if _is_true(dots["environment"]):
        env = _attr(x, ".Environment")
        if env is None:
            env = Obj("globalenv")
        hashes.append(digest(env, algo=algo))
    y = character(hashes)
    y = add_attributes(x, y)
    y.attributes.append(("digest::sha1", _attr_sha1(x, digits, zapsmall, algo, kwargs)))
    return digest(y, algo=algo)


def _sha1_attr_digest(x: Obj, digits: int, zapsmall: int, algo: str, kwargs: dict):
    y = _clone(x)
    y.attributes.append(("digest::sha1", _attr_sha1(x, digits, zapsmall, algo, kwargs)))
    return digest(y, algo=algo)


def _sha1_digest(x: Obj, digits: int, zapsmall: int, algo: str, kwargs: dict):
    del digits, zapsmall, kwargs
    return digest(x, algo=algo)


def _sha1_default(x: Obj, digits: int, zapsmall: int, algo: str, kwargs: dict):
    if x.kind == "list":
        return _sha1_list(x, digits, zapsmall, algo, kwargs)
    label = "', '".join(_classes(x))
    warnings.warn(
        "sha1() has no method for the '"
        + label
        + "' class, so using fallback.\nPlease read the note in ?digest::sha1"
        "on why this might be a problem.",
        stacklevel=3,
    )
    return _sha1_attr_digest(x, digits, zapsmall, algo, kwargs)


def add_attributes(x: Obj, y: Obj) -> Obj:
    """Copy attributes from ``x`` onto ``y``, dropping ``srcref`` at version 0.6.23.2."""
    y = _clone(y)
    version = str(get_option("sha1PackageVersion"))
    if _version_lt(version, (0, 6, 22, 2)):
        return y
    extra = list(x.attributes)
    if not _version_lt(version, (0, 6, 23, 2)):
        extra = [(name, value) for name, value in extra if name != "srcref"]
    attrs = list(y.attributes)
    for name, value in extra:
        if isinstance(value, Obj) and value.kind == "null":
            continue
        value = _expand_row_names(name, value)
        pasted = f"digest::attributes.{name}" if name else "digest::attributes"
        attrs.append((pasted, value))
    y.attributes = attrs
    return y


def _attr_sha1(x: Obj, digits: int, zapsmall: int, algo: str, kwargs: dict) -> Obj:
    pairs = [
        ("class", character(_classes(x))),
        ("digits", integer([digits])),
        ("zapsmall", integer([zapsmall])),
    ]
    if algo != "sha1":
        pairs.append(("algo", character([algo])))
    for key, value in kwargs.items():
        pairs.append((key, value if isinstance(value, Obj) else _coerce_value(value)))
    return _named_list(pairs)


def _attr_sha1_extra(x: Obj, digits: int, zapsmall: int, algo: str, extra: Obj) -> Obj:
    """``attr_sha1(..., dots)`` puts one unnamed element after the fixed fields."""
    pairs = [
        ("class", character(_classes(x))),
        ("digits", integer([digits])),
        ("zapsmall", integer([zapsmall])),
    ]
    if algo != "sha1":
        pairs.append(("algo", character([algo])))
    pairs.append(("", extra))
    return _named_list(pairs)


def _list_meta(x: Obj, digits: int, zapsmall: int, kwargs: dict) -> Obj:
    """sha1.list stores dots beside class, and never stores algo."""
    pairs = [
        ("class", character(_classes(x))),
        ("digits", integer([digits])),
        ("zapsmall", integer([zapsmall])),
    ]
    for key, value in kwargs.items():
        pairs.append((key, value if isinstance(value, Obj) else _coerce_value(value)))
    return _named_list(pairs)


def _resolve(obj: Obj):
    table = {
        "numeric": _sha1_numeric,
        "matrix": _sha1_matrix,
        "complex": _sha1_complex,
        "Date": _sha1_date,
        "array": _sha1_array,
        "data.frame": _sha1_data_frame,
        "list": _sha1_list,
        "POSIXlt": _sha1_posixlt,
        "POSIXct": _sha1_posixct,
        "anova": _sha1_anova,
        "pairlist": _sha1_pairlist,
        "function": _sha1_function,
        "formula": _sha1_formula,
        "(": _sha1_formula,
        "call": _sha1_attr_digest,
        "character": _sha1_attr_digest,
        "factor": _sha1_attr_digest,
        "integer": _sha1_attr_digest,
        "logical": _sha1_attr_digest,
        "raw": _sha1_attr_digest,
        "environment": _sha1_attr_digest,
        "<-": _sha1_attr_digest,
        "name": _sha1_digest,
        "NULL": _sha1_digest,
    }
    for name in _classes(obj):
        method = table.get(name)
        if method is not None:
            return method
    if obj.kind == "list":
        return _sha1_list
    return _sha1_default


def _classes(obj: Obj) -> list[str]:
    klass = _attr(obj, "class")
    if klass is not None and klass.kind == "string" and klass.data:
        return ["NA" if value is NA else str(value) for value in klass.data]
    dim = _attr(obj, "dim")
    if dim is not None and getattr(dim, "data", None):
        if len(dim.data) == 2:
            return ["matrix", "array"]
        return ["array"]
    implicit = {
        "real": "numeric",
        "integer": "integer",
        "logical": "logical",
        "string": "character",
        "complex": "complex",
        "raw": "raw",
        "list": "list",
        "null": "NULL",
        "symbol": "name",
        "pairlist": "pairlist",
        "lang": "call",
        "globalenv": "environment",
        "emptyenv": "environment",
        "baseenv": "environment",
        "function": "function",
        "closure": "function",
        "missing": "name",
    }
    return [implicit.get(obj.kind, obj.kind)]


def _prepare(value) -> Obj:
    if isinstance(value, Obj):
        return value
    return coerce(value)


def _clone(obj: Obj) -> Obj:
    data = obj.data
    if isinstance(data, list):
        data = list(data)
    elif isinstance(data, dict):
        data = dict(data)
    return Obj(
        obj.kind,
        data,
        list(obj.attributes),
        obj.object_bit,
        obj.tag,
        obj.car,
        obj.cdr,
    )


def _attr(obj: Obj, name: str):
    for key, value in obj.attributes:
        if key == name:
            return value
    return None


def _named_list(pairs: list[tuple[str, Obj]]) -> Obj:
    return Obj(
        "list",
        [value for _, value in pairs],
        [("names", character([name for name, _ in pairs]))],
    )


def _coerce_value(value):
    if isinstance(value, Obj):
        return value
    if isinstance(value, dict):
        return _named_list([(str(key), _coerce_value(item)) for key, item in value.items()])
    return coerce(value)


def _expand_row_names(name: str, value):
    """attributes() expands the compact row-name vector c(NA, -n)."""
    if name != "row.names" or not isinstance(value, Obj) or value.kind != "integer":
        return value
    data = value.data
    if (
        len(data) == 2
        and data[0] is NA
        and isinstance(data[1], int)
        and not isinstance(data[1], bool)
        and data[1] < 0
    ):
        return integer(list(range(1, -data[1] + 1)))
    return value


def _version_lt(text: str, target: tuple[int, ...]) -> bool:
    parts = tuple(int(piece) for piece in str(text).split(".") if piece != "")
    width = max(len(parts), len(target))
    left = parts + (0,) * (width - len(parts))
    right = target + (0,) * (width - len(target))
    return left < right


def _coerce_count(value, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise DigestError(f"{name} is not integer")
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value) or not _counts_as_integer(value):
            raise DigestError(f"{name} is not integer")
        value = int(math.trunc(value))
    if isinstance(value, (list, tuple)):
        raise DigestError(f"{name} must contain exactly one integer")
    if value < 1:
        raise DigestError(f"{name} must be positive")
    if value > 2_147_483_647:
        raise DigestError(f"{name} is not integer")
    return int(value)


def _counts_as_integer(value: float) -> bool:
    """all.equal(as.integer(x), x) for one finite double."""
    truncated = math.trunc(value)
    if truncated == value:
        return True
    tolerance = math.sqrt(2.220446049250313e-16)
    scale = max(abs(float(truncated)), abs(value))
    return abs(truncated - value) <= tolerance * scale


def _numeric_values(x) -> list:
    if isinstance(x, Obj):
        if x.kind not in ("real", "integer"):
            raise DigestError("x is not numeric")
        return list(x.data)
    if isinstance(x, bool) or x is NA:
        raise DigestError("x is not numeric")
    if isinstance(x, (int, float)):
        return [x]
    if isinstance(x, (list, tuple)):
        values = list(x)
        if any(isinstance(value, bool) for value in values):
            raise DigestError("x is not numeric")
        return values
    raise DigestError("x is not numeric")


def _is_missing(value) -> bool:
    if value is NA or value is None:
        return True
    return isinstance(value, float) and math.isnan(value)


def _floor_log2(value: float) -> int:
    _, exponent = math.frexp(value)
    return exponent - 1


def _zap_threshold(zapsmall: int) -> float:
    tiny = 10.0 ** (-int(zapsmall))
    if tiny == 0.0:
        return 0.0
    if math.isinf(tiny):
        return math.inf
    return math.ldexp(1.0, _floor_log2(tiny))


def _digits_hex(digits: int) -> int:
    value = math.log(10.0 ** digits) / math.log(16.0)
    return math.ceil(value - _DIGITS_HEX_FUDGE)


def _r_hex_float(value: float) -> str:
    """R's sprintf("%a") for a finite double."""
    sign = "-" if math.copysign(1.0, value) < 0.0 else ""
    magnitude = abs(value)
    if magnitude == 0.0:
        return f"{sign}0x0p+0"
    body = magnitude.hex()[2:]
    mantissa, exponent = body.split("p")
    if "." in mantissa:
        whole, fraction = mantissa.split(".")
        fraction = fraction.rstrip("0")
        mantissa = whole if fraction == "" else f"{whole}.{fraction}"
    power = int(exponent)
    power_text = f"+{power}" if power >= 0 else str(power)
    return f"{sign}0x{mantissa}p{power_text}"


def _substring(text: str, start: int, stop: int) -> str:
    """R substring, 1-based and inclusive. A backwards range is empty."""
    if start > stop or start > len(text) or start < 1:
        return ""
    return text[start - 1 : stop]


def _shape(obj: Obj) -> tuple[int, int]:
    dim = _attr(obj, "dim")
    if dim is None or not dim.data:
        length = len(obj.data)
        return length, 1 if length else 0
    return int(dim.data[0]), int(dim.data[1])


def _hex_matrix(x: Obj, digits: int, zapsmall: int) -> Obj:
    nrow, ncol = _shape(x)
    if nrow == 0 or ncol == 0:
        y = character([])
        y.attributes = [("dim", integer([nrow, ncol]))]
        return y
    converted = []
    for column in range(ncol):
        piece = list(x.data[column * nrow : (column + 1) * nrow])
        converted.append(num2hex(piece, digits, zapsmall))
    if all(isinstance(column, _KeepNumeric) for column in converted):
        return Obj("real", list(x.data), [("dim", integer([nrow, ncol]))])
    flat: list = []
    for column in converted:
        if isinstance(column, _KeepNumeric):
            flat.extend(_as_character_numeric(column.data))
        else:
            flat.extend(column)
    y = character(flat)
    y.attributes = [("dim", integer([nrow, ncol]))]
    return y


def _anova_apply(x: Obj, digits: int, zapsmall: int) -> Obj:
    columns = [_as_double_list(column) for column in x.data]
    nrow = _frame_rows(x, columns)
    ncol = len(columns)
    if ncol == 0 or nrow == 0:
        return character([])
    rows = []
    for row in range(nrow):
        rows.append(num2hex([column[row] for column in columns], digits, zapsmall))
    if all(isinstance(row, _KeepNumeric) for row in rows):
        flat: list = []
        for row in rows:
            flat.extend(row.data)
        if ncol == 1:
            return real(flat)
        return Obj("real", flat, [("dim", integer([ncol, nrow]))])
    flat = []
    for row in rows:
        if isinstance(row, _KeepNumeric):
            flat.extend(_as_character_numeric(row.data))
        else:
            flat.extend(row)
    if ncol == 1:
        return character(flat)
    y = character(flat)
    y.attributes = [("dim", integer([ncol, nrow]))]
    return y


def _frame_rows(obj: Obj, columns: list) -> int:
    row_names = _attr(obj, "row.names")
    if isinstance(row_names, Obj) and row_names.kind == "integer" and len(row_names.data) == 2:
        first, second = row_names.data
        if first is NA and isinstance(second, int) and second < 0:
            return -second
    if isinstance(row_names, Obj) and row_names.data is not None and row_names.kind != "null":
        return len(row_names.data)
    if columns:
        return len(columns[0])
    return 0


def _as_double_list(obj: Obj) -> list:
    if obj.kind == "real":
        return list(obj.data)
    if obj.kind == "integer":
        return [NA if value is NA else float(value) for value in obj.data]
    if obj.kind == "logical":
        return [NA if value is NA else (1.0 if value else 0.0) for value in obj.data]
    raise DigestError("x is not numeric")


def _as_character_numeric(values: list) -> list:
    output = []
    for value in values:
        if _is_missing(value):
            output.append(NA)
        elif isinstance(value, float) and math.isinf(value):
            output.append("Inf" if value > 0 else "-Inf")
        else:
            output.append(_format_double(float(value)))
    return output


def _format_double(value: float) -> str:
    """as.character for a finite double: 15 significant digits, R's exponent style."""
    if value == 0.0:
        return "0"
    text = format(abs(value), ".15g")
    if "e" in text:
        mantissa, exponent = text.split("e")
        exponent = int(exponent)
        text = f"{mantissa}e{exponent:+03d}"
    if value < 0:
        return "-" + text
    return text


def _pair(value):
    if isinstance(value, tuple) and len(value) == 2:
        return value
    raise DigestError("x is not numeric")


def _part(value):
    if value is NA or value is None:
        return NA
    if isinstance(value, float) and math.isnan(value):
        return NA
    return float(value)


def _character_values(obj) -> list[str] | None:
    if not isinstance(obj, Obj) or obj.kind != "string":
        return None
    return ["" if value is NA else str(value) for value in obj.data]


def _unlist(item) -> Obj:
    item = item if isinstance(item, Obj) else _prepare(item)
    if item.kind == "list" and item.data:
        return _unlist(item.data[0])
    return item


def _posixct_as_lt(x: Obj) -> Obj:
    tzone = _attr(x, "tzone")
    zone = "UTC"
    if tzone is not None and tzone.kind == "string" and tzone.data:
        text = tzone.data[0]
        if text not in (NA, None, "", "UTC", "GMT"):
            zone = str(text)
        elif text in ("UTC", "GMT"):
            zone = str(text)
    seconds = []
    minutes = []
    hours = []
    mdays = []
    months = []
    years = []
    wdays = []
    ydays = []
    isdst = []
    zones = []
    offsets = []
    for value in x.data:
        parts = _utc_parts(value, zone)
        if parts is None:
            seconds.append(NA)
            minutes.append(NA)
            hours.append(NA)
            mdays.append(NA)
            months.append(NA)
            years.append(NA)
            wdays.append(NA)
            ydays.append(NA)
            isdst.append(NA)
            zones.append(NA)
            offsets.append(NA)
            continue
        seconds.append(parts[0])
        minutes.append(parts[1])
        hours.append(parts[2])
        mdays.append(parts[3])
        months.append(parts[4])
        years.append(parts[5])
        wdays.append(parts[6])
        ydays.append(parts[7])
        isdst.append(parts[8])
        zones.append(parts[9])
        offsets.append(parts[10])
    columns = [
        real(seconds),
        integer(minutes),
        integer(hours),
        integer(mdays),
        integer(months),
        integer(years),
        integer(wdays),
        integer(ydays),
        integer(isdst),
        character(zones),
        integer(offsets),
    ]
    tzone_value = tzone if tzone is not None else character([zone])
    return Obj(
        "list",
        columns,
        [
            ("names", character(list(_COMPONENT_NAMES))),
            ("class", character(["POSIXlt", "POSIXt"])),
            ("tzone", tzone_value),
            ("balanced", logical([True])),
        ],
        object_bit=True,
    )


def _utc_parts(value, zone: str):
    if _is_missing(value):
        return None
    if zone not in ("UTC", "GMT"):
        raise DigestError("sha1.POSIXct only converts the UTC and GMT zones")
    stamp = float(value)
    whole = math.floor(stamp)
    fraction = stamp - whole
    when = datetime.fromtimestamp(whole, timezone.utc)
    second = when.second + fraction
    return (
        second,
        when.minute,
        when.hour,
        when.day,
        when.month - 1,
        when.year - 1900,
        (when.weekday() + 1) % 7,
        when.timetuple().tm_yday - 1,
        0,
        zone,
        0,
    )


def _pairlist_contents(obj: Obj):
    names = _attr(obj, "names")
    if isinstance(obj.data, list):
        return list(obj.data), names
    items = []
    tags = []
    node = obj
    while isinstance(node, Obj) and node.kind == "pairlist":
        items.append(node.car if node.car is not None else null())
        tags.append("" if node.tag is None else node.tag)
        node = node.cdr
        if isinstance(node, Obj) and node.kind == "null":
            break
    if names is None and any(tags):
        names = character(tags)
    return items, names


def _language_elements(obj: Obj) -> list:
    if isinstance(obj.data, list):
        return list(obj.data)
    elements = []
    if obj.car is not None:
        elements.append(obj.car)
    node = obj.cdr
    while isinstance(node, Obj) and node.kind == "pairlist":
        elements.append(node.car)
        node = node.cdr
        if isinstance(node, Obj) and node.kind == "null":
            break
    return elements


def _as_character_language(obj) -> Obj:
    if not isinstance(obj, Obj):
        return character([str(obj)])
    if obj.kind == "string":
        return obj
    if obj.kind == "symbol":
        return character(["" if obj.data is None else str(obj.data)])
    if obj.kind != "lang":
        return character([_piece_text(obj)])
    parts = [_piece_text(obj.car)]
    node = obj.cdr
    while isinstance(node, Obj) and node.kind == "pairlist":
        parts.append(_piece_text(node.car))
        node = node.cdr
        if isinstance(node, Obj) and node.kind == "null":
            break
    return character(parts)


def _piece_text(obj) -> str:
    if obj is None:
        return ""
    if isinstance(obj, str):
        return obj
    if not isinstance(obj, Obj):
        return str(obj)
    if obj.kind == "symbol":
        return "" if not obj.data else str(obj.data)
    if obj.kind == "string":
        value = obj.data[0] if obj.data else ""
        return "NA" if value is NA else str(value)
    if obj.kind == "integer":
        value = obj.data[0] if obj.data else NA
        return "NA" if value is NA else str(int(value))
    if obj.kind == "real":
        value = obj.data[0] if obj.data else NA
        if _is_missing(value):
            return "NA"
        return _format_double(float(value))
    if obj.kind == "logical":
        value = obj.data[0] if obj.data else NA
        if value is NA:
            return "NA"
        return "TRUE" if value else "FALSE"
    if obj.kind == "lang":
        return " ".join(_as_character_language(obj).data)
    return ""


def _is_true(value) -> bool:
    if value is True:
        return True
    if isinstance(value, Obj) and value.kind == "logical" and len(value.data) == 1:
        return value.data[0] is True
    return False
