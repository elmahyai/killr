"""toJSON and unbox. Arrays and objects are compact, with no spaces."""

from __future__ import annotations

import math
from typing import Any

from jsonlite._numbers import format_double, format_integer
from jsonlite._values import NA, DataFrame, I, Scalar


def unbox(x: Any) -> Any:
    """Mark a length-one vector or a one-row data frame so it is not an array."""

    if x is None:
        return x
    if isinstance(x, DataFrame):
        if len(x) == 1:
            return Scalar(x)
        raise ValueError(f"Tried to unbox dataframe with {len(x)} rows.")
    if isinstance(x, (list, dict)):
        raise ValueError("Only atomic vectors of length 1 or data frames with 1 row can be unboxed.")
    return Scalar(x)


def toJSON(
    x: Any,
    *,
    dataframe: str = "rows",
    digits: int | I = 4,
    auto_unbox: bool = False,
    pretty: bool | int = False,
    null: str = "list",
    na: str | None = None,
    factor: str = "string",
) -> str:
    """Encode ``x`` with jsonlite's defaults: rows for data frames, length-one values kept as arrays."""

    signif = isinstance(digits, I)
    precision = digits.value if isinstance(digits, I) else digits
    text = _encode(
        x,
        dataframe=dataframe,
        digits=precision,
        signif=signif,
        auto_unbox=auto_unbox,
        null=null,
        na=na,
        factor=factor,
        collapse=True,
    )
    if pretty is False or pretty == 0:
        return text
    from jsonlite._format import prettify

    indent = 2 if pretty is True else int(pretty)
    return prettify(text, indent=indent).rstrip("\n")


def _encode(
    x: Any,
    *,
    dataframe: str,
    digits: int,
    signif: bool,
    auto_unbox: bool,
    null: str,
    na: str | None,
    factor: str,
    collapse: bool,
) -> str:
    if isinstance(x, Scalar):
        return _encode(
            x.value,
            dataframe=dataframe,
            digits=digits,
            signif=signif,
            auto_unbox=True,
            null=null,
            na=na,
            factor=factor,
            collapse=False,
        )
    if isinstance(x, DataFrame):
        return _encode_frame(
            x,
            dataframe=dataframe,
            digits=digits,
            signif=signif,
            auto_unbox=auto_unbox,
            null=null,
            na="omit" if na is None else na,
            factor=factor,
            collapse=collapse,
        )
    if isinstance(x, dict):
        return _encode_object(
            x,
            dataframe=dataframe,
            digits=digits,
            signif=signif,
            auto_unbox=auto_unbox,
            null=null,
            na=na,
            factor=factor,
        )
    if isinstance(x, list):
        return _encode_list(
            x,
            dataframe=dataframe,
            digits=digits,
            signif=signif,
            auto_unbox=auto_unbox,
            null=null,
            na=na,
            factor=factor,
            collapse=collapse,
        )
    if x is None:
        return "null" if null == "null" else "{}"
    piece = _atomic_piece(x, digits=digits, signif=signif, na=_default_na(x, na))
    if auto_unbox or not collapse:
        return piece
    return f"[{piece}]"


def _default_na(value: Any, na: str | None) -> str:
    if na is not None:
        return na
    if isinstance(value, str):
        return "null"
    if isinstance(value, bool):
        return "null"
    return "string"


def _atomic_piece(value: Any, *, digits: int, signif: bool, na: str) -> str:
    if value is NA:
        return _missing_token(na, "NA")
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int) and not isinstance(value, bool):
        return format_integer(value)
    if isinstance(value, float):
        if math.isnan(value):
            return _missing_token(na, "NaN")
        if math.isinf(value):
            label = "Inf" if value > 0 else "-Inf"
            return _missing_token(na, label)
        return format_double(value, digits, signif=signif)
    if isinstance(value, str):
        return _quote(value)
    if isinstance(value, (bytes, bytearray)):
        from jsonlite._base64 import base64_enc

        return _quote(base64_enc(bytes(value)))
    raise TypeError(f"no JSON mapping for {type(value).__name__}")


