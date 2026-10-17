"""Sliding windows, from slider 0.3.3.

Period windows and the data-frame binders stay out of this slice. They need
warp and vctrs::vec_rbind / vec_cbind. `block()` uses warp boundaries.
"""

from __future__ import annotations

from slider.engine import hop_apply, hop_index_apply, slide_apply, slide_index_apply
from slider.errors import SliderError
from slider.summary import (
    slide_all,
    slide_any,
    slide_index_all,
    slide_index_any,
    slide_index_max,
    slide_index_mean,
    slide_index_min,
    slide_index_prod,
    slide_index_sum,
    slide_max,
    slide_mean,
    slide_min,
    slide_prod,
    slide_sum,
)

__all__ = [
    "pslide_period_int",
    "pslide_period_chr",
    "slide_period2_dbl",
    "slide_period2",
    "pslide_period",
    "slide_period",
    "block",
    "hop",
    "hop2",
    "hop2_vec",
    "hop_index",
    "hop_index2",
    "hop_index2_vec",
    "hop_index_vec",
    "hop_vec",
    "phop",
    "phop_index",
    "phop_index_vec",
    "phop_vec",
    "pslide",
    "pslide_chr",
    "pslide_dbl",
    "pslide_index",
    "pslide_index_chr",
    "pslide_index_dbl",
    "pslide_index_int",
    "pslide_index_lgl",
    "pslide_index_vec",
    "pslide_int",
    "pslide_lgl",
    "pslide_vec",
    "slide",
    "slide2",
    "slide2_chr",
    "slide2_dbl",
    "slide2_int",
    "slide2_lgl",
    "slide2_vec",
    "slide_all",
    "slide_any",
    "slide_chr",
    "slide_dbl",
    "slide_index",
    "slide_index2",
    "slide_index2_chr",
    "slide_index2_dbl",
    "slide_index2_int",
    "slide_index2_lgl",
    "slide_index2_vec",
    "slide_index_all",
    "slide_index_any",
    "slide_index_chr",
    "slide_index_dbl",
    "slide_index_int",
    "slide_index_lgl",
    "slide_index_max",
    "slide_index_mean",
    "slide_index_min",
    "slide_index_prod",
    "slide_index_sum",
    "slide_index_vec",
    "slide_int",
    "slide_lgl",
    "slide_max",
    "slide_mean",
    "slide_min",
    "slide_prod",
    "slide_sum",
    "slide_vec",
    "slider_minus",
    "slider_plus",
]


def _slide(groups, f, args, before, after, step, complete, kind, atomic, simplify):
    return slide_apply(
        groups, f, args, before, after, step, complete, kind=kind, atomic=atomic, simplify=simplify
    )


def slide(x, f, *args, before=0, after=0, step=1, complete=False):
    """Slide a function along one vector. The result is a list."""
    return _slide([x], f, args, before, after, step, complete, "list", False, False)


def slide_vec(x, f, *args, before=0, after=0, step=1, complete=False, ptype=None):
    """Slide and simplify each size-1 result to one vector."""
    return _slide([x], f, args, before, after, step, complete, None, True, True)


def slide_dbl(x, f, *args, before=0, after=0, step=1, complete=False):
    """Slide and cast each result to a double."""
    return _slide([x], f, args, before, after, step, complete, "dbl", True, False)


def slide_int(x, f, *args, before=0, after=0, step=1, complete=False):
    """Slide and cast each result to an integer."""
    return _slide([x], f, args, before, after, step, complete, "int", True, False)


def slide_lgl(x, f, *args, before=0, after=0, step=1, complete=False):
    """Slide and cast each result to a logical."""
    return _slide([x], f, args, before, after, step, complete, "lgl", True, False)


def slide_chr(x, f, *args, before=0, after=0, step=1, complete=False):
    """Slide and cast each result to a string."""
    return _slide([x], f, args, before, after, step, complete, "chr", True, False)


def slide2(x, y, f, *args, before=0, after=0, step=1, complete=False):
    """Slide a function along two vectors of the same size."""
    return _slide([x, y], f, args, before, after, step, complete, "list", False, False)


def slide2_vec(x, y, f, *args, before=0, after=0, step=1, complete=False, ptype=None):
    return _slide([x, y], f, args, before, after, step, complete, None, True, True)


def slide2_dbl(x, y, f, *args, before=0, after=0, step=1, complete=False):
    return _slide([x, y], f, args, before, after, step, complete, "dbl", True, False)


def slide2_int(x, y, f, *args, before=0, after=0, step=1, complete=False):
    return _slide([x, y], f, args, before, after, step, complete, "int", True, False)


def slide2_lgl(x, y, f, *args, before=0, after=0, step=1, complete=False):
    return _slide([x, y], f, args, before, after, step, complete, "lgl", True, False)


