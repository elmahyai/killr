"""Drop duplicated strings under Unicode collation.

The first string of each collation class is kept, including its leading
U+FEFF. ``ignore_case=True`` uses secondary strength unless ``strength``
is passed. The default locale is English.
"""

from __future__ import annotations

from stringi import stri_duplicated, stri_opts_collator


def str_unique(string, locale="en", ignore_case=False, **kwargs):
    """First occurrence of each collation class, in the original order.

    ``NULL`` stays ``None``. A missing string is kept once.
    """

    _check_string(locale, "locale")
    _check_bool(ignore_case, "ignore_case")
    opts = _collator_opts(locale, ignore_case, kwargs)
    flags = stri_duplicated(string, opts_collator=opts)
    if string is None:
        return None
    items = _items(string)
    return [item for item, flag in zip(items, flags, strict=True) if flag is False]


def _collator_opts(locale: str, ignore_case: bool, extra: dict) -> dict:
    strength = extra.pop("strength", None)
    if strength is None:
        strength = 2 if ignore_case else 3
    return stri_opts_collator(strength=strength, locale=locale, **extra)


def _items(values):
    if isinstance(values, range):
        return list(values)
    if isinstance(values, (list, tuple)):
        return list(values)
    return [values]


def _check_bool(value: object, name: str) -> None:
    if value is True or value is False:
        return
    raise ValueError(f"`{name}` must be `TRUE` or `FALSE`.")


def _check_string(value: object, name: str) -> None:
    if isinstance(value, str):
        return
    raise ValueError(f"`{name}` must be a single string.")
