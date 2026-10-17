"""Extract and replace substrings by code-point position.

``str_sub`` and ``str_sub_assign`` check sizes with
``stringr._size.size_common``, then call ``stringi.stri_sub`` and
``stringi.stri_sub_assign``. ``str_sub_all`` calls ``stringi.stri_sub_all``
and does not apply that size check. A two-column matrix is an
``IndexMatrix``, a dict of two columns, a locate matrix with ``colnames``,
or, for ``str_sub`` and ``str_sub_assign``, a list of rows.
"""

from __future__ import annotations

from stringi import stri_sub, stri_sub_all, stri_sub_assign
from stringi._na import NA
from stringi.sub import IndexMatrix
from stringr._size import size_common
from stringr.length import _copy_names

_MISSING = object()


def _is_row_matrix(value: object) -> bool:
    """True when stringi's ``stri_sub`` would read ``value`` as a matrix."""

    if isinstance(value, IndexMatrix):
        return True
    if isinstance(value, dict):
        columns = list(value.values())
        if len(columns) != 2:
            return False
        return all(
            isinstance(column, (list, tuple)) and not isinstance(column, (str, bytes))
            for column in columns
        )
    if not isinstance(value, (list, tuple)) or isinstance(value, (str, bytes)) or not value:
        return False
    for row in value:
        if not isinstance(row, (list, tuple)) or isinstance(row, (str, bytes)):
            return False
        for item in row:
            if not (item is None or item is NA or isinstance(item, (bool, int, float, str))):
                return False
    return True


def _as_matrix(start: object):
    """Keep column names that decide ``end`` versus ``length``."""

    if isinstance(start, IndexMatrix):
        return start
    colnames = getattr(start, "colnames", None)
    if (
        colnames
        and isinstance(start, (list, tuple))
        and not isinstance(start, (str, bytes))
        and start
        and isinstance(start[0], (list, tuple))
    ):
        return IndexMatrix([list(row) for row in start], colnames=tuple(colnames))
    return start


def _for_size(start: object) -> object:
    prepared = _as_matrix(start)
    if isinstance(prepared, IndexMatrix):
        return prepared.rows
    if isinstance(prepared, dict) and _is_row_matrix(prepared):
        return list(next(iter(prepared.values())))
    return start


def _vector_length(value: object) -> int:
    if value is None:
        return 0
    if isinstance(value, (str, bytes)) or not isinstance(value, (list, tuple, dict)):
        return 1
    if isinstance(value, dict):
        return len(_for_size(value))
    return len(value)


def str_sub(string, start=1, end=-1):
    """Extract one inclusive code-point range from each string.

    Positive indexes count from the left, starting at 1. Negative indexes
    count from the right. A matrix ``start`` supplies both ends and
    ``end`` is only size-checked. Names are kept when ``string`` is not
    recycled.
    """

    size_common(string, _for_size(start), end, names=["string", "start", "end"])
    prepared = _as_matrix(start)
    if _is_row_matrix(prepared):
        out = stri_sub(string, prepared)
    else:
        out = stri_sub(string, prepared, end)
    if _vector_length(out) == _vector_length(string):
        return _copy_names(string, out)
    return list(out)


def str_sub_assign(string, start=1, end=-1, value=_MISSING, omit_na=False):
    """Replace one inclusive range in each string. This is R's ``str_sub<-``.

    ``value`` is the replacement. ``omit_na=True`` leaves a string unchanged
    when any index or the string itself is missing.
    """

    if value is _MISSING:
        raise ValueError('argument "value" is missing, with no default')
    size_common(
        string,
        _for_size(start),
        end,
        value,
        names=["string", "start", "end", "value"],
    )
    prepared = _as_matrix(start)
    if _is_row_matrix(prepared):
        return stri_sub_assign(string, prepared, omit_na=omit_na, value=value)
    return stri_sub_assign(string, prepared, end, omit_na=omit_na, value=value)


def str_sub_all(string, start=1, end=-1):
    """Extract several ranges from each string.

    A flat ``start`` and ``end`` are one shared pair of index vectors.
    A list of vectors gives each string its own starts. A matrix, passed
    as an ``IndexMatrix``, a two-column dict, or a locate result with
    ``colnames``, is one set of ranges applied to every string. Names on
    ``string`` are copied onto the outer list.
    """

    prepared = _as_matrix(start)
    matrix = isinstance(prepared, (IndexMatrix, dict)) or (
        getattr(start, "colnames", None) is not None and prepared is not start
    )
    if matrix:
        out = stri_sub_all(string, prepared)
    else:
        out = stri_sub_all(string, start, end)
    return _copy_names(string, out)