def slide2_chr(x, y, f, *args, before=0, after=0, step=1, complete=False):
    return _slide([x, y], f, args, before, after, step, complete, "chr", True, False)


def pslide(items, f, *args, before=0, after=0, step=1, complete=False):
    """Slide a function along every vector in a list."""
    return _slide(list(items), f, args, before, after, step, complete, "list", False, False)


def pslide_vec(items, f, *args, before=0, after=0, step=1, complete=False, ptype=None):
    return _slide(list(items), f, args, before, after, step, complete, None, True, True)


def pslide_dbl(items, f, *args, before=0, after=0, step=1, complete=False):
    return _slide(list(items), f, args, before, after, step, complete, "dbl", True, False)


def pslide_int(items, f, *args, before=0, after=0, step=1, complete=False):
    return _slide(list(items), f, args, before, after, step, complete, "int", True, False)


def pslide_lgl(items, f, *args, before=0, after=0, step=1, complete=False):
    return _slide(list(items), f, args, before, after, step, complete, "lgl", True, False)


def pslide_chr(items, f, *args, before=0, after=0, step=1, complete=False):
    return _slide(list(items), f, args, before, after, step, complete, "chr", True, False)


def _hop(groups, starts, stops, f, args, kind, atomic, simplify):
    return hop_apply(groups, starts, stops, f, args, kind=kind, atomic=atomic, simplify=simplify)


def hop(x, starts, stops, f, *args):
    """Apply a function on the inclusive ranges `starts` to `stops`."""
    return _hop([x], starts, stops, f, args, "list", False, False)


def hop_vec(x, starts, stops, f, *args, ptype=None):
    return _hop([x], starts, stops, f, args, None, True, True)


def hop2(x, y, starts, stops, f, *args):
    return _hop([x, y], starts, stops, f, args, "list", False, False)


def hop2_vec(x, y, starts, stops, f, *args, ptype=None):
    return _hop([x, y], starts, stops, f, args, None, True, True)


def phop(items, starts, stops, f, *args):
    return _hop(list(items), starts, stops, f, args, "list", False, False)


def phop_vec(items, starts, stops, f, *args, ptype=None):
    return _hop(list(items), starts, stops, f, args, None, True, True)


def _slide_index(groups, index, f, args, before, after, complete, kind, atomic, simplify):
    return slide_index_apply(
        groups, index, f, args, before, after, complete, kind=kind, atomic=atomic, simplify=simplify
    )


def slide_index(x, i, f, *args, before=0, after=0, complete=False):
    """Slide along `x`, sizing each window from the index `i`."""
    return _slide_index([x], i, f, args, before, after, complete, "list", False, False)


def slide_index_vec(x, i, f, *args, before=0, after=0, complete=False, ptype=None):
    return _slide_index([x], i, f, args, before, after, complete, None, True, True)


def slide_index_dbl(x, i, f, *args, before=0, after=0, complete=False):
    return _slide_index([x], i, f, args, before, after, complete, "dbl", True, False)


def slide_index_int(x, i, f, *args, before=0, after=0, complete=False):
    return _slide_index([x], i, f, args, before, after, complete, "int", True, False)


def slide_index_lgl(x, i, f, *args, before=0, after=0, complete=False):
    return _slide_index([x], i, f, args, before, after, complete, "lgl", True, False)


def slide_index_chr(x, i, f, *args, before=0, after=0, complete=False):
    return _slide_index([x], i, f, args, before, after, complete, "chr", True, False)


def slide_index2(x, y, i, f, *args, before=0, after=0, complete=False):
    return _slide_index([x, y], i, f, args, before, after, complete, "list", False, False)


def slide_index2_vec(x, y, i, f, *args, before=0, after=0, complete=False, ptype=None):
    return _slide_index([x, y], i, f, args, before, after, complete, None, True, True)


def slide_index2_dbl(x, y, i, f, *args, before=0, after=0, complete=False):
    return _slide_index([x, y], i, f, args, before, after, complete, "dbl", True, False)


def slide_index2_int(x, y, i, f, *args, before=0, after=0, complete=False):
    return _slide_index([x, y], i, f, args, before, after, complete, "int", True, False)


def slide_index2_lgl(x, y, i, f, *args, before=0, after=0, complete=False):
    return _slide_index([x, y], i, f, args, before, after, complete, "lgl", True, False)


def slide_index2_chr(x, y, i, f, *args, before=0, after=0, complete=False):
    return _slide_index([x, y], i, f, args, before, after, complete, "chr", True, False)


def pslide_index(items, i, f, *args, before=0, after=0, complete=False):
    return _slide_index(list(items), i, f, args, before, after, complete, "list", False, False)


