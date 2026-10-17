"""glue, glue_data, glue_collapse, and as_glue."""

from __future__ import annotations

import inspect
import math
from typing import Any

from glue._eval import identity_transformer
from glue._scan import GlueError, scan
from glue._text import NA, Glue, character_vector, display_width
from glue._trim import trim_text

_EMPTY = object()


def _caller_names() -> dict[str, Any]:
    frame = inspect.currentframe()
    caller = frame.f_back.f_back if frame is not None and frame.f_back is not None else None
    if caller is None:
        return {}
    names = {key: value for key, value in caller.f_globals.items() if not key.startswith("__")}
    names.update(
        {key: value for key, value in caller.f_locals.items() if not key.startswith("__")}
    )
    return names


def _scope(data: Any, envir: dict[str, Any] | None, named: dict[str, Any]) -> dict[str, Any]:
    if envir is None:
        parent: dict[str, Any] = {}
    else:
        parent = dict(envir)
    if data is None:
        scope = parent
    elif isinstance(data, dict):
        scope = {**parent, **data}
    else:
        raise TypeError("glue_data expects a dict of names, or None")
    scope.update(named)
    return scope


def _as_pieces(value: Any, null: Any) -> tuple[Any, ...] | None:
    if value is None:
        value = () if null is _EMPTY else null
    if value is None:
        return None
    if callable(value) and not isinstance(value, type):
        return value  # type: ignore[return-value]
    return character_vector(value)


def _recycle(columns: list[tuple[Any, ...]]) -> list[tuple[Any, ...]]:
    if not columns:
        return []
    lengths = [len(column) for column in columns]
    if all(length == 0 for length in lengths):
        return []
    longest = max(lengths)
    if any(length != 1 and length != longest for length in lengths):
        if longest == 1:
            raise GlueError("Variables must be length 1")
        raise GlueError(f"Variables must be length 1 or {longest}")
    recycled: list[tuple[Any, ...]] = []
    for column, length in zip(columns, lengths):
        if longest != 1 and length == 1:
            recycled.append(column * longest)
        else:
            recycled.append(column)
    return recycled


def _paste(columns: list[tuple[Any, ...]], na: Any) -> Glue:
    if any(len(column) == 0 for column in columns):
        return Glue(())
    if na is not None:
        replaced: list[tuple[Any, ...]] = []
        for column in columns:
            replaced.append(tuple(na if item is NA else item for item in column))
        columns = replaced
        missing_rows: set[int] = set()
    else:
        missing_rows = set()
        for column in columns:
            for index, item in enumerate(column):
                if item is NA:
                    missing_rows.add(index)
    columns = _recycle(columns)
    if not columns:
        return Glue(())
    rows: list[Any] = []
    width = len(columns[0])
    for index in range(width):
        if na is None and index in missing_rows:
            rows.append(NA)
            continue
        rows.append("".join("" if item is NA else str(item) for item in (column[index] for column in columns)))
    return Glue(tuple(rows))


def glue_data(
    x: Any,
    *parts: Any,
    sep: str = "",
    envir: dict[str, Any] | None = None,
    open: str = "{",
    close: str = "}",
    na: Any = "NA",
    null: Any = _EMPTY,
    comment: str = "#",
    literal: bool = False,
    transformer: Any = None,
    trim: bool = True,
    **named: Any,
) -> Glue:
    """Interpolate ``parts`` using names from ``x``, then ``envir``, then ``named``."""

    if envir is None and not named and x is None:
        envir = _caller_names()
    elif envir is None:
        envir = _caller_names()
    scope = _scope(x, envir, named)
    convert = identity_transformer if transformer is None else transformer

    templates: list[Any] = []
    for part in parts:
        if part is None:
            part = () if null is _EMPTY else null
        if part is None:
            continue
        templates.append(part)
    if not templates:
        return Glue(())

    lengths = []
    for part in templates:
        if isinstance(part, str):
            lengths.append(1)
        elif isinstance(part, Glue):
            lengths.append(len(part.values))
        elif isinstance(part, (list, tuple)):
            lengths.append(len(part))
        else:
            lengths.append(1)
    if any(length == 0 for length in lengths):
        return Glue(())
    if any(length != 1 for length in lengths):
        raise GlueError("All unnamed arguments must be length 1")

    texts: list[Any] = []
    for part in templates:
        if isinstance(part, Glue):
            texts.append(part.values[0])
        elif isinstance(part, (list, tuple)):
            texts.append(part[0])
        else:
            texts.append(part)
    if any(item is NA for item in texts):
        if na is None:
            return Glue((NA,))
        texts = [na if item is NA else item for item in texts]
    template = sep.join("" if item is NA else str(item) for item in texts)
    if trim:
        template = trim_text(template)

    def apply(expr: str) -> Any:
        value = convert(expr, scope)
        if value is None:
            value = () if null is _EMPTY else null
        if value is None:
            return None
        if callable(value) and not isinstance(value, type):
            raise GlueError(
                "glue cannot interpolate functions into strings.\n"
                f"* object '{expr}' is a function."
            )
        return character_vector(value)

    pieces = scan(template, apply, open, close, comment, literal)
    kept: list[tuple[Any, ...]] = []
    for piece in pieces:
        if piece is None:
            continue
        if isinstance(piece, str):
            kept.append((piece,))
        else:
            kept.append(tuple(piece))
    return _paste(kept, na)


def glue(
    *parts: Any,
    sep: str = "",
    envir: dict[str, Any] | None = None,
    open: str = "{",
    close: str = "}",
    na: Any = "NA",
    null: Any = _EMPTY,
    comment: str = "#",
    literal: bool = False,
    transformer: Any = None,
    trim: bool = True,
    **named: Any,
) -> Glue:
    """Interpolate ``parts``. Braces are Python expressions over the names in scope."""

    if envir is None:
        envir = _caller_names()
    return glue_data(
        None,
        *parts,
        sep=sep,
        envir=envir,
        open=open,
        close=close,
        na=na,
        null=null,
        comment=comment,
        literal=literal,
        transformer=transformer,
        trim=trim,
        **named,
    )


def glue_collapse(x: Any, sep: str = "", width: float = math.inf, last: str = "") -> Glue:
    """Collapse a vector into one string. ``last`` separates the final item."""

    if x is None:
        return Glue(("",))
    values = character_vector(x)
    if values is None or len(values) == 0:
        return Glue(("",))
    if any(item is NA for item in values):
        return Glue((NA,))
    if last and len(values) > 1:
        head = glue_collapse(values[:-1], sep=sep, width=math.inf, last="")
        joined = f"{head.values[0]}{last}{values[-1]}"
        return glue_collapse(joined, width=width)
    text = sep.join(str(item) for item in values)
    if width < math.inf:
        if display_width(text) > width:
            keep = int(width) - 3
            if keep < 0:
                keep = 0
            text = text[:keep] + "..."
    return Glue((text,))


def as_glue(x: Any, *args: Any) -> Glue:
    """Mark a character vector as glue. Other values are converted first."""

    if isinstance(x, Glue):
        return x
    if x is None:
        return Glue(())
    values = character_vector(x)
    if values is None:
        return Glue(())
    return Glue(values)


def plain(value: Any) -> Any:
    """JSON-ready form of a glue result. A missing value is ``None``."""

    if isinstance(value, Glue):
        rows = [None if item is NA else item for item in value.values]
        if len(rows) == 1:
            return rows[0]
        return rows
    if value is NA:
        return None
    return value
