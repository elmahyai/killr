"""Sort strings with embedded numbers (gtools 3.9.5 ``mixedsort``)."""

from __future__ import annotations

import numpy as np

from gtools.mixedorder import mixedorder


def mixedsort(
    x,
    decreasing: bool = False,
    na_last: bool | None = True,
    blank_last: bool | None = False,
    numeric_type: str = "decimal",
    roman_case: str = "upper",
    scientific: bool = True,
):
    """Return ``x`` sorted with embedded numeric sections in numeric order."""
    ord = mixedorder(
        x,
        decreasing=decreasing,
        na_last=na_last,
        blank_last=blank_last,
        numeric_type=numeric_type,
        roman_case=roman_case,
        scientific=scientific,
    )
    if ord is None:
        return None
    return _index_1based(x, ord)


def _index_1based(x, ord):
    idx = np.asarray(ord, dtype=np.intp).reshape(-1) - 1

    if isinstance(x, str):
        return x

    if isinstance(x, np.ndarray):
        if x.ndim == 0:
            return x.item()
        vec = x.ravel(order="F")
        return vec.take(idx)

    if isinstance(x, (list, tuple)):
        seq = list(x)
        return [seq[i] for i in idx]

    return x
