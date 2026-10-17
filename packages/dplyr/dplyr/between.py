"""`between()` from dplyr 1.2.1.

Inclusive bounds: cast `x`, `left`, and `right` to their common type, recycle
the bounds to `x`, then keep the values that sit between them. `NULL` is not
a vector. A length other than 1 does not recycle, which is vctrs rather than
base R.
"""

from __future__ import annotations

from dplyr._vec import (
    as_vec,
    between_result,
    cast_common,
    compare,
    recycle_to,
)


def _show(value):
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, str):
        return value
    return str(value)


def _check_dots(args, kwargs):
    if not args and not kwargs:
        return
    lines = ["`...` must be empty.", "✖ Problematic argument:"]
    if args:
        lines.append(f"• ..1 = {_show(args[0])}")
        lines.append("ℹ Did you forget to name an argument?")
    else:
        name, value = next(iter(kwargs.items()))
        lines.append(f"• {name} = {_show(value)}")
    raise ValueError("\n".join(lines))


def between(x, left, right, *args, ptype=None, **kwargs):
    """True where `x` is inside `[left, right]` after a common-type cast.

    `left` and `right` recycle to the size of `x`. `ptype` sets that common
    type. An ordered factor compared with text is alphabetical unless `ptype`
    is the ordered factor, in which case the level order is used.
    """
    _check_dots(args, kwargs)
    casted = cast_common(
        [("x", as_vec(x)), ("left", as_vec(left)), ("right", as_vec(right))],
        ptype,
    )
    values, lower, upper = casted
    size = values.size()
    lower = recycle_to(lower, size, "left")
    upper = recycle_to(upper, size, "right")
    return between_result(compare(values, lower), compare(values, upper))
