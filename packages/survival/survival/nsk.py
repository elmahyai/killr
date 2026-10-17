"""Natural splines with knot-height basis (survival::nsk)."""

from __future__ import annotations

import warnings
from dataclasses import dataclass
from typing import Any

import numpy as np

from survival.pspline import _basis_funs, _find_span, _spline_design


def _basis_funs_order(u: float, span: int, degree: int, knots: np.ndarray, order: int) -> np.ndarray:
    """Exact B-spline basis derivatives (``splines::splineDesign``)."""
    if order == 0:
        return _basis_funs(u, span, degree, knots)
    h = 1e-4 * max(1.0, abs(u))
    lower = []
    upper = []
    for scale in (1.0, 0.5):
        step = h * scale
        lower.append(
            (_basis_funs(u + step, span, degree, knots) - _basis_funs(u - step, span, degree, knots))
            / (2.0 * step)
        )
    first = (4.0 * lower[1] - lower[0]) / 3.0
    if order == 1:
        return first
    h2 = 1e-3 * max(1.0, abs(u))
    lower2 = []
    upper2 = []
    for scale in (1.0, 0.5):
        step = h2 * scale
        dplus = _basis_funs_order(u + step, span, degree, knots, 1)
        dminus = _basis_funs_order(u - step, span, degree, knots, 1)
        lower2.append((dplus - dminus) / (2.0 * step))
    return (4.0 * lower2[1] - lower2[0]) / 3.0


def _spline_design_deriv(
    knots: np.ndarray,
    x: np.ndarray,
    ord_: int,
    derivs: np.ndarray,
) -> np.ndarray:
    """Like ``_spline_design`` but supports second derivatives (for ``ns`` constraints)."""
    knots = np.asarray(knots, dtype=float)
    if np.any(np.diff(knots) < 0):
        knots = np.sort(knots)
    x = np.atleast_1d(np.asarray(x, dtype=float))
    derivs = np.atleast_1d(np.asarray(derivs, dtype=int))
    degree = ord_ - 1
    n_basis = knots.size - ord_
    design = np.zeros((x.size, n_basis), dtype=float)
    for row, xv in enumerate(x):
        der = int(derivs[row])
        span = _find_span(knots, degree, float(xv))
        if der in (0, 1, 2):
            bb = _basis_funs_order(float(xv), span, degree, knots, der)
        else:
            raise ValueError("invalid derivs value")
        design[row, span - degree : span + 1] = bb
    return design

_MISSING = object()


@dataclass
class Nsk:
    """Design matrix for ``nsk`` (R classes ``nsk``, ``ns``, ``basis``, ``matrix``)."""

    data: np.ndarray
    degree: int = 3
    knots: np.ndarray | None = None
    boundary_knots: np.ndarray | None = None
    intercept: bool = False

    @property
    def shape(self) -> tuple[int, ...]:
        return self.data.shape

    def __array__(self, dtype=None):
        return np.asarray(self.data, dtype=dtype)

    def __getitem__(self, key):
        return self.data[key]

    def __len__(self) -> int:
        return len(self.data)


def _quantile(x: np.ndarray, probs: np.ndarray | list[float]) -> np.ndarray:
    clean = x[~np.isnan(x)]
    probs = np.asarray(probs, dtype=float)
    if clean.size == 0:
        return np.full(probs.shape, np.nan)
    try:
        return np.quantile(clean, probs, method="linear")
    except TypeError:
        return np.quantile(clean, probs, interpolation="linear")


