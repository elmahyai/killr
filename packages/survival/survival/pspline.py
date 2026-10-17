"""Penalized spline basis (survival::pspline)."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Callable

import numpy as np

from survival.wtest import coxph_wtest


@dataclass
class Pspline:
    """Spline basis matrix with Cox penalty metadata (R class ``pspline``)."""

    data: np.ndarray
    intercept: bool = False
    nterm: int = 0
    degree: int = 3
    boundary_knots: np.ndarray | None = None
    df: float = 4.0
    combine: np.ndarray | None = None
    varname: list[str] = field(default_factory=list)
    pparm: np.ndarray | None = None
    pfun: Callable[..., dict[str, Any]] | None = None
    printfun: Callable[..., dict[str, Any]] | None = None
    cfun: Callable[..., dict[str, Any]] | None = None
    cparm: dict[str, Any] = field(default_factory=dict)
    cargs: tuple[str, ...] | tuple = ()
    diag: bool = False
    penalty: bool = True
    method: str = "df"

    @property
    def shape(self):
        return self.data.shape

    def __array__(self, dtype=None):
        return np.asarray(self.data, dtype=dtype)

    def __getitem__(self, key):
        return self.data[key]

    def __len__(self) -> int:
        return len(self.data)


def _as_float_vector(x: Any) -> np.ndarray:
    arr = np.asarray(x, dtype=float).reshape(-1)
    return arr


def _is_na_scalar(value: float) -> bool:
    return isinstance(value, (float, np.floating)) and math.isnan(float(value))


def _basis_funs(u: float, span: int, degree: int, knots: np.ndarray) -> np.ndarray:
    """Nonzero B-spline basis values (Algorithm A2.2, Piegl & Tiller)."""
    values = np.zeros(degree + 1, dtype=float)
    values[0] = 1.0
    left = np.zeros(degree + 1, dtype=float)
    right = np.zeros(degree + 1, dtype=float)
    for j in range(1, degree + 1):
        left[j] = u - knots[span + 1 - j]
        right[j] = knots[span + j] - u
        saved = 0.0
        for r in range(j):
            temp = values[r] / (right[r + 1] + left[j - r])
            values[r] = saved + right[r + 1] * temp
            saved = left[j - r] * temp
        values[j] = saved
    return values


def _basis_deriv(u: float, span: int, degree: int, knots: np.ndarray) -> np.ndarray:
    step = 1e-8 * max(1.0, abs(u))
    return (_basis_funs(u + step, span, degree, knots) - _basis_funs(u - step, span, degree, knots)) / (
        2.0 * step
    )


def _find_span(knots: np.ndarray, degree: int, x: float) -> int:
    if x == knots[degree]:
        return degree
    n_basis = knots.size - degree - 1
    if x >= knots[n_basis]:
        return n_basis - 1
    return int(np.searchsorted(knots, x, side="right") - 1)


def _spline_design(
    knots: np.ndarray,
    x: np.ndarray,
    ord_: int,
    derivs: np.ndarray | None = None,
    *,
    outer_ok: bool = False,
) -> np.ndarray:
    """Port of ``splines::splineDesign`` (``spline.des`` design matrix)."""
    knots = np.asarray(knots, dtype=float)
    if np.any(np.diff(knots) < 0):
        knots = np.sort(knots)
    x = np.atleast_1d(np.asarray(x, dtype=float))
    if derivs is None:
        derivs = np.zeros(x.size, dtype=int)
    else:
        derivs = np.atleast_1d(np.asarray(derivs, dtype=int))
    if derivs.size != x.size:
        raise ValueError("length of derivs must match x")

    degree = ord_ - 1
    xmin = knots[degree]
    xmax = knots[-degree - 1]
    n_basis = knots.size - ord_
    if n_basis < 0:
        raise ValueError("order too large for knot sequence")
    if not outer_ok and (np.any(x < xmin) or np.any(x > xmax)):
        raise ValueError(
            "the 'x' data must be in the range "
            f"{xmin} to {xmax} unless you set 'outer.ok = TRUE'"
        )

    design = np.zeros((x.size, n_basis), dtype=float)
    for row, xv in enumerate(x):
        der = int(derivs[row])
        if outer_ok and (xv < xmin or xv > xmax):
            continue
        if der not in (0, 1):
            raise ValueError("invalid derivs value")
        span = _find_span(knots, degree, float(xv))
        if der == 0:
            bb = _basis_funs(float(xv), span, degree, knots)
        else:
            bb = _basis_deriv(float(xv), span, degree, knots)
        design[row, span - degree : span + 1] = bb
    return design


def _spline_des(
    knots: np.ndarray,
    x: np.ndarray,
    ord_: int,
    derivs: np.ndarray | None = None,
    *,
    outer_ok: bool = False,
) -> dict[str, Any]:
    if derivs is None:
        derivs_arr = np.zeros(np.size(x), dtype=int)
    else:
        derivs_arr = np.atleast_1d(np.asarray(derivs, dtype=int))
    knots = np.asarray(knots, dtype=float)
    if np.any(np.diff(knots) < 0):
        knots = np.sort(knots)
    design = _spline_design(knots, x, ord_, derivs_arr, outer_ok=outer_ok)
    return {
        "knots": knots,
        "order": ord_,
        "derivs": derivs_arr,
        "design": design,
    }


def _second_diff_penalty(nvar: int) -> np.ndarray:
    k = nvar - 2
    if k <= 0:
        return np.zeros((nvar, nvar), dtype=float)
    d = np.zeros((k, nvar), dtype=float)
    for i in range(k):
        d[i, i : i + 3] = (1.0, -2.0, 1.0)
    return d.T @ d


def _frailty_brent(x: np.ndarray, y: np.ndarray, lower=None, upper=None) -> float:
    x = np.asarray(x, dtype=float).reshape(-1)
    y = np.asarray(y, dtype=float).reshape(-1)
    n = x.size
    if y.size != n:
        raise ValueError("Length mismatch for x and y")
    if n < 3:
        return float(np.mean(x))
    order = np.argsort(x, kind="mergesort")
    xx = x[order]
    yy = y[order]
    best = int(np.where(yy == np.max(yy))[0][0])
    if np.sum(yy == np.max(yy)) > 1:
        raise ValueError("Ties for max(y), I surrender")
    if best == 0:
        new = xx[0] - 3.0 * (xx[1] - xx[0])
        if lower is not None and new < lower:
            above = xx[xx > lower]
            new = lower + (float(np.min(above)) - lower) / 10.0
        return float(new)
    if best == n - 1:
        new = xx[n - 1] + 3.0 * (xx[n - 1] - xx[n - 2])
        if upper is not None and new > upper:
            below = xx[xx < upper]
            new = upper + (float(np.max(below)) - upper) / 10.0
        return float(new)
    xx3 = xx[(best - 1) : (best + 2)]
    yy3 = yy[(best - 1) : (best + 2)]
    temp1 = (xx3[1] - xx3[0]) ** 2 * (yy3[1] - yy3[2]) - (xx3[1] - xx3[2]) ** 2 * (
        yy3[1] - yy3[0]
    )
    temp2 = (xx3[1] - xx3[0]) * (yy3[1] - yy3[2]) - (xx3[1] - xx3[2]) * (yy3[1] - yy3[0])
    new = xx3[1] - 0.5 * temp1 / temp2
    if new < xx3[0] or new > xx3[2] or (n > 4 and (new - x[n - 1]) > 0.5 * abs(x[n - 2] - x[n - 3])):
        if (xx3[1] - xx3[0]) > (xx3[2] - xx3[1]):
            return float(xx3[1] - 0.38 * (xx3[1] - xx3[0]))
        return float(xx3[1] + 0.32 * (xx3[2] - xx3[1]))
    return float(new)


def _frailty_controldf(parms, iter_, old, df):
    if iter_ == 0:
        theta = parms["guess"]
        history = np.column_stack((parms["thetas"], parms["dfs"]))
        return {"theta": theta, "done": False, "history": history}

    eps = parms.get("eps", 0.1)
    if eps is None or (isinstance(eps, (list, np.ndarray)) and len(eps) == 0):
        eps = 0.1

    thetas = np.concatenate((old["history"][:, 0], [old["theta"]]))
    dfs = np.concatenate((old["history"][:, 1], [df]))
    nx = thetas.size
    if nx == 2:
        theta = thetas[0] + (thetas[1] - thetas[0]) * (parms["df"] - dfs[0]) / (dfs[1] - dfs[0])
        if parms["df"] > df:
            theta *= 1.5
        history = np.column_stack((thetas, dfs))
        return {"theta": float(theta), "done": False, "history": history, "half": 0}

    done = iter_ > 1 and abs(dfs[nx - 1] - parms["df"]) < eps
    x = thetas.copy()
    y = dfs.copy()
    target = parms["df"]
    if abs((y[nx - 1] - target) / (y[nx - 2] - target)) > 0.6:
        doing_well = False
    else:
        doing_well = True
    order = np.argsort(x, kind="mergesort")
    if (x[0] - x[1]) * (y[0] - y[1]) > 0:
        y = y[order]
    else:
        y = -y[order]
        target = -target
    x = x[order]
    if np.all(y > target):
        b1 = 0
    elif np.all(y < target):
        b1 = nx - 3
    else:
        below = np.where(y <= target)[0]
        b1 = int(np.max(below))
        half = old.get("half")
        if not doing_well and (half is None or half < 2):
            return {
                "theta": float(np.mean(x[b1 : b1 + 2])),
                "done": done,
                "history": np.column_stack((thetas, dfs)),
                "half": (0 if half is None else half) + 1,
            }
        if (b1 + 1) == nx or (b1 > 0 and (target - y[b1]) < (y[b1 + 1] - target)):
            b1 -= 1
    b2 = b1 + np.array([1, 2])
    xx = np.log(x[b2] - x[b1])
    yy = np.log(y[b2] - y[b1])
    power = (yy[1] - yy[0]) / (xx[1] - xx[0])
    a = yy[0] - power * xx[0]
    newx = (math.log(target - y[b1]) - a) / power
    return {
        "theta": float(x[b1] + math.exp(newx)),
        "done": done,
        "history": np.column_stack((thetas, dfs)),
        "half": 0,
    }


def _frailty_controlaic(parms, iter_, old, n, df, loglik):
    if iter_ == 0:
        init = parms.get("init")
        theta = 0.005 if init is None else float(init[0])
        return {"theta": theta, "done": False}

    correct = bool(parms.get("caic", False))
    if n < df + 2:
        dfc = (df - n) + (df + 1) * df / 2.0 - 1.0
    else:
        dfc = -1.0 + (df + 1) / (1.0 - ((df + 2) / n))

    if iter_ == 1:
        history = np.array([[old["theta"], loglik, df, loglik - df, loglik - dfc]])
        init = parms.get("init")
        theta = 1.0 if init is None or len(init) < 2 else float(init[1])
        return {"theta": theta, "done": False, "history": history}

    history = np.vstack(
        (
            old["history"],
            np.array([[old["theta"], loglik, df, loglik - df, loglik - dfc]]),
        )
    )
    if iter_ == 2:
        return {"theta": float(np.mean(history[:, 0])), "done": False, "history": history}

    aic = history[:, 4] if correct else history[:, 3]
    done = abs(1.0 - aic[iter_ - 1] / aic[iter_ - 2]) < parms["eps"]
    x = history[:, 0]
    if x[iter_ - 1] == np.max(aic) and x[iter_ - 1] == np.max(x):
        newtheta = 2.0 * float(np.max(x))
    else:
        newtheta = _frailty_brent(x, aic, lower=parms.get("lower"), upper=parms.get("upper"))
    return {"theta": float(newtheta), "done": bool(done), "history": history}


def _pfun(coef, theta, n, dmat):
    coef = np.asarray(coef, dtype=float).reshape(-1)
    dmat = np.asarray(dmat, dtype=float)
    if theta >= 1:
        return {"penalty": 100.0 * (1.0 - theta), "flag": True}
    if theta <= 0:
        lam = 0.0
    else:
        lam = theta / (1.0 - theta)
    quad = float(coef @ dmat @ coef)
    return {
        "penalty": quad * lam / 2.0,
        "first": np.asarray(dmat @ coef, dtype=float) * lam,
        "second": np.asarray(dmat, dtype=float) * lam,
        "flag": False,
    }


def _pchisq(q, df, *, lower_tail=False):
    if df <= 0:
        return math.nan
    # survival uses stats::pchisq; reuse cox_zph-style approximation for df=1
    if df == 1:
        root = math.sqrt(max(float(q), 0.0))
        pnorm = 0.5 * (1.0 + math.erf(root / math.sqrt(2.0)))
        upper = 2.0 * (1.0 - pnorm)
        return 1.0 - upper if lower_tail else upper
    from survival.gamma import _pgamma_raw

    shape = df / 2.0
    x = q / 2.0
    cdf = _pgamma_raw(x, shape)
    return cdf if lower_tail else 1.0 - cdf


def _make_printfun(knots, nvar, boundary_knots):
    cbase = knots[1:nvar] + (boundary_knots[0] - knots[0])

    def printfun(coef, var, var2, df, history, cbase=cbase):
        coef = np.asarray(coef, dtype=float).reshape(-1)
        var = np.asarray(var, dtype=float)
        var2 = np.asarray(var2, dtype=float)
        test1 = coxph_wtest(var, coef)["test"]
        xmat = np.column_stack((np.ones(cbase.size), cbase))
        xsig = coxph_wtest(var, xmat)["solve"]
        cmat = coxph_wtest(xmat.T @ xsig, xsig.T)["solve"][1, :]
        linear = float(np.sum(cmat * coef))
        lvar1 = float(cmat @ var @ cmat)
        lvar2 = float(cmat @ var2 @ cmat)
        test2 = linear**2 / lvar1 if lvar1 else math.nan
        dfree = max(0.5, df - 1.0)
        row1 = np.array(
            [
                linear,
                math.sqrt(lvar1),
                math.sqrt(lvar2),
                test2,
                1.0,
                _pchisq(test2, 1, lower_tail=False),
            ]
        )
        diff = test1 - test2
        row2 = np.array(
            [
                math.nan,
                math.nan,
                math.nan,
                diff,
                df - 1.0,
                _pchisq(diff, dfree, lower_tail=False),
            ]
        )
        coef_mat = np.vstack((row1, row2))
        nn = history["thetas"].shape[0] if isinstance(history, dict) and "thetas" in history else 0
        if nn:
            theta = history["thetas"][nn - 1, 0]
        else:
            theta = history.get("theta", math.nan)
        return {"coef": coef_mat, "history": f"Theta= {theta:g}"}

    return printfun


def pspline(
    x,
    df=4,
    theta=None,
    nterm=None,
    degree=3,
    eps=0.1,
    method=None,
    boundary_knots=None,
    intercept=False,
    penalty=True,
    combine=None,
    **kwargs,
):
    """Build a penalized spline basis for Cox or survreg models."""
    has_theta = theta is not None
    if has_theta:
        method = "fixed"
        if theta <= 0 or theta >= 1:
            raise ValueError("Invalid value for theta")
    elif df == 0 or (method is not None and method == "aic"):
        method = "aic"
        nterm = 15
        if eps == 0.1:
            eps = 1e-5
    else:
        method = "df"
        if df <= 1:
            raise ValueError("Too few degrees of freedom")
        if nterm is None:
            nterm = 2.5 * df
        if df > nterm:
            raise ValueError(f"`nterm' too small for df={df}")

    xvec = _as_float_vector(x)
    keepx = ~np.isnan(xvec)
    if nterm is None:
        nterm = 2.5 * df
    nterm = int(round(float(nterm)))
    if nterm < 3:
        raise ValueError("Too few basis functions")

    if boundary_knots is not None:
        bk = np.asarray(boundary_knots, dtype=float).reshape(-1)
        if bk.size != 2 or not np.issubdtype(bk.dtype, np.number):
            raise ValueError("Invalid values for Boundary.knots")
        if bk[0] >= bk[1]:
            raise ValueError("Invalid values for Boundary.knots")
        boundary = bk.copy()
        xwork = xvec[keepx]
        outside = (xwork < boundary[0]) | (xwork > boundary[1])
    else:
        xwork = xvec[keepx]
        if xwork.size == 0:
            raise ValueError("no non-missing x")
        boundary = np.array([float(np.min(xwork)), float(np.max(xwork))], dtype=float)
        outside = np.zeros(xwork.size, dtype=bool)

    dx = (boundary[1] - boundary[0]) / nterm
    knots = np.concatenate(
        (
            boundary[0] + dx * np.arange(-degree, nterm, dtype=float),
            boundary[1] + dx * np.arange(0, degree + 1, dtype=float),
        )
    )
    ord_ = degree + 1
    ncols = nterm + degree

    if np.any(outside):
        newx = np.zeros((xwork.size, ncols), dtype=float)
        outl = xwork < boundary[0]
        outr = xwork > boundary[1]
        inside = ~(outl | outr)
        if np.any(outl):
            tt = _spline_des(knots, np.array([boundary[0], boundary[0]]), ord_, np.array([0, 1]))
            edge = np.column_stack((np.ones(np.sum(outl)), xwork[outl] - boundary[0]))
            newx[outl, :] = edge @ tt["design"]
        if np.any(outr):
            tt = _spline_des(knots, np.array([boundary[1], boundary[1]]), ord_, np.array([0, 1]))
            edge = np.column_stack((np.ones(np.sum(outr)), xwork[outr] - boundary[1]))
            newx[outr, :] = edge @ tt["design"]
        if np.any(inside):
            newx[inside, :] = _spline_des(knots, xwork[inside], ord_)["design"]
    else:
        newx = _spline_des(knots, xwork, ord_, outer_ok=True)["design"]

    if not np.all(keepx):
        temp = np.full((keepx.size, newx.shape[1]), np.nan, dtype=float)
        temp[keepx, :] = newx
        newx = temp

    if combine is not None:
        combine = np.asarray(combine, dtype=float).reshape(-1)
        if np.any(combine != np.floor(combine)) or np.any(combine < 0) or np.any(np.diff(combine) < 0):
            raise ValueError("combine must be an increasing vector of positive integers")
        ctemp = combine if intercept else np.concatenate(([0.0], combine))
        if ctemp.size != newx.shape[1]:
            raise ValueError("wrong length for combine")
        uc = np.sort(np.unique(ctemp))
        tmat = np.zeros((newx.shape[1], uc.size), dtype=float)
        for i, level in enumerate(uc):
            tmat[ctemp == level, i] = 1.0
        newx = newx @ tmat

    nvar = newx.shape[1]
    dmat = _second_diff_penalty(nvar)

    xname = "x"
    if intercept:
        names = [f"ps({xname}){i + 1}" for i in range(nvar)]
    else:
        newx = newx[:, 1:]
        dmat = dmat[1:, 1:]
        names = [f"ps({xname}){i}" for i in range(3, nvar + 2)]

    if not penalty:
        return Pspline(
            newx,
            intercept=intercept,
            nterm=nterm,
            degree=degree,
            boundary_knots=boundary,
            combine=combine,
            penalty=False,
        )

    printfun = _make_printfun(knots, nvar, boundary)

    if method == "fixed":
        meta = {
            "pfun": _pfun,
            "printfun": printfun,
            "pparm": dmat,
            "diag": False,
            "cparm": {"theta": theta},
            "varname": names,
            "cfun": lambda parms, iter_, old: {"theta": parms["theta"], "done": True},
        }
    elif method == "df":
        meta = {
            "pfun": _pfun,
            "printfun": printfun,
            "diag": False,
            "cargs": ("df",),
            "cparm": {
                "df": df,
                "eps": eps,
                "thetas": np.array([1.0, 0.0]),
                "dfs": np.array([1.0, float(nterm)]),
                "guess": 1.0 - df / nterm,
                **kwargs,
            },
            "pparm": dmat,
            "varname": names,
            "cfun": _frailty_controldf,
        }
    else:
        meta = {
            "pfun": _pfun,
            "printfun": printfun,
            "pparm": dmat,
            "diag": False,
            "cargs": ("neff", "df", "plik"),
            "cparm": {"eps": eps, "init": np.array([0.5, 0.95]), "lower": 0.0, "upper": 1.0, **kwargs},
            "varname": names,
            "cfun": _frailty_controlaic,
        }

    return Pspline(
        newx,
        intercept=intercept,
        nterm=nterm,
        degree=degree,
        boundary_knots=boundary,
        df=df,
        combine=combine,
        method=method,
        penalty=True,
        **meta,
    )
