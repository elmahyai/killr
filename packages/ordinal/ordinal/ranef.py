"""ranef, VarCorr and condVar methods for clmm objects.

Ports ordinal clmm.ranef.R (ranef.clmm, condVar.clmm) and the varcov / formatVC
helpers from clmm.methods.R. These are pure formatting over the fields a clmm fit
already carries: ``ranef``, ``ST``, ``condVar``, ``gfList`` and ``dims``. The
``nlme`` generic is not needed; R's method only dispatches on it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

import numpy as np

from ordinal.cond_var import ClmmCondVarLike, _format_ranef_blocks, cond_var


@dataclass
class RanefFrame:
    """One grouping factor's random effects (R data.frame, one column per term column)."""

    _columns: dict[str, np.ndarray]
    _row_names: list[str]
    condVar: "RanefFrame | None" = None

    def __getitem__(self, key):
        if isinstance(key, str):
            return self._columns[key]
        raise KeyError(key)

    @property
    def columns(self) -> dict[str, np.ndarray]:
        return self._columns

    @property
    def row_names(self) -> list[str]:
        return self._row_names

    @property
    def nrow(self) -> int:
        return len(self._row_names)

    def to_numpy(self) -> np.ndarray:
        if not self._columns:
            return np.empty((self.nrow, 0))
        return np.column_stack(list(self._columns.values()))


@dataclass
class VarCorrMatrix:
    """A variance-covariance matrix with R's ``stddev`` and ``correlation`` attributes."""

    matrix: np.ndarray
    stddev: np.ndarray
    correlation: np.ndarray | None = None

    def __array__(self, dtype=None):
        return np.asarray(self.matrix, dtype=dtype)


def clmm_like(fit: Mapping[str, Any] | ClmmCondVarLike) -> ClmmCondVarLike:
    """The subset of a clmm fit that ranef/VarCorr/condVar read."""
    if isinstance(fit, ClmmCondVarLike):
        return fit
    dims = fit["dims"]
    matrices = fit.get("ST.matrices") or {fit["ST.name"]: np.array([[fit["ST"]]])}
    colnames = fit.get("ST.colnames") or [["(Intercept)"]]
    return ClmmCondVarLike(
        gf_list_levels=[list(x) for x in fit["gfList"].values()],
        gf_list_names=list(fit["gfList"]),
        gf_assign=np.asarray(fit["assign"], dtype=int),
        st_matrices=[np.asarray(m, dtype=float) for m in matrices.values()],
        st_colnames=[list(c) for c in colnames],
        dims_nretrms=int(dims["nretrms"]),
        dims_nlev_re=np.asarray(dims["nlev.re"], dtype=int),
        dims_qi=np.asarray(dims["qi"], dtype=int),
        ranef=np.asarray(fit["ranef"], dtype=float),
        cond_var=np.asarray(fit["condVar"], dtype=float),
    )


def ranef(object: Mapping[str, Any] | ClmmCondVarLike, condVar: bool = False) -> dict[str, RanefFrame]:
    """ranef.clmm: random effects by grouping factor, optionally with conditional variances."""
    obj = clmm_like(object)
    dims = obj.dims
    nretrms = int(dims["nretrms"])
    nlev_re = np.asarray(dims["nlev.re"], dtype=int).reshape(-1)
    qi = np.asarray(dims["qi"], dtype=int).reshape(-1)

    reind = np.repeat(np.arange(1, nretrms + 1), nlev_re * qi)
    relist = [np.asarray(obj.ranef, dtype=float)[reind == k] for k in range(1, nretrms + 1)]
    out = _format_ranef_blocks(
        relist,
        obj._st_colnames,
        [list(x) for x in obj.gfList],
        obj._gf_assign,
        qi,
        obj._gf_list_names,
    )
    frames = {
        name: RanefFrame(_columns=f._columns, _row_names=f._row_names)
        for name, f in out.items()
    }
    if condVar:
        cv = cond_var(obj)
        for name, frame in frames.items():
            frame.condVar = RanefFrame(_columns=cv[name]._columns, _row_names=cv[name]._row_names)
    return frames


def cond_var_ranef(object: Mapping[str, Any] | ClmmCondVarLike) -> dict[str, RanefFrame]:
    """condVar.clmm: the conditional variances attached by ranef(condVar = TRUE)."""
    return {name: frame.condVar for name, frame in ranef(object, condVar=True).items()}


def var_corr(x: Mapping[str, Any] | ClmmCondVarLike) -> dict[str, VarCorrMatrix]:
    """VarCorr.clmm: variance-covariance matrices of the random effects (varcov)."""
    obj = clmm_like(x)
    res: dict[str, VarCorrMatrix] = {}
    names = list(obj._gf_list_names) if obj._gf_list_names else [str(i + 1) for i in range(len(obj.ST))]
    for name, st in zip(names, obj.ST):
        st = np.asarray(st, dtype=float)
        vc = st @ st.T
        stddev = np.sqrt(np.diag(vc))
        corr = None
        if st.shape[1] > 1:
            corr = vc / stddev[:, None] / stddev[None, :]
            np.fill_diagonal(corr, 1.0)
        res[name] = VarCorrMatrix(matrix=vc, stddev=stddev, correlation=corr)
    return res


def _format_number(values: np.ndarray, digits: int) -> list[str]:
    """R's format(x, digits=digits) for a numeric vector."""
    return [f"{float(v):.{digits}g}" for v in np.ravel(values)]


def format_vc(varc: Mapping[str, VarCorrMatrix], digits: int = 4) -> tuple[list[list[str]], list[str]]:
    """formatVC: the printed VarCorr table as (rows, column names)."""
    groups: list[str] = []
    names: list[str] = []
    variance: list[str] = []
    stddev: list[str] = []
    for group, vc in varc.items():
        groups.extend([group] + [""] * (len(vc.stddev) - 1))
        names.extend([f"({i + 1})" if len(vc.stddev) > 1 else "(Intercept)" for i in range(len(vc.stddev))])
        variance.extend(_format_number(vc.stddev**2, digits))
        stddev.extend(_format_number(vc.stddev, digits))

    cols = ["Groups", "Name", "Variance", "Std.Dev."]
    rows = [[groups[i], names[i], variance[i], stddev[i]] for i in range(len(groups))]

    lens = [len(vc.stddev) for vc in varc.values()]
    if any(n > 1 for n in lens):
        maxlen = max(lens)
        corr_rows: list[list[str]] = []
        for vc in varc.values():
            if vc.correlation is None:
                block = [[""]]
            else:
                block = [
                    ["" if j >= i else f"{vc.correlation[i, j]:.3f}" for j in range(maxlen)]
                    for i in range(vc.correlation.shape[0])
                ]
            block = [row + [""] * (maxlen - len(row)) for row in block]
            corr_rows.extend(block)
        for i, row in enumerate(corr_rows):
            if i < len(rows):
                rows[i].extend(row)
            else:
                rows.append([""] * 4 + row)
        cols.extend(["Corr"] + [""] * (maxlen - 1))
    return rows, cols