def _missing_token(na: str, label: str) -> str:
    if na == "omit":
        return ""
    if na == "null":
        return "null"
    if na == "string":
        return _quote(label)
    return ""


def _quote(text: str) -> str:
    out = ['"']
    previous = ""
    for char in text:
        if char == "\\" or char == '"':
            out.append("\\" + char)
        elif char == "\n":
            out.append("\\n")
        elif char == "\r":
            out.append("\\r")
        elif char == "\t":
            out.append("\\t")
        elif char == "\b":
            out.append("\\b")
        elif char == "\f":
            out.append("\\f")
        elif char == "/" and previous == "<":
            out.append("\\/")
        elif ord(char) < 32:
            out.append(f"\\u{ord(char):04x}")
        else:
            out.append(char)
        previous = char
    out.append('"')
    return "".join(out)


def _encode_list(
    values: list,
    *,
    dataframe: str,
    digits: int,
    signif: bool,
    auto_unbox: bool,
    null: str,
    na: str | None,
    factor: str,
    collapse: bool,
) -> str:
    if values and all(_is_atomic(item) for item in values):
        kind_na = na if na is not None else _vector_na(values)
        pieces = [_atomic_piece(item, digits=digits, signif=signif, na=kind_na) for item in values]
        if auto_unbox and len(pieces) == 1:
            return pieces[0]
        if not collapse:
            return pieces[0] if len(pieces) == 1 else "[" + ",".join(pieces) + "]"
        return "[" + ",".join(pieces) + "]"
    pieces = [
        _encode(
            item,
            dataframe=dataframe,
            digits=digits,
            signif=signif,
            auto_unbox=auto_unbox,
            null=null,
            na=na,
            factor=factor,
            collapse=True,
        )
        for item in values
    ]
    if not collapse and len(pieces) == 1:
        return pieces[0]
    return "[" + ",".join(pieces) + "]"


def _encode_object(
    values: dict,
    *,
    dataframe: str,
    digits: int,
    signif: bool,
    auto_unbox: bool,
    null: str,
    na: str | None,
    factor: str,
) -> str:
    parts: list[str] = []
    for key, value in values.items():
        encoded = _encode(
            value,
            dataframe=dataframe,
            digits=digits,
            signif=signif,
            auto_unbox=auto_unbox,
            null=null,
            na=na,
            factor=factor,
            collapse=True,
        )
        if encoded == "":
            continue
        parts.append(_quote(str(key)) + ":" + encoded)
    return "{" + ",".join(parts) + "}"


def _encode_frame(
    frame: DataFrame,
    *,
    dataframe: str,
    digits: int,
    signif: bool,
    auto_unbox: bool,
    null: str,
    na: str,
    factor: str,
    collapse: bool,
) -> str:
    if dataframe == "columns":
        return _encode_object(
            frame.columns,
            dataframe=dataframe,
            digits=digits,
            signif=signif,
            auto_unbox=auto_unbox,
            null=null,
            na=None,
            factor=factor,
        )
    names = list(frame.columns)
    rows = []
    for index in range(len(frame)):
        parts = []
        for name in names:
            cell = frame.columns[name][index]
            piece = _encode(
                cell,
                dataframe=dataframe,
                digits=digits,
                signif=signif,
                auto_unbox=True,
                null=null,
                na="omit",
                factor=factor,
                collapse=False,
            )
            if piece == "":
                continue
            parts.append(_quote(name) + ":" + piece)
        rows.append("{" + ",".join(parts) + "}")
    if not collapse:
        return rows  # type: ignore[return-value]
    return "[" + ",".join(rows) + "]"


def _is_atomic(value: Any) -> bool:
    if value is None:
        return False
    if value is NA:
        return True
    return isinstance(value, (bool, int, float, str, bytes, bytearray))


def _vector_na(values: list) -> str:
    saw_number = False
    for item in values:
        if isinstance(item, str):
            return "null"
        if isinstance(item, bool):
            return "null"
        if isinstance(item, (int, float)) and item is not NA:
            saw_number = True
    return "string" if saw_number else "null"
