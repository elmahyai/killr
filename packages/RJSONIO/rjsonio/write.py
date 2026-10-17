"""toJSON, following the S4 methods and the atomic fast path."""

from __future__ import annotations

import math
import warnings

from rjsonio.errors import RJSONIOError
from rjsonio.values import (
    Array,
    AsIs,
    Atomic,
    DataFrame,
    Environment,
    Factor,
    HexMode,
    Matrix,
    RList,
)

_COLLAPSE = {
    "integer": "\n  ",
    "logical": "\n",
    "numeric": "\n",
    "character": "\n",
    "hexmode": "\n   ",
    "list": "\n",
    "matrix": "\n",
    "array": "\n",
    "data.frame": "\n",
    "environment": "\n  ",
    "null": "\n",
    "factor": "\n",
    "asis": "\n",
}


def _kind_of(value) -> str:
    if value is None:
        return "null"
    if isinstance(value, AsIs):
        return "asis"
    if isinstance(value, Matrix):
        return "matrix"
    if isinstance(value, Array):
        return "array"
    if isinstance(value, DataFrame):
        return "data.frame"
    if isinstance(value, Factor):
        return "factor"
    if isinstance(value, Environment):
        return "environment"
    if isinstance(value, HexMode):
        return "hexmode"
    if isinstance(value, Atomic):
        return value.kind
    if isinstance(value, (RList, list, dict)):
        return "list"
    if isinstance(value, bool):
        return "logical"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "numeric"
    if isinstance(value, str):
        return "character"
    if callable(value):
        return "function"
    raise RJSONIOError(
        "S4 slot walking is not part of this translation. "
        f"No method for converting {type(value).__name__} to JSON."
    )


def _names_of(value):
    if isinstance(value, (Atomic, RList, Factor, HexMode, Matrix)):
        return value.names
    if isinstance(value, dict):
        return list(value.keys())
    if isinstance(value, DataFrame):
        return list(value.columns.keys())
    return None


def _length_of(value) -> int:
    if value is None:
        return 0
    if isinstance(value, (Atomic, RList, Factor, HexMode, Matrix)):
        return len(value)
    if isinstance(value, (list, dict, str)):
        return len(value)
    if isinstance(value, DataFrame):
        columns = list(value.columns.values())
        return 0 if not columns else _length_of(columns[0])
    if isinstance(value, (bool, int, float)):
        return 1
    if isinstance(value, AsIs):
        return _length_of(value.value)
    if isinstance(value, Environment):
        return len(value.bindings)
    return 1


def _is_list(value) -> bool:
    return isinstance(value, (RList, list, dict))


def _is_container(value, as_is, level: int) -> bool:
    if as_is is None and level == 1:
        return True
    if as_is is not None and as_is:
        return True
    if level == 1:
        return True
    if _length_of(value) > 1:
        return True
    names = _names_of(value)
    if names is not None and len(names) > 0:
        return True
    return _is_list(value)


def _with_names(value, supplied) -> bool:
    if supplied is not None:
        return bool(supplied)
    names = _names_of(value)
    return _length_of(value) > 0 and names is not None and len(names) > 0


def _quote(text: str) -> str:
    return '"' + text + '"'


def _escape(text: str, escape_escapes: bool) -> str:
    out = []
    for char in text:
        if char == "\\":
            out.append("\\\\")
        elif escape_escapes and char == "\t":
            out.append("\\t")
        elif escape_escapes and char == "\n":
            out.append("\\n")
        elif escape_escapes and char == "\b":
            out.append("\\b")
        elif escape_escapes and char == "\r":
            out.append("\\r")
        elif escape_escapes and char == "\f":
            out.append("\\f")
        elif char == '"':
            out.append('\\"')
        else:
            out.append(char)
    return "".join(out)


def _format_c(values, digits: int) -> list[str]:
    """formatC(..., format = 'g') with width digits + 1."""
    width = digits + 1
    formatted = []
    for value in values:
        if value is None or (isinstance(value, float) and math.isnan(value)):
            text = "NA"
        elif isinstance(value, float) and math.isinf(value):
            text = "Inf" if value > 0 else "-Inf"
        else:
            text = format(float(value), f".{digits}g")
        if len(text) < width:
            text = text.rjust(width)
        formatted.append(text)
    return formatted


