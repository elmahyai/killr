"""signTabulate, ported from matrixStats 1.5.0."""

from __future__ import annotations

import numpy as np

import signtabulate as _signtabulate

from matrixstats._values import prepare_idxs, prepare_x


def signTabulate(x, idxs=None):
    """Count negative, zero, positive, and missing values.

    Mirrors ``matrixStats::signTabulate``. ``idxs`` is 1-based, as in R.
    ``None`` selects every element. The result is a one-dimensional integer
    array. A double vector is ordered ``-1``, ``0``, ``+1``, ``NA``, ``-Inf``,
    ``+Inf``. An integer vector stops after ``NA`` and has no infinity counts.

    ``-Inf`` is included in ``-1``, and ``+Inf`` is included in ``+1``. A
    double missing value is NaN. An integer missing value is ``None`` or R's
    integer NA sentinel. An out-of-bounds or missing subscript counts as missing.
    """
    if isinstance(x, (bool, np.bool_)):
        raise ValueError("Argument 'x' cannot be logical")
    storage, values = prepare_x(x)
    if storage == "logical":
        raise ValueError("Argument 'x' cannot be logical")
    if storage not in ("double", "integer"):
        raise ValueError("Argument 'x' must be of type integer or numeric")
    idxs_kind, idxs_values = prepare_idxs(idxs)
    return _signtabulate.sign_tabulate(values, storage, idxs_values, idxs_kind)