def pslide_index_vec(items, i, f, *args, before=0, after=0, complete=False, ptype=None):
    return _slide_index(list(items), i, f, args, before, after, complete, None, True, True)


def pslide_index_dbl(items, i, f, *args, before=0, after=0, complete=False):
    return _slide_index(list(items), i, f, args, before, after, complete, "dbl", True, False)


def pslide_index_int(items, i, f, *args, before=0, after=0, complete=False):
    return _slide_index(list(items), i, f, args, before, after, complete, "int", True, False)


def pslide_index_lgl(items, i, f, *args, before=0, after=0, complete=False):
    return _slide_index(list(items), i, f, args, before, after, complete, "lgl", True, False)


def pslide_index_chr(items, i, f, *args, before=0, after=0, complete=False):
    return _slide_index(list(items), i, f, args, before, after, complete, "chr", True, False)


def _hop_index(groups, index, starts, stops, f, args, kind, atomic, simplify):
    return hop_index_apply(
        groups, index, starts, stops, f, args, kind=kind, atomic=atomic, simplify=simplify
    )


def hop_index(x, i, starts, stops, f, *args):
    """Apply a function on index ranges that may extend past `i`."""
    return _hop_index([x], i, starts, stops, f, args, "list", False, False)


def hop_index_vec(x, i, starts, stops, f, *args, ptype=None):
    return _hop_index([x], i, starts, stops, f, args, None, True, True)


def hop_index2(x, y, i, starts, stops, f, *args):
    return _hop_index([x, y], i, starts, stops, f, args, "list", False, False)


def hop_index2_vec(x, y, i, starts, stops, f, *args, ptype=None):
    return _hop_index([x, y], i, starts, stops, f, args, None, True, True)


def phop_index(items, i, starts, stops, f, *args):
    return _hop_index(list(items), i, starts, stops, f, args, "list", False, False)


def phop_index_vec(items, i, starts, stops, f, *args, ptype=None):
    return _hop_index(list(items), i, starts, stops, f, args, None, True, True)


def slider_plus(x, y):
    """Add an index and an `.after` value. The default is ordinary addition."""
    return _arith(x, y, lambda left, right: left + right)


def slider_minus(x, y):
    """Subtract a `.before` value from an index. The default is ordinary subtraction."""
    return _arith(x, y, lambda left, right: left - right)


def _arith(x, y, op):
    from slider.engine import as_vector, recycle

    left_scalar = not isinstance(x, (list, tuple))
    right_scalar = not isinstance(y, (list, tuple))
    values = recycle([as_vector(x), as_vector(y)])
    out = [op(left, right) for left, right in zip(values[0], values[1])]
    if left_scalar and right_scalar:
        return out[0]
    return out


def block(x, i, period, every=1, origin=None):
    """Split `x` into period blocks using warp boundaries."""
    from slider.block import block as _block
    return _block(x, i, period, every=every, origin=origin)


def slide_period(x, i, period, f, *args, before=0, after=0, complete=False):
    from slider.slide_period import slide_period as _slide_period
    return _slide_period(x, i, period, f, *args, before=before, after=after, complete=complete)


def pslide_period(items, i, period, f, *args, every=1, origin=None, before=0, after=0, complete=False):
    from slider.pslide_period import pslide_period as _fn
    return _fn(
        items, i, period, f, *args,
        every=every, origin=origin, before=before, after=after, complete=complete,
    )


def pslide_period_dbl(items, i, period, f, *args, every=1, origin=None, before=0, after=0, complete=False):
    from slider.pslide_period_dbl import pslide_period_dbl as _fn
    return _fn(items, i, period, f, *args, every=every, origin=origin, before=before, after=after, complete=complete)


def slide_period2(x, y, i, period, f, *args, every=1, origin=None, before=0, after=0, complete=False):
    from slider.slide_period2 import slide_period2 as _fn
    return _fn(x, y, i, period, f, *args, every=every, origin=origin, before=before, after=after, complete=complete)


def pslide_period_int(items, i, period, f, *args, every=1, origin=None, before=0, after=0, complete=False):
    from slider.pslide_period_int import pslide_period_int as _fn
    return _fn(items, i, period, f, *args, every=every, origin=origin, before=before, after=after, complete=complete)

def pslide_period_chr(items, i, period, f, *args, every=1, origin=None, before=0, after=0, complete=False):
    from slider.pslide_period_chr import pslide_period_chr as _fn
    return _fn(items, i, period, f, *args, every=every, origin=origin, before=before, after=after, complete=complete)


def slide_period2_dbl(x, y, i, period, f, *args, every=1, origin=None, before=0, after=0, complete=False):
    from slider.slide_period2_dbl import slide_period2_dbl as _fn
    return _fn(x, y, i, period, f, *args, every=every, origin=origin, before=before, after=after, complete=complete)
