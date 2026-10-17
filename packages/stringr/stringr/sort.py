"""Sort, order, and rank character vectors.

``str_sort`` is the original vector indexed by ``stri_order``. A leading
U+FEFF stays on the string, and a number stays a number. The default
locale is English.
"""

from __future__ import annotations

from stringi import stri_opts_collator, stri_order, stri_rank
from stringi._na import NA


def str_order(x, decreasing=False, na_last=True, locale="en", numeric=False, **kwargs):
    """1-based stable positions that sort ``x``.

    ``na_last=True`` puts missing strings last, ``False`` puts them first,
    and ``NA`` drops them. ``numeric=True`` compares digit runs as numbers.
    """

    _check_bool(decreasing, "decreasing")
    _check_bool(na_last, "na_last", allow_na=True)
    _check_string(locale, "locale")
    _check_bool(numeric, "numeric")
    opts = stri_opts_collator(locale, numeric=numeric, **kwargs)
    return stri_order(x, decreasing=decreasing, na_last=na_last, opts_collator=opts)


def str_rank(x, locale="en", numeric=False, **kwargs):
    """Minimum ranks. Tied strings share the smaller rank. Missing strings stay missing."""

    _check_string(locale, "locale")
    _check_bool(numeric, "numeric")
    opts = stri_opts_collator(locale, numeric=numeric, **kwargs)
    return stri_rank(x, opts_collator=opts)


def str_sort(x, decreasing=False, na_last=True, locale="en", numeric=False, **kwargs):
    """The elements of ``x`` in collation order.

    ``NULL`` stays ``None``. An empty vector is an empty list. Missing
    strings follow ``na_last``, the same rule as ``str_order``.
    """

    _check_bool(decreasing, "decreasing")
    _check_bool(na_last, "na_last", allow_na=True)
    _check_string(locale, "locale")
    _check_bool(numeric, "numeric")
    opts = stri_opts_collator(locale, numeric=numeric, **kwargs)
    index = stri_order(x, decreasing=decreasing, na_last=na_last, opts_collator=opts)
    return _subset(x, index)


def _subset(values, index):
    if values is None:
        return None
    items = _items(values)
    return [items[position - 1] for position in index]


def _items(values):
    if isinstance(values, range):
        return list(values)
    if isinstance(values, (list, tuple)):
        return list(values)
    return [values]


def _check_bool(value: object, name: str, allow_na: bool = False) -> None:
    if value is True or value is False:
        return
    if allow_na and value is NA:
        return
    if allow_na:
        raise ValueError(f"`{name}` must be `TRUE`, `FALSE`, or `NA`.")
    raise ValueError(f"`{name}` must be `TRUE` or `FALSE`.")


def _check_string(value: object, name: str) -> None:
    if isinstance(value, str):
        return
    raise ValueError(f"`{name}` must be a single string.")
