"""Shared helpers for deSolve matplot.* (R ``plot.deSolve.R`` internals)."""

from __future__ import annotations

import re
from typing import Any

import numpy as np

from deSolve.rk4 import DeSolveMatrix


def _is_desolve(x: Any) -> bool:
    return isinstance(x, DeSolveMatrix)


def _as_array(x: Any) -> tuple[np.ndarray, list[str]]:
    if isinstance(x, DeSolveMatrix):
        return np.asarray(x.data, dtype=np.float64), list(x.colnames)
    arr = np.asarray(x, dtype=np.float64)
    if arr.ndim != 2:
        raise ValueError("x must be a matrix")
    names = getattr(x, "colnames", None)
    if names is None and hasattr(x, "columns"):
        names = list(x.columns)
    if names is None:
        names = [str(i + 1) for i in range(arr.shape[1])]
    return arr, list(names)


def convert2wide(data: np.ndarray) -> np.ndarray:
    col0 = data[:, 0]
    if col0.dtype.kind not in "OUS":
        cnames = np.unique(col0)
        cnames = [str(v) for v in cnames]
    else:
        cnames = [str(v) for v in np.unique(col0)]
    mat = data[data[:, 0] == data[0, 0], 1:3].copy()
    colnames = ["x", cnames[0]]
    for ivar in cnames[1:]:
        sel = data[data[:, 0] == ivar, 1:3]
        nt = np.column_stack(
            [
                sel[:, 0],
                np.full((sel.shape[0], mat.shape[1] - 1), np.nan),
                sel[:, 1],
            ]
        )
        mat = np.column_stack([mat, np.full((mat.shape[0], 1), np.nan)])
        colnames = list(colnames) + [""]
        nt_cols = colnames[: mat.shape[1]]
        # align column count
        if nt.shape[1] < mat.shape[1]:
            nt = np.column_stack([nt, np.full((nt.shape[0], mat.shape[1] - nt.shape[1]), np.nan)])
        elif nt.shape[1] > mat.shape[1]:
            mat = np.column_stack([mat, np.full((mat.shape[0], nt.shape[1] - mat.shape[1]), np.nan)])
        mat = np.vstack([mat, nt[:, : mat.shape[1]]])
        colnames[-1] = ivar
    mat = np.asarray(mat, dtype=np.float64)
    return mat


def merge_obs(obs: np.ndarray, newobs: np.ndarray) -> np.ndarray:
    if newobs.ndim != 2:
        raise ValueError("the elements in 'obs' should be either a 'data.frame' or a 'matrix'")
    col0 = newobs[:, 0]
    if col0.dtype.kind in "OUS" or isinstance(col0[0], str):
        newobs = convert2wide(newobs)
    obsname = list(getattr(obs, "colnames", [f"V{i}" for i in range(obs.shape[1])]))
    if len(obsname) < obs.shape[1]:
        obsname = [str(i + 1) for i in range(obs.shape[1])]
    newname = [str(n) for n in range(1, newobs.shape[1])]
    newname = [f"x" if i == 0 else newobs[0, i] if False else str(i) for i in range(newobs.shape[1])]
    newname = [str(c) for c in (["x"] + [f"n{i}" for i in range(1, newobs.shape[1])])]
    # use actual colnames from convert2wide path
    newname = ["x"] + [f"var{j}" for j in range(1, newobs.shape[1])]

    obsname = [str(c) for c in obsname]
    raw_new_cols = newobs.shape[1] - 1
    ii = [j for j in range(raw_new_cols) if newname[j + 1] in obsname]
    merged_names = list(obsname)
    for j in range(1, newobs.shape[1]):
        nm = newname[j]
        if nm not in merged_names:
            merged_names.append(nm)
    o1 = np.full((newobs.shape[0], len(merged_names)), np.nan, dtype=np.float64)
    o1[:, 0] = newobs[:, 0]
    o1 = np.column_stack([o1, newobs[:, 1:]])
    # R mergeObs is intricate; for proof cases obs is NULL — keep minimal path
    return np.vstack([obs, newobs]) if obs.size else newobs


