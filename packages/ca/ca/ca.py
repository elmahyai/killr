"""Simple correspondence analysis."""

import numpy as np


def ca(obj, nd=None, suprow=None, supcol=None, subsetrow=None, subsetcol=None, **_):
    """Compute simple correspondence analysis for a two-way frequency table."""
    nmat = np.asarray(obj, dtype=float)
    if nmat.ndim != 2:
        raise ValueError("obj must be a two-dimensional table")
    nrow0, ncol0 = nmat.shape
    suprow = _indices(suprow, nrow0)
    supcol = _indices(supcol, ncol0)
    subsetrow = _indices(subsetrow, nrow0)
    subsetcol = _indices(subsetcol, ncol0)
    active_rows = [i for i in range(nrow0) if i not in (suprow or [])]
    active_cols = [j for j in range(ncol0) if j not in (supcol or [])]
    if subsetrow is not None:
        active_rows = [i for i in active_rows if i in subsetrow]
    if subsetcol is not None:
        active_cols = [j for j in active_cols if j in subsetcol]
    active = nmat[np.ix_(active_rows, active_cols)]
    total = active.sum()
    if total <= 0:
        raise ValueError("table must have positive total")
    p = active / total
    rm = p.sum(axis=1)
    cm = p.sum(axis=0)
    s = (p - np.outer(rm, cm)) / np.sqrt(np.outer(rm, cm))
    u, sv, vt = np.linalg.svd(s, full_matrices=False)
    maxdim = min(s.shape) - (0 if subsetrow is not None or subsetcol is not None else 1)
    maxdim = max(0, min(maxdim, len(sv)))
    if nd is None or (isinstance(nd, float) and np.isnan(nd)):
        nd_out = maxdim
    else:
        nd_out = min(int(nd), maxdim)
    sv = sv[:maxdim]
    u = u[:, :maxdim]
    v = vt.T[:, :maxdim]
    rowcoord = u / np.sqrt(rm)[:, None]
    colcoord = v / np.sqrt(cm)[:, None]
    rowinertia = (s * s).sum(axis=1)
    colinertia = (s * s).sum(axis=0)
    rowdist = np.sqrt(rowinertia / rm)
    coldist = np.sqrt(colinertia / cm)
    rowmass = np.full(nrow0, np.nan)
    colmass = np.full(ncol0, np.nan)
    rowmass[active_rows] = rm
    colmass[active_cols] = cm
    rowcoord_all = np.full((nrow0, maxdim), np.nan)
    colcoord_all = np.full((ncol0, maxdim), np.nan)
    rowcoord_all[active_rows] = rowcoord
    colcoord_all[active_cols] = colcoord
    rowdist_all = np.full(nrow0, np.nan)
    coldist_all = np.full(ncol0, np.nan)
    rowdist_all[active_rows] = rowdist
    coldist_all[active_cols] = coldist
    # Passive coordinates use the active cloud and the same singular values.
    if suprow:
        for i in suprow:
            prof = nmat[i, active_cols] / nmat[i, active_cols].sum()
            rowcoord_all[i] = ((prof / cm) - 1) @ v / sv
            rowdist_all[i] = np.sqrt(np.sum(((prof - cm) ** 2) / cm))
    if supcol:
        for j in supcol:
            prof = nmat[active_rows, j] / nmat[active_rows, j].sum()
            colcoord_all[j] = ((prof / rm) - 1) @ u / sv
            coldist_all[j] = np.sqrt(np.sum(((prof - rm) ** 2) / rm))
    return {
        "sv": sv, "nd": nd_out, "rownames": list(range(nrow0)),
        "rowmass": rowmass, "rowdist": rowdist_all, "rowinertia": rowinertia,
        "rowcoord": rowcoord_all[:, :nd_out], "rowsup": suprow or [],
        "colnames": list(range(ncol0)), "colmass": colmass, "coldist": coldist_all,
        "colinertia": colinertia, "colcoord": colcoord_all[:, :nd_out],
        "colsup": supcol or [], "N": nmat,
    }


def _indices(value, n):
    if value is None:
        return None
    a = np.asarray(value)
    if a.ndim == 0 and (np.isnan(a) if a.dtype.kind == "f" else False):
        return None
    if a.size == 0:
        return None
    out = a.astype(int).ravel()
    if np.all((out >= 1) & (out <= n)):
        out = out - 1
    if np.any((out < 0) | (out >= n)):
        raise IndexError("index out of bounds")
    return sorted(set(out.tolist()))
