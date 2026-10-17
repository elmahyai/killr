"""Ridge penalty matrix from survival::ridge."""

from __future__ import annotations

import inspect
import math
from dataclasses import dataclass, field
from typing import Any, Callable

import numpy as np

_MISSING = object()


@dataclass
class RidgePenalty:
    """Matrix predictor block with Cox ridge penalty metadata (R ``coxph.penalty``)."""

    data: np.ndarray
    colnames: list[str]
    pfun: Callable[..., dict[str, Any]]
    cfun: Callable[..., dict[str, Any]]
    pparm: np.ndarray
    varname: list[str]
    diag: bool = True
    cparm: dict[str, Any] = field(default_factory=dict)
    cargs: str | None = None

    @property
    def shape(self) -> tuple[int, ...]:
        return self.data.shape


def _is_missing(value: Any) -> bool:
    return value is _MISSING


def _column_var(values: np.ndarray) -> float:
    clean = values[~np.isnan(values)] if values.dtype.kind == "f" else values
    if clean.size < 2:
        return float("nan") if clean.size == 0 else 0.0
    return float(np.var(clean, ddof=1))


def _match_call_words(caller: Any, args: tuple[Any, ...]) -> list[str]:
    names: list[str] = []
    for arg in args:
        found = ""
        if caller is not None:
            for name, value in caller.f_locals.items():
                if name.startswith("_") or name == "args":
                    continue
                if value is arg:
                    found = name
                    break
        names.append(found)
    return names


def _ridge_xnames(caller: Any, args: tuple[Any, ...], kwargs: dict[str, Any]) -> list[str]:
    """Match ``as.character(parse(text=substitute(cbind(...))))[-1]``."""
    names: list[str] = []
    for arg in args:
        names.extend(_match_call_words(caller, (arg,)))
    for _key, value in kwargs.items():
        names.extend(_match_call_words(caller, (value,)))
    return names


def _as_column(name: str, values: Any) -> tuple[str, np.ndarray]:
    if isinstance(values, np.ndarray):
        arr = np.asarray(values, dtype=float)
    elif isinstance(values, (list, tuple)):
        arr = np.asarray(values, dtype=float)
    else:
        arr = np.asarray([values], dtype=float)
    if arr.ndim != 1:
        raise ValueError("ridge predictors must be vectors")
    colname = name if name else ""
    return colname, arr


def _cbind_columns(
    caller: Any,
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
) -> tuple[np.ndarray, list[str], list[str]]:
    if not args and not kwargs:
        raise ValueError("ridge requires at least one predictor")
    lengths: list[int] = []
    pieces: list[np.ndarray] = []
    colnames: list[str] = []
    argnames = _match_call_words(caller, args)
    for index, arg in enumerate(args):
        colname, column = _as_column(argnames[index] if index < len(argnames) else "", arg)
        if not colname:
            colname = f"V{index + 1}"
        lengths.append(column.size)
        pieces.append(column)
        colnames.append(colname)
    for key, value in kwargs.items():
        _, column = _as_column(key, value)
        lengths.append(column.size)
        pieces.append(column)
        colnames.append(key)
    if any(length != lengths[0] for length in lengths):
        raise ValueError("arguments must be the same length")
    matrix = np.column_stack(pieces)
    xname = _ridge_xnames(caller, args, kwargs)
    if len(xname) < len(colnames):
        xname = xname + [""] * (len(colnames) - len(xname))
    return matrix, colnames, xname[: len(colnames)]


