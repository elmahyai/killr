"""Row and column all/any checks, ported from matrixStats.

``rowAnyMissings``, ``colAnyMissings``, ``rowAnyNAs``, and ``colAnyNAs``
call :func:`rowAnys` or :func:`colAnys` with ``value=None``, which is R's
``NA``.
"""

from __future__ import annotations

from matrixstats.rowcounts import (
    _WHAT_ALL,
    _WHAT_ANY,
    _as_logical_counts,
    _call_matrix,
    _coerce_value,
    _counts_equal,
    _flag,
    _is_logical_scalar,
    _is_true,
    _logical_is_na,
    _prepare_matrix,
    _prepare_vector,
    _scalar_equal,
    _scalar_logical,
    _vector_question,
)

__all__ = [
    "rowAlls",
    "colAlls",
    "allValue",
    "rowAnys",
    "colAnys",
    "anyValue",
    "rowAnyMissings",
    "colAnyMissings",
    "rowAnyNAs",
    "colAnyNAs",
]


def rowAlls(x, rows=None, cols=None, value=True, na_rm=False, dim=None, use_names=True):
    """Return whether every selected element in a row equals ``value``.

    Mirrors ``matrixStats::rowAlls``. ``rows`` and ``cols`` are 1-based.
    ``None`` uses every row or column. A logical ``value`` on a numeric
    matrix treats zeros as ``FALSE`` and every other non-missing number as
    ``TRUE``. The result is an object array of ``True``, ``False``, and
    ``None``. ``None`` is R's ``NA``.
    """
    return _margin_logic(
        x, rows, cols, value, na_rm, dim, use_names, by_row=True, question="all"
    )


def colAlls(x, rows=None, cols=None, value=True, na_rm=False, dim=None, use_names=True):
    """Return whether every selected element in a column equals ``value``.

    Mirrors ``matrixStats::colAlls``. Arguments match :func:`rowAlls`.
    """
    return _margin_logic(
        x, rows, cols, value, na_rm, dim, use_names, by_row=False, question="all"
    )


def allValue(x, idxs=None, value=True, na_rm=False):
    """Return whether every selected element equals ``value``.

    Mirrors ``matrixStats::allValue``. ``idxs`` is 1-based. ``None`` selects
    every element. A logical ``value`` on a numeric vector treats zeros as
    ``FALSE``. The result is ``True``, ``False``, or ``None``.
    """
    return _vector_logic(x, idxs, value, na_rm, question="all")


def rowAnys(x, rows=None, cols=None, value=True, na_rm=False, dim=None, use_names=True):
    """Return whether any selected element in a row equals ``value``.

    Mirrors ``matrixStats::rowAnys``. Arguments match :func:`rowAlls`.
    A logical ``value`` on a numeric matrix treats zeros as ``FALSE``.
    """
    return _margin_logic(
        x, rows, cols, value, na_rm, dim, use_names, by_row=True, question="any"
    )


def colAnys(x, rows=None, cols=None, value=True, na_rm=False, dim=None, use_names=True):
    """Return whether any selected element in a column equals ``value``.

    Mirrors ``matrixStats::colAnys``. Arguments match :func:`rowAlls`.
    """
    return _margin_logic(
        x, rows, cols, value, na_rm, dim, use_names, by_row=False, question="any"
    )


def anyValue(x, idxs=None, value=True, na_rm=False):
    """Return whether any selected element equals ``value``.

    Mirrors ``matrixStats::anyValue``. Arguments match :func:`allValue`.
    """
    return _vector_logic(x, idxs, value, na_rm, question="any")


def rowAnyMissings(x, rows=None, cols=None, na_rm=False, dim=None, use_names=True):
    """Return whether any selected element in a row is missing.

    Mirrors ``matrixStats::rowAnyMissings``. This calls :func:`rowAnys`
    with ``value=None``.
    """
    return rowAnys(x, rows, cols, value=None, na_rm=na_rm, dim=dim, use_names=use_names)


def colAnyMissings(x, rows=None, cols=None, na_rm=False, dim=None, use_names=True):
    """Return whether any selected element in a column is missing.

    Mirrors ``matrixStats::colAnyMissings``. This calls :func:`colAnys`
    with ``value=None``.
    """
    return colAnys(x, rows, cols, value=None, na_rm=na_rm, dim=dim, use_names=use_names)


def rowAnyNAs(x, rows=None, cols=None, na_rm=False, dim=None, use_names=True):
    """Return whether any selected element in a row is missing.

    Mirrors ``matrixStats::rowAnyNAs``. This calls :func:`rowAnys` with
    ``value=None``.
    """
    return rowAnys(x, rows, cols, value=None, na_rm=na_rm, dim=dim, use_names=use_names)


def colAnyNAs(x, rows=None, cols=None, na_rm=False, dim=None, use_names=True):
    """Return whether any selected element in a column is missing.

    Mirrors ``matrixStats::colAnyNAs``. This calls :func:`colAnys` with
    ``value=None``.
    """
    return colAnys(x, rows, cols, value=None, na_rm=na_rm, dim=dim, use_names=use_names)


def _margin_logic(x, rows, cols, value, na_rm, dim, use_names, by_row, question):
    _flag(na_rm, "na.rm")
    _flag(use_names, "useNames")
    matrix, storage = _prepare_matrix(x, dim)
    if storage in ("integer", "double") and _is_logical_scalar(value) and not _logical_is_na(value):
        what, target = _zero_question(question, _is_true(value))
        zero = 0.0 if storage == "double" else 0
        counts = _call_matrix(matrix, storage, rows, cols, zero, na_rm, what, by_row)
        return _counts_equal(counts, target)
    coerced = _coerce_value(value, storage, length_style="single", on_character="error")
    counts = _call_matrix(
        matrix,
        storage,
        rows,
        cols,
        coerced,
        na_rm,
        _WHAT_ALL if question == "all" else _WHAT_ANY,
        by_row,
    )
    return _as_logical_counts(counts)


def _vector_logic(x, idxs, value, na_rm, question):
    _flag(na_rm, "na.rm")
    _values, storage = _prepare_vector(x)
    if storage in ("integer", "double") and _is_logical_scalar(value) and not _logical_is_na(value):
        what, target = _zero_question(question, _is_true(value))
        tally = _vector_question(
            x, idxs, False, na_rm, what, length_style="single", on_character="error"
        )
        return _scalar_equal(tally, target)
    tally = _vector_question(
        x,
        idxs,
        value,
        na_rm,
        _WHAT_ALL if question == "all" else _WHAT_ANY,
        length_style="single",
        on_character="error",
    )
    return _scalar_logical(tally)


def _zero_question(question, value_is_true):
    """C calls that implement a logical value on numeric data.

    ``rowAlls`` with ``TRUE`` asks whether any zero exists and keeps the rows
    where that count is 0. ``FALSE`` asks whether every element is zero.
    ``rowAnys`` swaps those two questions.
    """
    if question == "all":
        if value_is_true:
            return _WHAT_ANY, 0
        return _WHAT_ALL, 1
    if value_is_true:
        return _WHAT_ALL, 0
    return _WHAT_ANY, 1
