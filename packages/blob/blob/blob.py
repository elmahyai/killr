"""Python value model for the CRAN ``blob`` package.

R's ``blob`` is an S3/vctrs list whose elements are raw vectors or NULL.
Python represents raw vectors as ``bytes`` and missing blob elements as
``None``.  The two vctrs S3 methods are ordinary functions here; Python
does not reproduce vctrs dispatch.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any


class Blob(list):
    """A list of bytes objects (or None for an R NULL/missing element)."""


def _is_raw(value: Any) -> bool:
    return isinstance(value, (bytes, bytearray, memoryview))


def _raw(value: Any) -> bytes:
    if _is_raw(value):
        return bytes(value)
    raise TypeError("blob elements must be bytes-like or None")


def validate_blob(x: Any) -> None:
    """Validate a list of raw vectors, returning invisibly as in R."""
    if not isinstance(x, list) or not all(item is None or _is_raw(item) for item in x):
        raise TypeError("`x` must be a list of raw vectors")


def new_blob(x: list[Any] | None = None) -> Blob:
    """Low-level constructor for a list of raw vectors."""
    if x is None:
        x = []
    validate_blob(x)
    return Blob(None if item is None else bytes(item) for item in x)


def blob(*args: Any) -> Blob:
    """Construct a blob from individual raw vectors."""
    validate_blob(list(args))
    return new_blob(list(args))


def vec_cast_blob(x: Any, to: Any = None, *args: Any, **kwargs: Any) -> Blob:
    """Cast ``x`` to Blob; an ordinary function replacing vctrs dispatch."""
    if isinstance(x, Blob):
        return x
    if isinstance(x, (bytes, bytearray, memoryview)):
        return blob(bytes(x))
    if isinstance(x, str):
        # R's charToRaw uses the native UTF-8 representation for these
        # examples and NA_character_ is represented by None in Python.
        return blob(x.encode("utf-8"))
    if x is None:
        return blob(None)
    if isinstance(x, int):
        return blob(bytes((x % 256,)))
    if isinstance(x, (list, tuple)):
        if all(item is None or isinstance(item, str) for item in x):
            return blob(*(None if item is None else item.encode("utf-8") for item in x))
        if all(item is None or _is_raw(item) for item in x):
            return blob(*x)
        if all(isinstance(item, int) or item is None for item in x):
            return blob(*(None if item is None else bytes((item % 256,)) for item in x))
        raise TypeError("cannot cast object to blob")
    raise TypeError("cannot cast object to blob")


def as_blob(x: Any) -> Blob:
    return vec_cast_blob(x, new_blob())


def as_blob_legacy(x: Any, *args: Any, **kwargs: Any) -> Blob:
    """Legacy ``as.blob`` entry point; R marks this interface deprecated."""
    return as_blob(x)


def is_blob(x: Any) -> bool:
    return isinstance(x, Blob)


def vec_ptype2_blob(x: Any, y: Any, *args: Any, **kwargs: Any) -> Blob:
    """Return the common blob prototype; an ordinary vctrs replacement."""
    if isinstance(x, Blob) and isinstance(y, Blob):
        return new_blob()
    if isinstance(x, Blob) and isinstance(y, list):
        validate_blob(y)
        return new_blob()
    if isinstance(y, Blob) and isinstance(x, list):
        validate_blob(x)
        return new_blob()
    raise TypeError("incompatible types for blob common prototype")


# Make the R export names available to callers using getattr/importlib.
globals()["as.blob"] = as_blob_legacy
globals()["vec_cast.blob"] = vec_cast_blob
globals()["vec_ptype2.blob"] = vec_ptype2_blob