def _frailty_controldf(parms: dict[str, Any], iter_: int, old: dict[str, Any], df: float) -> dict[str, Any]:
    if iter_ == 0:
        theta = parms["guess"]
        history = np.column_stack((parms["thetas"], parms["dfs"]))
        return {"theta": theta, "done": False, "history": history}

    eps = parms.get("eps", 0.1)
    if isinstance(eps, (list, tuple, np.ndarray)) and len(eps) == 0:
        eps = 0.1

    history_old = np.asarray(old["history"], dtype=float)
    thetas = np.concatenate((history_old[:, 0], [old["theta"]]))
    dfs = np.concatenate((history_old[:, 1], [df]))
    nx = len(thetas)

    if nx == 2:
        theta = thetas[0] + (thetas[1] - thetas[0]) * (parms["df"] - dfs[0]) / (dfs[1] - dfs[0])
        if parms["df"] > df:
            theta = theta * 1.5
        return {
            "theta": float(theta),
            "done": False,
            "history": np.column_stack((thetas, dfs)),
            "half": 0,
        }

    done = iter_ > 1 and abs(dfs[nx - 1] - parms["df"]) < eps
    x = thetas
    y = dfs
    target = parms["df"]
    if abs((y[nx - 1] - target) / (y[nx - 2] - target)) > 0.6:
        doing_well = False
    else:
        doing_well = True

    ord_idx = np.argsort(x)
    if (x[0] - x[1]) * (y[0] - y[1]) > 0:
        y_work = y[ord_idx]
    else:
        y_work = -1 * y[ord_idx]
        target = -target
    x = x[ord_idx]

    if np.all(y_work > target):
        b1 = 0
    elif np.all(y_work < target):
        b1 = nx - 3
    else:
        candidates = np.flatnonzero(y_work <= target)
        b1 = int(np.max(candidates))
        half = old.get("half")
        if not doing_well and (half is None or half < 2):
            if parms.get("trace"):
                print(np.column_stack((thetas, dfs)))
                print(f"  bisect:new theta= {np.mean(x[b1 : b1 + 2])}\n")
            return {
                "theta": float(np.mean(x[b1 : b1 + 2])),
                "done": done,
                "history": np.column_stack((thetas, dfs)),
                "half": max(half or 0, 0) + 1,
            }
        if (b1 + 1) == nx - 1 or (b1 > 0 and (target - y_work[b1]) < (y_work[b1 + 1] - target)):
            b1 = b1 - 1

    b2 = b1 + np.array([1, 2])
    xx = np.log(x[b2] - x[b1])
    yy = np.log(y_work[b2] - y_work[b1])
    power = (yy[1] - yy[0]) / (xx[1] - xx[0])
    a = yy[0] - power * xx[0]
    newx = (math.log(target - y_work[b1]) - a) / power
    if parms.get("trace"):
        print(np.column_stack((thetas, dfs)))
        print(f"  new theta= {x[b1] + math.exp(newx)}\n")
    return {
        "theta": float(x[b1] + math.exp(newx)),
        "done": done,
        "history": np.column_stack((thetas, dfs)),
        "half": 0,
    }


def _make_pfun(scale: bool) -> Callable[..., dict[str, Any]]:
    if scale:

        def pfun(coef, theta, ndead, scale_vec):
            coef_arr = np.asarray(coef, dtype=float)
            scale_arr = np.asarray(scale_vec, dtype=float)
            return {
                "penalty": float(np.sum(coef_arr**2 * scale_arr) * theta / 2.0),
                "first": theta * coef_arr * scale_arr,
                "second": theta * scale_arr,
                "flag": False,
            }

    else:

        def pfun(coef, theta, ndead, scale_vec):
            coef_arr = np.asarray(coef, dtype=float)
            return {
                "penalty": float(np.sum(coef_arr**2) * theta / 2.0),
                "first": theta * coef_arr,
                "second": theta,
                "flag": False,
            }

    return pfun


def _theta_cfun(parms: dict[str, Any], iter_: int, history: Any) -> dict[str, Any]:
    return {"theta": parms["theta"], "done": True}


def ridge(
    *args: Any,
    theta: Any = _MISSING,
    df: Any = _MISSING,
    eps: float = 0.1,
    scale: bool = True,
    **kwargs: Any,
) -> RidgePenalty:
    """Build a ridge penalty predictor block for Cox or survreg models."""
    frame = inspect.currentframe()
    caller = frame.f_back if frame is not None else None
    try:
        matrix, colnames, xname = _cbind_columns(caller, args, kwargs)
        nvar = matrix.shape[1]
        vars_ = np.array([_column_var(matrix[:, j]) for j in range(nvar)], dtype=float)

        if not _is_missing(theta) and not _is_missing(df):
            raise ValueError("Only one of df or theta can be specified")

        pfun = _make_pfun(scale)
        varname = [f"ridge({name})" for name in xname]

        if not _is_missing(theta):
            cparm = {"theta": float(theta)}
            cfun: Callable[..., dict[str, Any]] = _theta_cfun
            cargs = None
        else:
            if _is_missing(df):
                df_value = nvar / 2.0
            else:
                df_value = float(df)
            cparm = {
                "df": df_value,
                "eps": eps,
                "thetas": 0.0,
                "dfs": float(nvar),
                "guess": 1.0,
            }
            cfun = _frailty_controldf
            cargs = "df"

        return RidgePenalty(
            data=matrix,
            colnames=colnames,
            pfun=pfun,
            diag=True,
            cfun=cfun,
            cparm=cparm,
            pparm=vars_,
            varname=varname,
            cargs=cargs,
        )
    finally:
        del frame
