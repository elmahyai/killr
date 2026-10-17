"""Translation of ``mclustICL`` (mclust 6.1.3, R/icl.R).

``mclustICL`` fits the BIC matrix with ``mclustBIC``. Then, for every fitted
cell (one number of components and one model), it refits that model with
``summaryMclustBIC`` (``summaryMclustBICn`` when the BIC has a noise start) and
takes ``icl.Mclust`` of the refit: the BIC of the refit plus twice the sum of
``log(z)`` over the hard classes. A one-component cell keeps its BIC value.

The result has the layout of the BIC matrix: one row per G, one column per
model name, with ``criterion = "ICL"`` and ``class = "mclustICL"``. It is a
dict with the matrix under ``"values"`` and the R attributes under their R
names, as ``mclustBIC`` returns its object.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import numpy as np

from .bic_family import mclustBIC
from .summary_mclust_bic import summaryMclustBIC, summaryMclustBICn

__all__ = ["mclustICL", "icl_mclust"]


def _get(x: Any, name: str, default: Any = None) -> Any:
    if isinstance(x, Mapping):
        return x.get(name, default)
    return getattr(x, name, default)


def icl_mclust(object_: Any) -> float:
    """R ``icl.Mclust``: ``object$bic + 2 * sum(C * ifelse(z > 0, log(z), 0))``.

    ``C`` marks the first largest ``z`` in each row. A missing ``z`` is one
    column of ones, as R takes it.
    """
    n = int(_get(object_, "n"))
    z = _get(object_, "z")
    z = np.ones((n, 1)) if z is None else np.asarray(z, dtype=float)
    if z.ndim == 1:
        z = z[:, None]
    bic = float(np.ravel(np.asarray(_get(object_, "bic"), dtype=float))[0])
    hard = np.zeros_like(z)
    hard[np.arange(z.shape[0]), np.argmax(z, axis=1)] = 1.0
    positive = z > 0
    logz = np.where(positive, np.log(np.where(positive, z, 1.0)), 0.0)
    return bic + 2.0 * float(np.sum(hard * logz))


def _label(value: Any) -> str:
    """R ``as.character`` for a G value: integers print without a decimal point."""
    if isinstance(value, (float, np.floating)) and float(value).is_integer():
        return str(int(value))
    return str(value)


def _matrix_names(x: Any) -> tuple[np.ndarray, list[str], list[str]]:
    """Values with their row (G) and column (model) labels, as R's dimnames."""
    values = np.atleast_2d(np.asarray(_get(x, "values", x), dtype=float))
    rows = _get(x, "G")
    cols = _get(x, "modelNames")
    row_labels = ([str(i + 1) for i in range(values.shape[0])] if rows is None
                  else [_label(v) for v in np.atleast_1d(rows)])
    col_labels = ([str(i + 1) for i in range(values.shape[1])] if cols is None
                  else [str(v) for v in np.atleast_1d(cols)])
    return values, row_labels, col_labels