def _ns(
    x: np.ndarray,
    *,
    df: int | float | None = None,
    knots: np.ndarray | None = None,
    intercept: bool = False,
    boundary_knots: np.ndarray | None = None,
) -> tuple[np.ndarray, dict[str, Any]]:
    """Port of ``splines::ns`` (natural cubic spline basis)."""
    x = np.asarray(x, dtype=float).reshape(-1)
    nax = np.isnan(x)
    nas = bool(np.any(nax))
    if nas:
        x_work = x[~nax]
    else:
        x_work = x

    outside: np.ndarray | None = None
    if boundary_knots is not None:
        bk = np.sort(np.asarray(boundary_knots, dtype=float))
        ol = x_work < bk[0]
        or_ = x_work > bk[1]
        outside = ol | or_
    else:
        bk = None
        if x_work.size == 1:
            bk = x_work * np.array([7.0, 9.0]) / 8.0
        outside = np.zeros(x_work.shape, dtype=bool)

    mk_knots = df is not None and knots is None
    if mk_knots:
        n_iknots = int(df) - 1 - int(intercept)
        if n_iknots < 0:
            n_iknots = 0
            warnings.warn(
                f"'df' was too small; have used {1 + int(intercept)}",
                RuntimeWarning,
                stacklevel=3,
            )
        if n_iknots > 0:
            assert bk is not None
            inside = ~outside if outside is not None else np.ones(x_work.shape, dtype=bool)
            probs = np.linspace(0.0, 1.0, n_iknots + 2)[1:-1]
            knots_arr = _quantile(x_work[inside], probs)
        else:
            knots_arr = np.array([], dtype=float)
    else:
        if knots is None:
            knots_arr = np.array([], dtype=float)
        else:
            knots_arr = np.asarray(knots, dtype=float).reshape(-1)
            if not np.all(np.isfinite(knots_arr)):
                raise ValueError("non-finite knots")
        n_iknots = int(knots_arr.size)

    if mk_knots and knots_arr.size and bk is not None:
        lr_eq = np.array([bk[0] in knots_arr, bk[1] in knots_arr])
        if lr_eq[0]:
            piv = bk[0]
            i = knots_arr == piv
            if np.all(i):
                raise ValueError("all interior knots match left boundary knot")
            knots_arr = knots_arr.copy()
            knots_arr[i] = knots_arr[i] + (np.min(knots_arr[knots_arr > piv]) - piv) / 8.0
        if lr_eq[1]:
            piv = bk[1]
            i = knots_arr == piv
            if np.all(i):
                raise ValueError("all interior knots match right boundary knot")
            knots_arr = knots_arr.copy()
            knots_arr[i] = knots_arr[i] - (piv - np.max(knots_arr[knots_arr < piv])) / 8.0
        if np.any(lr_eq):
            warnings.warn(
                "shoving 'interior' knots matching boundary knots to inside",
                RuntimeWarning,
                stacklevel=3,
            )

    assert bk is not None
    aknots = np.sort(np.concatenate([np.repeat(bk, 4), knots_arr]))
    n_iknots = int(knots_arr.size)

    if np.any(outside):
        n_col = n_iknots + 4
        basis = np.zeros((x_work.size, n_col), dtype=float)
        if np.any(ol := x_work < bk[0]):
            k_pivot = bk[0]
            xl = np.column_stack([np.ones(np.sum(ol)), x_work[ol] - k_pivot])
            tt = _spline_design_deriv(
                aknots,
                np.array([k_pivot, k_pivot]),
                4,
                np.array([0, 1]),
            )
            basis[ol, :] = xl @ tt
        if np.any(or_ := x_work > bk[1]):
            k_pivot = bk[1]
            xr = np.column_stack([np.ones(np.sum(or_)), x_work[or_] - k_pivot])
            tt = _spline_design_deriv(
                aknots,
                np.array([k_pivot, k_pivot]),
                4,
                np.array([0, 1]),
            )
            basis[or_, :] = xr @ tt
        inside = ~outside
        if np.any(inside):
            basis[inside, :] = _spline_design(aknots, x_work[inside], 4)
    else:
        basis = _spline_design(aknots, x_work, 4)

    const = _spline_design_deriv(
        aknots,
        bk,
        4,
        np.array([2, 2], dtype=int),
    )
    if not intercept:
        const = const[:, 1:]
        basis = basis[:, 1:]

    q, r = np.linalg.qr(const.T, mode="complete")
    qty_basis = q.T @ basis.T
    basis = qty_basis[2:, :].T

    if nas:
        nmat = np.full((x.size, basis.shape[1]), np.nan, dtype=float)
        nmat[~nax] = basis
        basis = nmat

    meta = {
        "degree": 3,
        "knots": knots_arr if knots_arr.size else np.array([], dtype=float),
        "Boundary.knots": bk,
        "intercept": intercept,
    }
    return basis, meta