def _join_named(names, parts, collapse: str) -> str:
    body = f",{collapse}".join(
        f"{_quote(str(name))}: {part}" for name, part in zip(names, parts)
    )
    return " ".join((f"{{{collapse}", body, f"{collapse}}}"))


def _join_array(parts, collapse: str) -> str:
    body = f",{collapse}".join(parts)
    return " ".join((f"[{collapse}", body, f"{collapse}]"))


def _fast_atomic(parts, names, container: bool, collapse: str) -> str:
    count = len(parts)
    if not container:
        if count == 0:
            return "[ ]" if parts is not None else ""
        return parts[0]
    if names:
        chunks = ["{", collapse]
        for index, (name, part) in enumerate(zip(names, parts)):
            if index:
                chunks.append(",")
                chunks.append(collapse)
            chunks.append(_quote(str(name)))
            chunks.append(": ")
            chunks.append(part)
        chunks.append(collapse)
        chunks.append("}")
        return "".join(chunks)
    return "[ " + ", ".join(parts) + " ]"


def _atomic_parts(value: Atomic, na: str, escape_escapes: bool, inf: str, digits: int):
    kind = value.kind
    if kind == "integer":
        parts = []
        for item in value.values:
            parts.append(na if item is None else str(int(item)))
        return parts
    if kind == "logical":
        parts = []
        for item in value.values:
            if item is None:
                parts.append(na)
            else:
                parts.append("true" if item else "false")
        return parts
    if kind == "character":
        parts = []
        for item in value.values:
            if item is None:
                parts.append(na)
            else:
                parts.append(_quote(_escape(str(item), escape_escapes)))
        return parts
    parts = _format_c(value.values, digits)
    rendered = []
    for item, text in zip(value.values, parts):
        if item is None or (isinstance(item, float) and math.isnan(item)):
            rendered.append(na)
        elif isinstance(item, float) and math.isinf(item):
            sign = "-" if item < 0 else ""
            rendered.append(f" {sign}{inf}")
        else:
            rendered.append(text)
    return rendered


def _as_column(value):
    if isinstance(value, (Atomic, AsIs, RList, Matrix, Factor)):
        return value
    if isinstance(value, list):
        if all(isinstance(item, bool) or item is None for item in value):
            return Atomic("logical", value)
        if all(isinstance(item, str) or item is None for item in value):
            return Atomic("character", value)
        if all((isinstance(item, int) and not isinstance(item, bool)) or item is None for item in value):
            return Atomic("integer", value)
        if all(
            (isinstance(item, (int, float)) and not isinstance(item, bool)) or item is None
            for item in value
        ):
            return Atomic(
                "numeric",
                [None if item is None else float(item) for item in value],
            )
    return value


def _as_atomic(value) -> Atomic | None:
    if isinstance(value, Atomic):
        return value
    if isinstance(value, bool):
        return Atomic("logical", [value])
    if isinstance(value, int):
        return Atomic("integer", [value])
    if isinstance(value, float):
        return Atomic("numeric", [None if math.isnan(value) else value])
    if isinstance(value, str):
        return Atomic("character", [value])
    return None


def _list_items(value):
    if isinstance(value, RList):
        return value.values, value.names
    if isinstance(value, dict):
        return list(value.values()), list(value.keys())
    if isinstance(value, list):
        return value, None
    if isinstance(value, Environment):
        return list(value.bindings.values()), list(value.bindings.keys())
    raise RJSONIOError("internal list")


def _slice_array(value: Array, index: int):
    stride = 1
    for dim in value.dim[:-1]:
        stride *= dim
    chunk = value.data[index * stride : (index + 1) * stride]
    rest = value.dim[:-1]
    if len(rest) == 2:
        return Matrix(chunk, rest[0], rest[1], value.kind)
    if len(rest) == 1:
        return Atomic(value.kind, chunk)
    return Array(chunk, rest, value.kind)


