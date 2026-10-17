"""idiv from iterators 1.0.14.

Returns an abstract iterator over pieces of one number. Each step yields
``ceiling(n / chunks)``, subtracts that piece from ``n``, and subtracts one
from ``chunks``. It stops when ``chunks`` or ``n`` is no longer positive.
``iter`` and ``nextElem`` from ``iterators.core`` are what walk the result.
"""

from __future__ import annotations

import math

import numpy as np

from iterators.core import Iter, IteratorError
from iterators.core import iter as r_iter


_NAMED = ("n", "chunks", "chunkSize")


def _is_bool(value):
    return isinstance(value, (bool, np.bool_))


def _is_real(value):
    return (not _is_bool(value)) and isinstance(value, (int, float, np.integer, np.floating))


def _is_text(value):
    return isinstance(value, str)


def _elements(value):
    """An R atomic vector as ``(kind, elements)``.

    ``NULL`` and an empty vector have no elements. A Python list or tuple is
    that atomic vector, which is how ``c()`` is represented beside ``icount``.
    """
    if value is None:
        return "empty", []
    if _is_bool(value):
        return "logical", [bool(value)]
    if _is_real(value):
        if isinstance(value, np.generic):
            value = value.item()
        return "numeric", [value]
    if _is_text(value):
        return "character", [value]
    if isinstance(value, np.ndarray):
        if value.dtype.kind == "b":
            kind = "logical"
            elements = [bool(item) for item in np.ravel(value, order="F")]
        elif value.dtype.kind in "iuf":
            kind = "numeric"
            elements = [item.item() if isinstance(item, np.generic) else item for item in np.ravel(value, order="F")]
        elif value.dtype.kind in "SU":
            kind = "character"
            elements = [str(item) for item in np.ravel(value, order="F")]
        else:
            return "other", []
        return kind, elements
    if isinstance(value, (list, tuple)):
        if len(value) == 0:
            return "empty", []
        if all(_is_bool(item) for item in value):
            return "logical", [bool(item) for item in value]
        if all(_is_real(item) for item in value):
            return "numeric", [
                item.item() if isinstance(item, np.generic) else item for item in value
            ]
        if all(_is_text(item) for item in value):
            return "character", [str(item) for item in value]
        return "other", []
    return "other", []


def _single_number(value, message):
    """``is.numeric(value) && length(value) == 1``, as a float."""
    kind, elements = _elements(value)
    if kind != "numeric" or len(elements) != 1:
        raise IteratorError(message)
    return float(elements[0])


def _le_zero(value):
    """The scalar ``value <= 0`` used by ``||``.

    Length greater than one is the coercion error ``||`` raises. Length zero
    is a missing condition. A character value is compared with ``"0"``.
    """
    kind, elements = _elements(value)
    if kind == "other":
        raise IteratorError("non-numeric argument to binary operator")
    width = len(elements)
    if width > 1:
        raise IteratorError(f"'length = {width}' in coercion to 'logical(1)'")
    if width == 0:
        return None
    item = elements[0]
    if kind == "numeric":
        number = float(item)
        if math.isnan(number):
            return None
        return number <= 0.0
    if kind == "logical":
        return float(bool(item)) <= 0.0
    if kind == "character":
        return item <= "0"
    raise IteratorError("non-numeric argument to binary operator")


def _or_le_zero(left, right):
    """``left <= 0 || right <= 0``. ``None`` means the condition is missing."""
    left_flag = _le_zero(left)
    if left_flag is True:
        return True
    right_flag = _le_zero(right)
    if left_flag is False:
        return right_flag
    if right_flag is True:
        return True
    return None


def _number(value):
    kind, elements = _elements(value)
    if kind == "numeric" and len(elements) == 1:
        return float(elements[0])
    if kind == "logical" and len(elements) == 1:
        return float(bool(elements[0]))
    raise IteratorError("non-numeric argument to binary operator")


def _ceiling(value):
    value = float(value)
    if math.isnan(value) or math.isinf(value):
        return value
    return float(math.ceil(value))


def _chunks_from_size(n, chunk_size):
    kind, elements = _elements(chunk_size)
    if kind != "numeric" or len(elements) != 1:
        raise IteratorError("chunkSize must be a numeric value >= 1")
    size = float(elements[0])
    if math.isnan(size):
        raise IteratorError("missing value where TRUE/FALSE needed")
    if size < 1.0:
        raise IteratorError("chunkSize must be a numeric value >= 1")
    return _ceiling(n / size)


def idiv(*args, **kwargs):
    """Divide ``n`` into ``chunks`` pieces, or into pieces of ``chunkSize``.

    ``n`` has to be one number. ``chunks`` and ``chunkSize`` have to be named,
    and exactly one of them is supplied. Names after the dots are exact, so a
    shortened name is an extra argument. A missing ``chunks`` sets the count
    to ``ceiling(n / chunkSize)``, and ``chunkSize`` has to be at least 1.
    """
    supplied = {}
    dots = []
    for name, value in kwargs.items():
        if name in _NAMED:
            supplied[name] = value
        else:
            dots.append(value)
    positionals = list(args)
    if "n" in supplied:
        dots.extend(positionals)
    elif not positionals:
        raise IteratorError('argument "n" is missing, with no default')
    else:
        supplied["n"] = positionals.pop(0)
        dots.extend(positionals)

    n = _single_number(supplied["n"], "n must be a numeric value")
    if dots:
        raise IteratorError("chunks and chunkSize must be specified as named arguments")

    has_chunks = "chunks" in supplied
    has_size = "chunkSize" in supplied
    if has_chunks == has_size:
        raise IteratorError("either chunks or chunkSize must be specified, but not both")
    if has_chunks:
        chunks = supplied["chunks"]
    else:
        chunks = _chunks_from_size(n, supplied["chunkSize"])

    def next_el():
        nonlocal n, chunks
        flag = _or_le_zero(chunks, n)
        if flag is None:
            raise IteratorError("missing value where TRUE/FALSE needed")
        if flag:
            raise IteratorError("StopIteration")
        left = _number(n)
        right = _number(chunks)
        piece = _ceiling(left / right)
        n = left - piece
        chunks = right - 1.0
        return piece

    return r_iter(Iter(["abstractiter", "iter"], nextElem=next_el))