def _fit_bic(data: Any, G: Any, modelNames: Any, initialization: Any,
             x: Any, kwargs: dict[str, Any]) -> dict[str, Any]:
    """``mclustBIC`` as R's ``mclustICL`` calls it, with ``x`` supplied or not.

    R's ``mclustBIC`` with ``x`` returns the requested subset of ``x`` when every
    requested G and model is in ``x``. Otherwise it fits the cells ``x`` does
    not hold and keeps ``x``'s values for the rest. That second case is done
    here: the full grid is fitted without ``x``, then ``x``'s cells replace
    the fitted ones, which gives the same values as R.
    """
    if x is None:
        return mclustBIC(data, G=G, modelNames=modelNames, initialization=initialization,
                         **kwargs)
    x_vals, x_rows, x_cols = _matrix_names(x)
    want_g = x_rows if G is None else [_label(g) for g in np.atleast_1d(G)]
    want_m = x_cols if modelNames is None else [str(m) for m in np.atleast_1d(modelNames)]
    if all(g in x_rows for g in want_g) and all(m in x_cols for m in want_m):
        return mclustBIC(data, G=G, modelNames=modelNames, initialization=initialization,
                         x=x, **kwargs)

    all_g = sorted({*want_g, *x_rows}, key=float)
    all_m = list(dict.fromkeys([*want_m, *x_cols]))
    full = mclustBIC(data, G=[float(g) for g in all_g], modelNames=all_m,
                     initialization=initialization, **kwargs)
    f_vals, f_rows, f_cols = _matrix_names(full)
    f_codes = _get(full, "returnCodes")
    x_codes = _get(x, "returnCodes")

    values = np.full((len(want_g), len(want_m)), np.nan)
    codes = np.full(values.shape, np.nan)
    for i, g in enumerate(want_g):
        for j, m in enumerate(want_m):
            if g in f_rows and m in f_cols:
                values[i, j] = f_vals[f_rows.index(g), f_cols.index(m)]
                if f_codes is not None:
                    codes[i, j] = np.asarray(f_codes, dtype=float)[
                        f_rows.index(g), f_cols.index(m)]
            if g in x_rows and m in x_cols:
                values[i, j] = x_vals[x_rows.index(g), x_cols.index(m)]
                if x_codes is not None:
                    codes[i, j] = np.asarray(x_codes, dtype=float)[
                        x_rows.index(g), x_cols.index(m)]

    out: dict[str, Any] = {
        "values": values,
        "G": [int(float(g)) for g in want_g],
        "modelNames": want_m,
        "returnCodes": codes,
    }
    for key in ("prior", "control", "initialization", "warn", "n", "d", "oneD", "Vinv"):
        value = _get(full, key)
        if value is None:
            value = _get(x, key)
        if value is not None:
            out[key] = value
    return out


def mclustICL(data: Any, G: Any = None, modelNames: Any = None,
              initialization: Any = None, x: Any = None, **kwargs: Any) -> dict[str, Any]:
    """ICL for each number of components and model, as R's ``mclustICL``.

    All arguments are passed to ``mclustBIC`` (``prior``, ``control``,
    ``Vinv``, ``warn`` and ``verbose`` come in through ``kwargs``). When ``x``
    is an earlier ``mclustICL`` result, its values are copied for the G and
    model names they share, as R does, and only the other cells are refitted.
    """
    bic = _fit_bic(data, G, modelNames, initialization, x, kwargs)
    bic_values = np.atleast_2d(np.asarray(bic["values"], dtype=float))
    rows = [_label(v) for v in np.atleast_1d(bic["G"])]
    cols = [str(v) for v in np.atleast_1d(bic["modelNames"])]

    icl = np.full(bic_values.shape, np.nan)
    if x is not None:
        # R: r <- match(as.character(G), rownames(x), nomatch = 0), then ICL[r, c] <- BIC[r, c].
        # The positions are taken from x's rownames and used on ICL, as R does.
        _, x_rows, x_cols = _matrix_names(x)
        r = [x_rows.index(g) + 1 for g in rows if g in x_rows]
        c = [x_cols.index(m) + 1 for m in cols if m in x_cols]
        if r and c:
            if max(r) > icl.shape[0] or max(c) > icl.shape[1]:
                raise IndexError("subscript out of bounds")
            ri = [k - 1 for k in r]
            ci = [k - 1 for k in c]
            icl[np.ix_(ri, ci)] = bic_values[np.ix_(ri, ci)]

    noise = _get(_get(bic, "initialization") or {}, "noise")
    summarise = summaryMclustBICn if noise is not None else summaryMclustBIC
    for i, g in enumerate(rows):
        for j, model in enumerate(cols):
            if np.isnan(bic_values[i, j]):
                continue  # not fitted
            if not np.isnan(icl[i, j]):
                continue  # already available from x
            summary = summarise(bic, data, G=int(float(g)), modelNames=model)
            icl[i, j] = icl_mclust(summary)

    out: dict[str, Any] = {
        "values": icl,
        "G": [int(float(g)) for g in rows],
        "modelNames": cols,
    }
    for key in ("prior", "control", "initialization", "warn", "n", "d", "oneD",
                "returnCodes", "Vinv"):
        value = _get(bic, key)
        if value is not None:
            out[key] = value
    out["criterion"] = "ICL"
    out["class"] = "mclustICL"
    return out
