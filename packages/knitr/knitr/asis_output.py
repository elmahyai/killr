"""Mark an object with class knit_asis, matching knitr::asis_output.

The R function is ``structure(x, class = "knit_asis", knit_meta = meta,
knit_cacheable = cacheable)``. A NULL attribute is removed. The default
``cacheable`` is logical NA, so that attribute is stored. ``meta`` defaults
to NULL and is omitted. ``structure(NULL, *)`` warns and becomes an empty
list, because NULL cannot hold attributes.
"""

from __future__ import annotations

import warnings

_MISSING = object()

_NULL_STRUCTURE = (
    "Calling 'structure(NULL, *)' is deprecated, as NULL cannot have attributes.\n"
    "  Consider 'structure(list(), *)' instead."
)


class LogicalNA:
    """R's logical NA, the default of ``cacheable``."""

    def __repr__(self):
        return "NA"

    def __bool__(self):
        raise ValueError("missing value where TRUE/FALSE needed")


NA = LogicalNA()


class KnitAsis:
    """The object ``asis_output`` returns.

    ``value`` is the data. ``attrs`` is ``(name, value)`` pairs in the order
    R keeps after ``attributes<-``. A name that is absent was NULL.
    """

    def __init__(self, value, attrs):
        self.value = value
        self.attrs = list(attrs)

    def attr(self, name):
        for key, val in self.attrs:
            if key == name:
                return val
        return None

    def __repr__(self):
        return f"KnitAsis({self.value!r}, {self.attrs!r})"


def asis_output(x=_MISSING, meta=None, cacheable=NA):
    """Attach class ``knit_asis`` to ``x``.

    ``meta`` is the ``knit_meta`` attribute. None omits it, which is R's NULL.
    ``cacheable`` is the ``knit_cacheable`` attribute. None removes it. The
    default is logical NA.
    """

    if x is _MISSING:
        raise TypeError('argument "x" is missing, with no default')
    value, attrs = _unwrap(x)
    if value is None:
        warnings.warn(_NULL_STRUCTURE, stacklevel=2)
        value = []
    updates = [
        ("class", "knit_asis"),
        ("knit_meta", _copy(meta)),
        ("knit_cacheable", cacheable),
    ]
    return KnitAsis(_copy(value), _set_attributes(attrs, updates))


def _unwrap(x):
    if isinstance(x, KnitAsis):
        return x.value, list(x.attrs)
    return x, []


def _copy(value):
    if isinstance(value, dict):
        return {key: _copy(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_copy(item) for item in value]
    return value


def _set_attributes(existing, updates):
    """Apply ``attributes(x) <- c(attributes(x), updates)``.

    NULL deletes the name. A later value replaces the earlier one and stays
    in the first position of that name.
    """

    merged = list(existing)
    for name, val in updates:
        if val is None:
            merged = [(key, item) for key, item in merged if key != name]
            continue
        replaced = False
        for index, (key, _) in enumerate(merged):
            if key == name:
                merged[index] = (name, val)
                replaced = True
                break
        if not replaced:
            merged.append((name, val))
    return merged
