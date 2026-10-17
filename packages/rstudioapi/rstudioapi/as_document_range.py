"""Coerce values to ``document_range`` (rstudioapi 0.19.0)."""

from __future__ import annotations

from dataclasses import dataclass

from rstudioapi.as_document_position import (
    DocumentPosition,
    as_document_position,
    document_position,
    format_document_position,
)
from rstudioapi.is_available import RstudioapiError


@dataclass(frozen=True, slots=True)
class DocumentRange:
    """A start and end ``document_position`` pair."""

    start: DocumentPosition
    end: DocumentPosition


def document_range(start, end=None):
    """Build a ``document_range`` from positions or a length-four numeric vector."""
    if end is None:
        values = _numeric_vector4(start)
        if values is None:
            raise RstudioapiError("invalid range specification")
        return DocumentRange(
            document_position(values[0], values[1]),
            document_position(values[2], values[3]),
        )
    return DocumentRange(
        as_document_position(start),
        as_document_position(end),
    )


def is_document_range(x) -> bool:
    """Return whether ``x`` is a ``document_range``."""
    return isinstance(x, DocumentRange)


def as_document_range(x):
    """Coerce ``x`` to ``document_range``.

    Existing ranges are returned unchanged. A numeric vector of length four
    becomes ``document_range(x[0], x[1], x[2], x[3])`` via ``document_range``.
    """
    if isinstance(x, DocumentRange):
        return x
    return document_range(x)


def format_document_range(x: DocumentRange) -> str:
    """R ``format.document_range``."""
    start = format_document_position(x.start)
    end = format_document_position(x.end)
    return f"{start} -- {end}"


def print_document_range(x: DocumentRange) -> None:
    """R ``print.document_range``."""
    print("Document Range:")
    print("- Start: ", format_document_position(x.start), sep="")
    print("- End: ", format_document_position(x.end), sep="")


def _numeric_vector4(x):
    if isinstance(x, (list, tuple)):
        if len(x) != 4:
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