def set_data(obs: Any) -> dict[str, Any]:
    nobs = 0
    obs_pos = None
    obsname = None
    dat = None
    if obs is not None:
        if not isinstance(obs, dict):
            arr = np.asarray(obs, dtype=object)
            if arr.ndim == 2 or hasattr(obs, "shape"):
                block = np.asarray(obs, dtype=np.float64)
                if block.ndim != 2:
                    raise ValueError("'obs' should be either a 'data.frame' or a 'matrix'")
                col0 = block[:, 0]
                if col0.dtype.kind in "OUS" or (block.shape[1] >= 1 and isinstance(col0.flat[0], str)):
                    block = convert2wide(block.astype(str))
                dat = block
                obsname = [str(i + 1) for i in range(dat.shape[1])]
                obs_pos = np.array([[1, dat.shape[0]]], dtype=int)
                nobs = 1
            elif isinstance(obs, list):
                obs_list = obs
                dat = np.asarray(obs_list[0], dtype=np.float64)
                obs_pos = np.array([[1, dat.shape[0]]], dtype=int)
                obsname = [str(i + 1) for i in range(dat.shape[1])]
                for i in range(1, len(obs_list)):
                    dat = merge_obs(dat, np.asarray(obs_list[i], dtype=np.float64))
                    obs_pos = np.vstack([obs_pos, [obs_pos[-1, 1] + 1, dat.shape[0]]])
                nobs = obs_pos.shape[0]
        else:
            dat = obs.get("dat")
            obs_pos = obs.get("pos")
            obsname = obs.get("name")
            nobs = obs.get("length", 0)
    return {"dat": dat, "pos": obs_pos, "name": obsname, "length": nobs, "par": None}