def toJSON(
    x,
    container=None,
    collapse=None,
    level: int = 1,
    with_names=None,
    na: str = "null",
    escape_escapes: bool = True,
    pretty: bool = False,
    as_is=None,
    inf: str = " Infinity",
    digits: int = 7,
    byrow: bool = False,
    col_names: bool = False,
) -> str:
    """Serialize x the way RJSONIO::toJSON does for ordinary values."""
    kind = _kind_of(x)
    if collapse is None:
        collapse = _COLLAPSE.get(kind, "\n")
    if container is None:
        container = _is_container(x, as_is, level)
    named = _with_names(x, with_names)

    if kind == "function":
        warnings.warn(
            "converting an R function to JSON as null. "
            "To change this, define a method for toJSON() for a 'function' object.",
            UserWarning,
            stacklevel=2,
        )
        text = "null"
    elif kind == "asis":
        text = toJSON(
            x.value,
            container=True,
            collapse=collapse,
            level=level + 1,
            with_names=named,
            na=na,
            escape_escapes=escape_escapes,
            pretty=False,
            as_is=as_is,
            inf=inf,
            digits=digits,
        )
    elif kind == "factor":
        text = toJSON(
            Atomic("character", x.labels, x.names),
            container=container,
            collapse=collapse,
            level=level,
            with_names=named,
            na=na,
            escape_escapes=escape_escapes,
            pretty=False,
            as_is=as_is,
            inf=inf,
            digits=digits,
        )
    elif kind == "environment":
        text = toJSON(
            RList(list(x.bindings.values()), list(x.bindings.keys())),
            container=container,
            collapse=collapse,
            level=level,
            na=na,
            escape_escapes=escape_escapes,
            pretty=False,
            as_is=as_is,
            inf=inf,
            digits=digits,
        )
    elif kind == "null":
        text = "[ null ] " if container else "null"
    elif kind == "hexmode":
        present = [int(item) for item in x.values if item is not None]
        width = max((len(format(item, "x")) for item in present), default=1)
        parts = []
        for item in x.values:
            if item is None:
                parts.append(na)
            else:
                parts.append("0x" + format(int(item), "x").zfill(width))
        text = _fast_atomic(parts, x.names if named else None, container, collapse)
    elif kind in ("integer", "logical", "numeric", "character"):
        atomic = _as_atomic(x)
        if kind == "numeric" and any(
            isinstance(item, float) and math.isinf(item) for item in atomic.values
        ):
            warnings.warn(
                "non-fininte values in numeric vector may not be approriately represented in JSON",
                UserWarning,
                stacklevel=2,
            )
        parts = _atomic_parts(atomic, na, escape_escapes, inf, digits)
        use_fast = kind != "numeric" and (kind != "character" or escape_escapes)
        if use_fast:
            if not container and kind == "character" and len(parts) == 0:
                text = "[ ]"
            elif not container and len(parts) != 1:
                text = "[ ]" if len(parts) == 0 else parts[0]
            else:
                text = _fast_atomic(parts, atomic.names if named else None, container, collapse)
        elif container and named:
            text = _join_named(atomic.names, parts, collapse)
        elif container:
            text = "[ " + ", ".join(parts) + " ]"
        elif len(parts) == 0:
            text = ""
        else:
            text = parts[0]
    elif kind == "matrix":
        rows = [
            toJSON(
                x.row(index),
                na=na,
                escape_escapes=escape_escapes,
                inf=inf,
                digits=digits,
                as_is=as_is,
                pretty=False,
            )
            for index in range(x.nrow)
        ]
        body = f",{collapse}".join(rows)
        if not container:
            text = body
        elif named:
            text = "{ " + ", ".join(
                f"{_quote(str(name))}: {body}" for name in x.names
            ) + " }"
        else:
            text = "[ " + body + " ]"
    elif kind == "array":
        if len(x.dim) <= 2:
            text = toJSON(
                Matrix(x.data, x.dim[0], x.dim[1] if len(x.dim) == 2 else 1, x.kind),
                container=container,
                collapse=collapse,
                level=level,
                na=na,
                escape_escapes=escape_escapes,
                inf=inf,
                digits=digits,
                as_is=as_is,
                pretty=False,
            )
        else:
            slices = [
                toJSON(
                    _slice_array(x, index),
                    na=na,
                    escape_escapes=escape_escapes,
                    inf=inf,
                    digits=digits,
                    as_is=as_is,
                    pretty=False,
                )
                for index in range(x.dim[-1])
            ]
            text = collapse.join(("[", ", ".join(slices), "]"))
    elif kind == "data.frame":
        if byrow:
            names = list(x.columns.keys())
            columns = list(x.columns.values())
            nrow = _length_of(columns[0]) if columns else 0
            rows = []
            for index in range(nrow):
                items = []
                for column in columns:
                    atomic = _as_atomic(column) if not isinstance(column, Atomic) else column
                    if isinstance(column, Atomic):
                        items.append(column.values[index])
                    elif isinstance(column, list):
                        items.append(column[index])
                    else:
                        items.append(atomic.values[index] if atomic else column)
                row = RList(items, names if col_names else None)
                rows.append(row)
            text = toJSON(
                rows,
                container=container,
                collapse=collapse,
                level=level,
                with_names=False,
                na=na,
                escape_escapes=escape_escapes,
                pretty=False,
                as_is=as_is,
                inf=inf,
                digits=digits,
            )
        else:
            wrapped = RList(
                [AsIs(_as_column(column)) for column in x.columns.values()],
                list(x.columns.keys()),
            )
            text = toJSON(
                wrapped,
                container=container,
                collapse=collapse,
                level=level,
                with_names=named,
                na=na,
                escape_escapes=escape_escapes,
                pretty=False,
                as_is=as_is,
                inf=inf,
                digits=digits,
            )
    else:
        items, names = _list_items(x)
        if len(items) == 0:
            text = "{}" if names is not None else "[]"
        else:
            elements = [
                toJSON(
                    item,
                    collapse=collapse,
                    level=level + 1,
                    na=na,
                    escape_escapes=escape_escapes,
                    pretty=False,
                    as_is=as_is,
                    inf=inf,
                    digits=digits,
                )
                for item in items
            ]
            elements = ["[]" if element == "" else element for element in elements]
            if not container:
                text = elements[0] if len(elements) == 1 else ", ".join(elements)
            elif named:
                text = _join_named(names, elements, collapse)
            else:
                text = _join_array(elements, collapse)

    if pretty:
        from rjsonio.parse import pretty_json

        return pretty_json(text)
    return text


