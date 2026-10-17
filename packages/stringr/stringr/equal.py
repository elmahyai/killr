"""Collation equivalence of two character vectors.

Sizes follow vctrs: a length-1 vector recycles, and two other lengths
must agree. ``ignore_case=True`` uses secondary strength unless
``strength`` is passed. The default locale is English.
"""

from __future__ import annotations

from stringi import stri_cmp_equiv, stri_opts_collator

from stringr._size import size_common


def str_equal(x, y, locale="en", ignore_case=False, **kwargs):
    """True where ``x`` and ``y`` are equivalent under the collator.

    A missing element makes that result missing. ``NULL`` takes no part
    in the size check; the comparison of an empty argument is empty.
    """

    size_common(x, y, names=["x", "y"])
    _check_string(locale, "locale")
    _check_bool(ignore_case, "ignore_case")
    opts = _collator_opts(locale, ignore_case, kwargs)
    return stri_cmp_equiv(x, y, opts_collator=opts)


def _collator_opts(locale: str, ignore_case: bool, extra: dict) -> dict:
    strength = extra.pop("strength", None)
    if strength is None:
        strength = 2 if ignore_case else 3
    return stri_opts_collator(strength=strength, locale=locale, **extra)


def _check_bool(value: object, name: str) -> None:
    if value is True or value is False:
        return
    raise ValueError(f"`{name}` must be `TRUE` or `FALSE`.")


def _check_string(value: object, name: str) -> None:
    if isinstance(value, str):
        return
    raise ValueError(f"`{name}` must be a single string.")
