"""Recursive residuals, the R engine from ``recresid_r``.

The default engine refits with ``lm.fit`` until the rank-one update matches
those coefficients, then keeps the update. The comparison is ``all.equal``
at ``sqrt(.Machine$double.eps) / k``.
"""

import numpy as np

from strucchange.model import coef_zero, design_from_formula, lm_fit, match_arg, x_inverse


def _all_equal_numeric(target, current, tolerance):
    """``isTRUE(all.equal(as.vector(target), as.vector(current), tolerance))``."""
    target = np.asarray(target, dtype=float).ravel()
    current = np.asarray(current, dtype=float).ravel()
    if target.shape != current.shape:
        return False
    target_na = np.isnan(target)
    current_na = np.isnan(current)
    if np.any(target_na != current_na):
        return False
    equal = target_na | (target == current)
    if np.all(equal):
        return True
    target = target[~equal]
    current = current[~equal]
    n = target.size
    scale = float(np.sum(np.abs(target) / n))
    if not (np.isfinite(scale) and scale > tolerance):
        scale = 1.0
    difference = float(np.sum(np.abs(target - current) / (n * scale)))
    return bool(np.isfinite(difference) and difference <= tolerance)


def recresid_r(x, y, start, end, tol, qr_tol):
    """R implementation of the recursive residual recursion."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float).ravel()
    n = int(end)
    q = int(start) - 1
    k = x.shape[1]
    rval = np.zeros(n - q, dtype=float)

    fm = lm_fit(x[:q, :], y[:q], tol=qr_tol)
    x1 = x_inverse(fm, k)
    betar = coef_zero(fm.coefficients)
    xr = np.array(x[q, :], dtype=float, copy=True)
    fr = float(1.0 + xr @ x1 @ xr)
    rval[0] = (y[q] - float(xr @ betar)) / np.sqrt(fr)
    check = True

    if (q + 1) < n:
        for r in range(q + 1, n):
            nona = bool(np.all(np.isfinite(fm.coefficients)))
            x1 = x1 - (x1 @ np.outer(xr, xr) @ x1) / fr
            betar = betar + (x1 @ xr) * rval[r - q - 1] * np.sqrt(fr)
            if check:
                fm = lm_fit(x[:r, :], y[:r], tol=qr_tol)
                nona = (
                    nona
                    and bool(np.all(np.isfinite(betar)))
                    and bool(np.all(np.isfinite(fm.coefficients)))
                )
                if nona and _all_equal_numeric(fm.coefficients, betar, tol):
                    check = False
                x1 = x_inverse(fm, k)
                betar = coef_zero(fm.coefficients)
            xr = np.array(x[r, :], dtype=float, copy=True)
            fr = float(1.0 + xr @ x1 @ xr)
            product = xr * betar
            keep = np.isfinite(product)
            rval[r - q] = (y[r] - float(np.sum(product[keep]))) / np.sqrt(fr)
    return rval


def recresid(x, y=None, start=None, end=None, tol=None, qr_tol=1e-7, engine="R", data=None):
    """Recursive residuals. ``engine="R"`` is the default; the C engine is not ported."""
    engine = match_arg(engine, ("R", "C"))
    if isinstance(x, str):
        y, x, _names = design_from_formula(x, data)
    else:
        x = np.asarray(x, dtype=float)
        if x.ndim == 1:
            x = x.reshape(-1, 1)
        if y is None:
            raise ValueError("recresid needs a response")
        y = np.asarray(y, dtype=float).ravel()
    n, k = x.shape
    if start is None:
        start = k + 1
    if end is None:
        end = n
    start = int(start)
    end = int(end)
    if not (start > k and start <= n):
        raise ValueError("start > ncol(x) & start <= nrow(x) is not TRUE")
    if not (end >= start and end <= n):
        raise ValueError("end >= start & end <= nrow(x) is not TRUE")
    if tol is None:
        tol = float(np.sqrt(np.finfo(float).eps) / k)
    if engine == "C":
        raise NotImplementedError("recresid C engine")
    return recresid_r(x, y, start=start, end=end, tol=float(tol), qr_tol=float(qr_tol))