def asJSVars(*args, qualifier="", types=False, **kwargs):
    """Declare variables the way asJSVars does for ActionScript."""
    if kwargs:
        mapping = kwargs
    elif len(args) == 1 and isinstance(args[0], dict):
        mapping = args[0]
    else:
        raise RJSONIOError("asJSVars() needs names, as in asJSVars(a=1, b=2).")
    names = list(mapping.keys())
    values = [toJSON(mapping[name]) + " ;" for name in names]
    if types is True:
        type_names = [_js_type(mapping[name]) for name in names]
        ids = [f"{name} : {kind}" for name, kind in zip(names, type_names)]
    elif types:
        ids = [f"{name} : {kind}" for name, kind in zip(names, types)]
    else:
        ids = names
    if qualifier:
        ids = [f"{qualifier} {name}" for name in ids]
    rendered = []
    for name, value in zip(ids, values):
        pad = " " * (len(name) + 3)
        rendered.append(value.replace("\n", "\n" + pad))
    return "\n\n".join(f"{name} = {value}" for name, value in zip(ids, rendered))


def _js_type(value) -> str:
    if isinstance(value, Matrix):
        return "Array"
    atomic = _as_atomic(value)
    if atomic is not None and len(atomic) == 1 and not atomic.names:
        return {"integer": "int", "numeric": "Number", "logical": "Boolean", "character": "String"}[
            atomic.kind
        ]
    if _names_of(value):
        return "Object"
    return "Array"
