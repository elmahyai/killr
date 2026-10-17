"""Port of R ``mclust::mclustBICupdate`` (mclust 6.1.3, R/mclust.R).

Merges BIC matrices. The rows are the union of G labels in order of first
appearance, and the columns are the union of model names in the same way.
Where both inputs have a value, the larger one is kept (``pmax`` with
``na.rm = TRUE``). Other cells come from whichever input has them, with the
later input overwriting the earlier one, as R does. The attributes come
from the input whose best BIC is larger; ties keep the first. ``returnCodes``
is dropped.

NULL inputs are passed as ``None``. Any number of inputs is accepted. R's
own code fails for more than three inputs (``args[[-1]]``), so that case
is not reproduced.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from ._bic_objects import has_class, matrix_parts
from .pick_bic import pickBIC

__all__ = ["mclustBICupdate"]

_BIC_CLASSES = ("mclustBIC", "mclustSBIC", "mclustICL")


def _unique(seq):
    return list(dict.fromkeys(seq))


def _top(x: dict[str, Any]) -> float:
    res = pickBIC(x, 1)
    return float(res["values"][0])


def mclustBICupdate(BIC: Any, *args: Any) -> Any:
    if len(args) == 0:
        raise IndexError("subscript out of bounds")
    if len(args) > 1:
        BIC2 = mclustBICupdate(args[0], *args[1:])
    else:
        BIC2 = args[0]
    BIC1 = BIC
    if BIC1 is None:
        return BIC2
    if BIC2 is None:
        return BIC1

    if not (has_class(BIC1, _BIC_CLASSES) and has_class(BIC2, _BIC_CLASSES)):
        raise ValueError("BIC1 and BIC2 must inherit from mclustBIC, mclustSBIC or mclustICL")
    p1 = matrix_parts(BIC1)
    p2 = matrix_parts(BIC2)
    if p1 is None or p2 is None:
        raise ValueError("BIC1 and BIC2 must be matrices")
    v1, rows1, cols1, attrs1 = p1
    v2, rows2, cols2, attrs2 = p2
    for key in ("n", "d"):
        if attrs1.get(key) != attrs2.get(key):
            raise ValueError(f"attributes '{key}' of BIC1 and BIC2 differ")

    G = _unique(rows1 + rows2)
    M = _unique(cols1 + cols2)
    gi = {g: i for i, g in enumerate(G)}
    mi = {m: j for j, m in enumerate(M)}
    out = np.full((len(G), len(M)), np.nan)

    if rows1 and cols1:
        out[np.ix_([gi[g] for g in rows1], [mi[m] for m in cols1])] = v1
    if rows2 and cols2:
        out[np.ix_([gi[g] for g in rows2], [mi[m] for m in cols2])] = v2

    r = _unique(g for g in rows1 if g in set(rows2))
    c = _unique(m for m in cols1 if m in set(cols2))
    if r and c:
        a = v1[np.ix_([rows1.index(g) for g in r], [cols1.index(m) for m in c])]
        b = v2[np.ix_([rows2.index(g) for g in r], [cols2.index(m) for m in c])]
        out[np.ix_([gi[g] for g in r], [mi[m] for m in c])] = np.fmax(a, b)

    t1 = _top(BIC1)
    t2 = _top(BIC2)
    if np.isnan(t1) or np.isnan(t2):
        raise ValueError("missing value where TRUE/FALSE needed")
    chosen = attrs2 if t2 > t1 else attrs1

    result = {k: v for k, v in chosen.items()
              if k not in ("values", "returnCodes", "G", "modelNames", "dim", "dimnames")}
    result["values"] = out
    result["G"] = [float(g) for g in G]
    result["modelNames"] = M
    return result
