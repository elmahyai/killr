"""Coerce values to ``document_position`` (rstudioapi 0.19.0)."""

from __future__ import annotations

import math
from dataclasses import dataclass

from rstudioapi.is_available import RstudioapiError


@dataclass(frozen=True, slots=True)
class DocumentPosition:
    """A row and column in a document, using 1-based indexing."""

    row: float
    column: float


def document_position(row, column):
    """Build a ``document_position`` from row and column."""
    return DocumentPosition(_as_numeric(row), _as_numeric(column))


def is_document_position(x) -> bool:
    """Return whether ``x`` is a ``document_position``."""
    return isinstance(x, DocumentPosition)


def as_document_position(x):
    """Coerce ``x`` to ``document_position``.

    Existing positions are returned unchanged. A numeric vector of length two
    becomes ``document_position(x[0], x[1])``.
    """
    if isinstance(x, DocumentPosition):
        return x
    return _as_document_position_default(x)


def format_document_position(x: DocumentPosition) -> str:
    """R ``format.document_position``."""
    row = _format_num(x.row)
    column = _format_num(x.column)
    return f"[{row}, {column}]"


def print_document_position(x: DocumentPosition) -> None:
    """R ``print.document_position``."""
    print(f"Document Position: {format_document_position(x)}")


def _as_document_position_default(x):
    values = _numeric_vector2(x)
    if values is None:
        raise RstudioapiError("'x' should be a numeric vector of length 2")
    return document_position(values[0], values[1])


def _numeric_vector2(x):
    if isinstance(x, (list, tuple)):
        if len(x) != 2:
            return None
        out = []
        for item in x:
            if isinstance(item, bool) or isinstance(item, complex):
                return None
            if isinstance(item, int):
                out.append(float(item))
            elif isinstance(item, float):
                out.append(item)
            else:
                return None
        return out
    return None


def _as_numeric(value):
    if isinstance(value, bool):
        raise RstudioapiError("'x' should be a numeric vector of length 2")
    if isinstance(value, int):
        return float(value)
    if isinstance(value, float):
        return value
    raise RstudioapiError("'x' should be a numeric vector of length 2")


def _format_num(value: float) -> str:
    if math.isnan(value):
        return "NA"
    if value == int(value):
        return str(int(value))
    return format(value, ".15g")