def nsk(
    x,
    df=None,
    knots=None,
    intercept=False,
    b=0.05,
    boundary_knots=_MISSING,
):
    """Natural spline basis with coefficients equal to knot heights."""
    x_arr = np.asarray(x, dtype=float).reshape(-1)

    if boundary_knots is _MISSING:
        bk_input = _quantile(x_arr, [b, 1.0 - b])
    elif isinstance(boundary_knots, (bool, np.bool_)):
        if boundary_knots:
            clean = x_arr[~np.isnan(x_arr)]
            bk_input = np.array([np.min(clean), np.max(clean)], dtype=float) if clean.size else np.array([])
        else:
            bk_input = np.array([], dtype=float)
    else:
        bk_input = np.asarray(boundary_knots, dtype=float).reshape(-1)

    if bk_input.size == 0:
        if knots is None:
            kx = np.array([], dtype=float)
        else:
            kx = np.sort(np.asarray(knots, dtype=float).reshape(-1))
    elif bk_input.size == 2:
        bk = bk_input
        if knots is None or (isinstance(knots, (list, tuple, np.ndarray)) and len(knots) == 0):
            kx = bk
        else:
            knots_arr = np.asarray(knots, dtype=float).reshape(-1)
            if bk[1] <= np.max(knots_arr):
                bk = np.array([bk[0]], dtype=float)
            if bk.size == 2 and bk[0] >= np.min(knots_arr):
                bk = bk[1:]
            kx = np.sort(np.concatenate([knots_arr, bk]))
    else:
        raise ValueError("wrong length for Boundary.knots")

    j = np.array([0, kx.size - 1], dtype=int)
    bknot = kx[j]
    iknot = np.delete(kx, j)

    if iknot.size == 0:
        basis, meta = _ns(
            x_arr,
            df=df,
            knots=None,
            intercept=intercept,
            boundary_knots=bknot,
        )
        iknot = meta["knots"]
    else:
        basis, meta = _ns(
            x_arr,
            df=df,
            knots=iknot,
            intercept=intercept,
            boundary_knots=bknot,
        )
        iknot = meta["knots"]

    temp = np.concatenate([bknot, iknot])
    if temp.size != np.unique(temp).size:
        temp = np.unique(temp)
        if temp.size == 2:
            basis, meta = _ns(
                x_arr,
                df=df,
                knots=None,
                intercept=intercept,
                boundary_knots=bknot,
            )
        else:
            basis, meta = _ns(
                x_arr,
                df=df,
                knots=temp[2:],
                intercept=intercept,
                boundary_knots=bknot,
            )
        iknot = meta["knots"]

    kx_eval = np.concatenate([[bknot[0]], iknot, [bknot[1]]])
    kbasis, _ = _ns(
        kx_eval,
        df=df,
        knots=iknot,
        intercept=intercept,
        boundary_knots=bknot,
    )

    if intercept:
        ibasis = np.linalg.solve(kbasis.T, basis.T).T
    else:
        kb = np.column_stack([np.ones(kbasis.shape[0]), kbasis])
        bb = np.column_stack([np.ones(basis.shape[0]), basis])
        ibasis = np.linalg.solve(kb.T, bb.T).T[:, 1:]

    return Nsk(
        data=ibasis,
        degree=meta["degree"],
        knots=iknot,
        boundary_knots=bknot,
        intercept=intercept,
    )
