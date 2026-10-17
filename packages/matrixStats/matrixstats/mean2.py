"""Fast mean over a subset of vector elements, ported from matrixStats."""

from __future__ import annotations

import mean2 as _mean2

from matrixstats._values import as_logical, prepare_idxs, prepare_x


def mean2(x, idxs=None, na_rm=False, refine=True):
    """Average all or a subset of values.

    Mirrors ``matrixStats::mean2``. ``idxs`` is 1-based, as in R. ``None``
    selects every element. ``refine`` defaults to true and, for double ``x``,
    adds a second pass over the residuals. Integer and logical data stay on
    the one-pass average. An empty mean is ``nan``. Double missing values are
    ``nan``.
    """
    na_rm = as_logical(na_rm, "na.rm")
    refine = as_logical(refine, "refine")
    storage, values = prepare_x(x)
    idxs_kind, idxs_values = prepare_idxs(idxs)
    x_kind = "double" if storage == "double" else "integer"
    return float(_mean2.mean2(values, x_kind, na_rm, refine, idxs_values, idxs_kind))