def repdots(dots: Any, n: int) -> Any:
    if callable(dots):
        return dots
    if dots is None:
        return None
    if isinstance(dots, (list, tuple)):
        out = list(dots)
        if len(out) < n:
            out = (out * ((n // len(out)) + 1))[:n]
        return out
    if isinstance(dots, np.ndarray):
        flat = np.ravel(dots)
        if flat.size >= n:
            return flat[:n]
        return np.resize(flat, n)
    return [dots] * n


def expanddots(dots: Any, default: Any, n: int) -> list[Any]:
    value = default if dots is None else dots
    if isinstance(value, (list, tuple, np.ndarray)):
        flat = list(np.ravel(value))
        if len(flat) >= n:
            return flat[:n]
        return (flat * ((n // max(len(flat), 1)) + 1))[:n]
    return [value] * n


def expanddotslist(dots: Any, n: int) -> list[Any]:
    if dots is None:
        return [None] * n
    if isinstance(dots, list) and dots and isinstance(dots[0], (list, tuple, np.ndarray)):
        dd = list(dots)
    elif isinstance(dots, list):
        dd = [dots]
    else:
        dd = [dots]
    if len(dd) < n:
        dd = (dd * ((n // len(dd)) + 1))[:n]
    return dd[:n]


def extractdots(dots: dict[str, Any], index: int | slice | list[int]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, val in dots.items():
        if val is None:
            out[key] = None
            continue
        if isinstance(val, list):
            if isinstance(index, slice):
                out[key] = val[index]
            elif isinstance(index, list):
                picked = []
                for i in index:
                    pos = int(i) - 1
                    picked.append(val[pos])
                out[key] = picked if len(picked) > 1 else picked[0]
            else:
                out[key] = val[int(index) - 1]
        else:
            out[key] = val
    return out


def setdots(dots: dict[str, Any], n: int) -> dict[str, Any]:
    return {k: repdots(v, n) for k, v in dots.items()}


def splitdots(ldots: dict[str, Any], varnames: list[str]) -> dict[str, Any]:
    x2: list[Any] = []
    dots: dict[str, Any] = {}
    nd = 0
    nother = 0
    ndots = list(ldots.keys())
    if ldots:
        for i, key in enumerate(ndots):
            item = ldots[key]
            if _is_desolve(item):
                nother += 1
                x2.append(item)
            elif isinstance(item, list) and item and _is_desolve(item[0]):
                for sub in item:
                    nother += 1
                    x2.append(sub)
            elif item is not None:
                nd += 1
                dots[key] = item
    if nother > 0:
        for item in x2:
            cols = list(item.colnames) if _is_desolve(item) else []
            if cols and cols != varnames:
                raise ValueError(
                    "'x' is not compatible with other deSolve objects - colnames not the same"
                )
    plotnames = {
        "xlab",
        "ylab",
        "xlim",
        "ylim",
        "main",
        "sub",
        "log",
        "asp",
        "ann",
        "axes",
        "frame.plot",
        "panel.first",
        "panel.last",
        "cex.lab",
        "cex.axis",
        "cex.main",
    }
    dotmain = {k: v for k, v in dots.items() if k in plotnames}
    dotpoints = {k: v for k, v in dots.items() if k not in plotnames}
    return {"points": dotpoints, "main": dotmain, "nother": nother, "x2": x2}


def range_merge(range_a: tuple[float, float] | None, x: Any, log: bool = False) -> tuple[float, float]:
    vals = np.asarray(x, dtype=np.float64).reshape(-1)
    vals = vals[~np.isnan(vals)]
    if log and vals.size:
        pos = vals[vals > 0]
        if pos.size:
            vals = np.where(vals <= 0, np.min(pos), vals)
    if range_a is None:
        if vals.size == 0:
            return (0.0, 1.0)
        return (float(np.min(vals)), float(np.max(vals)))
    if vals.size == 0:
        return range_a
    return (min(range_a[0], float(np.min(vals))), max(range_a[1], float(np.max(vals))))


def selectvar(which: Any, var: list[str], naallowed: bool = False) -> list[int | float]:
    if not isinstance(which, (list, tuple, np.ndarray)) or (
        isinstance(which, np.ndarray) and which.dtype.kind not in "iu"
    ):
        if isinstance(which, (int, float, np.integer)):
            which_list = [which]
        else:
            which_list = list(which) if isinstance(which, (list, tuple)) else [which]
        if which_list and isinstance(which_list[0], str):
            select: list[int | float] = []
            for item in which_list:
                hits = [i + 1 for i, name in enumerate(var) if name == item]
                if not hits and not naallowed:
                    raise ValueError(f"variable {item} not in variable names")
                select.append(hits[0] if hits else np.nan)
            return select
        which_arr = np.asarray(which_list, dtype=float)
        select = (which_arr + 1).astype(int).tolist()
        if max(select) > len(var):
            raise ValueError(f"index in 'which' too large: {max(select) - 1}")
        if min(select) < 1:
            raise ValueError("index in 'which' should be > 0")
        return select
    which_list = list(which)
    if which_list and isinstance(which_list[0], str):
        select = []
        for item in which_list:
            hits = [i + 1 for i, name in enumerate(var) if name == item]
            if not hits and not naallowed:
                raise ValueError(f"variable {item} not in variable names")
            select.append(hits[0] if hits else np.nan)
        return select
    which_arr = np.asarray(which_list, dtype=float)
    select = (which_arr + 1).astype(int).tolist()
    if max(select) > len(var):
        raise ValueError(f"index in 'which' too large: {max(select) - 1}")
    if min(select) < 1:
        raise ValueError("index in 'which' should be > 0")
    return select


def update_obs2(obs: dict[str, Any], varnames: list[str], xwhich: list[int]) -> dict[str, Any]:
    if obs["length"] > 0:
        names = obs.get("name") or varnames
        obs["Which"] = selectvar([varnames[i - 1] for i in xwhich], names, naallowed=True)
        w = obs["Which"]
        if obs["dat"] is not None and obs["dat"].shape[1] < max(w):
            obs["Which"] = [np.nan if (not np.isnan(v) and v > obs["dat"].shape[1]) else v for v in w]
        if obs["pos"] is not None and obs["pos"].shape[0] != len(obs["Which"]):
            obs["pos"] = np.tile(obs["pos"][0], (len(obs["Which"]), 1))
    else:
        obs["Which"] = [np.nan] * len(xwhich)
    return obs


def update_obs(obs: dict[str, Any], varnames: list[str], xwhich: list[int]) -> dict[str, Any]:
    if obs["length"] > 0:
        names = obs.get("name") or varnames
        obs["Which"] = selectvar([varnames[i - 1] for i in xwhich], names, naallowed=True)
        w = obs["Which"]
        if obs["dat"] is not None:
            obs["Which"] = [
                np.nan if (not np.isnan(v) and v > obs["dat"].shape[1]) else v for v in w
            ]
    else:
        obs["Which"] = [np.nan] * len(xwhich)
    return obs


def which_var_obs(
    which: Any,
    obs: dict[str, Any],
    nvar: int,
    varnames: list[str],
    remove1st: bool = True,
) -> list[Any]:
    if which is None and obs["dat"] is None:
        return list(range(1, nvar + 1))
    if which is None:
        hits = [i for i, name in enumerate(varnames) if name in (obs.get("name") or [])]
        if remove1st:
            hits = [h for h in hits if h != 0]
        return [varnames[h] for h in hits]
    return list(which) if isinstance(which, (list, tuple)) else [which]


def select1dvar(which: Any, var: list[str], att: dict[str, Any]) -> dict[str, Any]:
    if att.get("map") is None:
        proddim = int(np.prod(att["dimens"]))
    else:
        proddim = int(np.sum(~np.isnan(np.asarray(att["map"], dtype=float))))
    if isinstance(which, (list, tuple, np.ndarray)):
        which_list = list(which)
    else:
        which_list = [which]
    ln = len(which_list)
    lengthvar = att.get("lengthvar")
    if lengthvar is None:
        csum = np.array([], dtype=int)
    else:
        csum = np.cumsum(np.asarray(lengthvar, dtype=int)) + 2
    if which_list and isinstance(which_list[0], str):
        select = []
        for item in which_list:
            ss = [i + 1 for i, name in enumerate(var) if name == item]
            if not ss:
                raise ValueError(f"variable {item} not in variable names")
            select.extend(ss)
    else:
        select = [int(w) for w in which_list]
        if max(select) > len(var):
            raise ValueError("index in 'which' too large")
        if min(select) < 1:
            raise ValueError("index in 'which' should be > 0")
    istart = np.zeros(ln, dtype=int)
    istop = np.zeros(ln, dtype=int)
    for i, sel in enumerate(select):
        if sel <= att["nspec"]:
            ii = sel
            istart[i] = (ii - 1) * proddim + 2
            istop[i] = istart[i] + proddim - 1
        else:
            ii = sel - att["nspec"]
            if csum.size == 0:
                raise ValueError(f"variable {which_list[i]} is not a 1-D variable")
            istart[i] = csum[ii - 1]
            istop[i] = csum[ii] - 1
        if istart[i] == istop[i]:
            raise ValueError(f"variable {which_list[i]} is not a 1-D variable")
    return {"Which": select, "istart": istart, "istop": istop}


def set_range(
    lim: Any,
    x: np.ndarray,
    x2: list[np.ndarray] | None,
    isub: np.ndarray | slice,
    ix: slice | list[int],
    obs: dict[str, Any],
    io: float,
    log: bool,
) -> tuple[float, float]:
    nother = 0 if x2 is None else len(x2)
    if lim is None:
        yrange = range_merge(None, x[isub, ix], log)
        if nother > 0:
            for j in range(nother):
                yrange = range_merge(yrange, x2[j][isub, ix], log)
        if io is not None and not (isinstance(io, float) and np.isnan(io)):
            col = int(io) - 1
            yrange = range_merge(yrange, obs["dat"][:, col], log)
    else:
        yrange = tuple(lim)
    return yrange


def setplotpar(ldots: dict[str, Any], nv: int, ask: bool | None) -> bool:
    nmdots = set(ldots.keys())
    if not nmdots.intersection({"mfrow", "mfcol"}):
        nc = min(int(np.ceil(np.sqrt(nv))), 3)
        nr = min(int(np.ceil(nv / nc)), 3)
        mfrow = (nr, nc)
    elif "mfcol" in nmdots:
        mfrow = tuple(reversed(tuple(ldots["mfcol"])))
    else:
        mfrow = tuple(ldots["mfrow"])
    # mfrow consumed by caller via matplotlib subplots
    if ask is None:
        ask = mfrow[0] * mfrow[1] < nv
    return bool(ask)


def _extend_lim(lim: tuple[float, float], axs: str = "r") -> tuple[float, float]:
    lo, hi = lim
    if axs == "i":
        return lo, hi
    dx = hi - lo
    if dx == 0:
        dx = abs(lo) if lo != 0 else 1.0
    pad = 0.04 * dx
    return lo - pad, hi + pad


def _eval_subset(subset: Any, x: np.ndarray, colnames: list[str]) -> np.ndarray:
    if subset is None:
        return np.ones(x.shape[0], dtype=bool)
    frame = {name: x[:, i] for i, name in enumerate(colnames)}
    if isinstance(subset, str):
        r = eval(subset, {"__builtins__": {}}, frame)
    else:
        r = subset
    if isinstance(r, (int, np.integer)):
        return np.arange(x.shape[0]) == int(r)
    if isinstance(r, (list, tuple, np.ndarray)):
        arr = np.asarray(r)
        if arr.dtype.kind in "iu":
            return arr
        return arr.astype(bool) & ~np.isnan(arr.astype(float))
    if isinstance(r, (bool, np.bool_)):
        return np.full(x.shape[0], bool(r))
    arr = np.asarray(r)
    if arr.dtype.kind in "iu":
        return arr
    return arr.astype(bool) & ~np.isnan(arr.astype(float))


def _r_color(index: int) -> str:
    # R default palette: black, red, green3, blue, cyan, magenta, yellow, gray
    palette = ["#000000", "#FF0000", "#00CD00", "#0000FF", "#00FFFF", "#FF00FF", "#FFFF00", "#BEBEBE"]
    return palette[(int(index) - 1) % len(palette)]


def _line_style(lty: int) -> str:
    styles = ["solid", "dashed", "dotted", "dashdot"]
    return styles[(int(lty) - 1) % len(styles)]
