"""The quantile regression process (tau outside [0, 1]) and the functions that read it.

``rq_fit_br_process`` is the Barrodale-Roberts parametric sweep of R's ``rq.fit.br``
for ``tau`` outside ``[0, 1]``. It runs in the Rust kernel ``quantreg_br_kernel``
(crates/quantreg_br, the port of ``rqbr.f``) and returns the ``sol`` and ``dsol``
parts of an R ``rq.process`` object. ``ranks`` and ``predict_rq_process`` read
those two parts, as R's ``ranks`` and ``predict.rq.process`` do.
"""

from __future__ import annotations

import warnings

import numpy as np
from scipy.special import ndtri

from quantreg.fit import _rank

_SQRT_2PI = float(np.sqrt(2.0 * np.pi))

# R's .Machine$double.eps^(2/3), the tolerance rq.fit.br passes to rqbr.
_TOL = float(np.finfo(float).eps ** (2.0 / 3.0))

_FLAG_MESSAGES = {
    1: "Solution may be nonunique",
    2: "Premature end - possible conditioning problem in x",
}


def _as_matrix(x):
    array = np.asarray(x, dtype=float)
    if array.ndim == 1:
        array = array.reshape(-1, 1)
    return array


def _qnorm(p):
    """R's qnorm for the standard normal."""
    return ndtri(p)


def _dnorm(x):
    """R's dnorm for the standard normal."""
    return np.exp(-0.5 * x * x) / _SQRT_2PI


def _colon(a: int, b: int) -> np.ndarray:
    """R's ``a:b`` on 1-based indices, which runs downward when b < a."""
    if b >= a:
        return np.arange(a, b + 1)
    return np.arange(a, b - 1, -1)


def rq_fit_br_process(x, y):
    """The quantile regression process for all tau, as R's rq.fit.br(tau = -1).

    Returns a dict with ``sol`` ((p + 3) x J: rows tau, Qbar, Obj.Fun, then the
    coefficients at each breakpoint), ``dsol`` (n x J: the duals), ``lsol`` (J),
    and ``info`` (the rqbr flag, 0 when clean).
    """
    from quantreg_br_kernel import rqbr_process

    design = _as_matrix(x)
    response = np.asarray(y, dtype=float).reshape(-1)
    n, p = design.shape
    if response.shape[0] != n:
        raise ValueError("x and y don't match n")
    if _rank(design) < p:
        raise ValueError("Singular design matrix")
    sol, dsol, lsol, info = rqbr_process(design, response, _TOL)
    if info in _FLAG_MESSAGES:
        warnings.warn(_FLAG_MESSAGES[info], stacklevel=2)
    return {
        "sol": np.asarray(sol, dtype=float),
        "dsol": np.asarray(dsol, dtype=float),
        "lsol": int(lsol),
        "info": int(info),
        "x": design,
        "y": response,
    }


def _interp_dual(taus, dsol, target):
    """R: w * dsol[, j + 1] + (1 - w) * dsol[, j] at the tau value ``target``, with j = sum(taus < target)."""
    j = int(np.sum(taus < target))
    w = (target - taus[j - 1]) / (taus[j] - taus[j - 1])
    return w * dsol[:, j] + (1.0 - w) * dsol[:, j - 1]


def ranks(v, score="wilcoxon", tau=0.5, trim=None):
    """Rank scores of the quantile process, as R's ``ranks``.

    ``v`` is a dict with ``sol`` and ``dsol`` as returned by ``rq_fit_br_process``.
    Returns a dict with ``ranks`` (length n) and ``A2``, the constant the score
    test uses.
    """
    sol = np.asarray(v["sol"], dtype=float)
    dsol = np.asarray(v["dsol"], dtype=float)
    taus_all = sol[0]
    if trim is not None and np.size(trim) > 0 and score != "wilcoxon":
        raise ValueError("trimming is only permitted with the wilcoxon score functions")

    if score == "wilcoxon":
        phibar = 0.5
        a2 = 1.0 / 12.0
        u = taus_all.copy()
        d = dsol
        # R expands a single trim value to c(trim, 1 - trim), but the trimming block
        # is the else of that test, so a single value changes nothing. Only two
        # values trim the process, and that is what this branch does.
        trim_values = np.atleast_1d(np.asarray(trim, dtype=float)) if trim is not None else np.array([])
        if trim_values.size > 2:
            raise ValueError("Only 2 trimming proportions allowed")
        if trim_values.size == 2:
            if np.any(trim_values < 0) or np.any(trim_values > 1):
                raise ValueError("trim must lie in [0,1]")
            trim_values = np.sort(trim_values)
            a_lo, b_hi = trim_values[0], trim_values[1]
            jdim = len(u)
            klo = int(np.searchsorted(u, a_lo, side="right"))
            khi = int(np.searchsorted(u, b_hi, side="right"))
            wlo = (a_lo - u[klo - 1]) / (u[klo] - u[klo - 1])
            dlo = wlo * d[:, klo - 1] + (1.0 - wlo) * d[:, klo]
            s = _colon(klo + 1, khi) - 1
            if khi < jdim:
                whi = (b_hi - u[khi - 1]) / (u[khi] - u[khi - 1])
                dhi = whi * d[:, khi - 1] + (1.0 - whi) * d[:, khi]
                u = np.concatenate([[a_lo], u[s], [b_hi]])
                d = np.column_stack([dlo, d[:, s], dhi])
            else:
                u = np.concatenate([[a_lo], u[s]])
                d = np.column_stack([dlo, d[:, s]])
            a, b = a_lo, b_hi
            c = (a * a + 2.0 * b - b * b) / 2.0
            phibar = c
            a2 = (2.0 / 3.0) * (a**3 - b**3) - c * a * a - 2.0 * b * c + c * c + (1.0 + c) * b * b
        jn = len(u)
        out = 0.5 * (d[:, 1:jn] + d[:, : jn - 1]) @ np.diff(u) - phibar
        return {"ranks": np.asarray(out, dtype=float).reshape(-1), "A2": a2}

    if score == "normal":
        taus = taus_all
        jn = len(taus)
        dt = taus[1:] - taus[:-1]
        phi = np.concatenate([[0.0], _dnorm(_qnorm(taus[1 : jn - 1])), [0.0]])
        dphi = np.diff(phi)
        out = (dsol[:, 1:] - dsol[:, :-1]) @ (dphi / dt)
        return {"ranks": np.asarray(out, dtype=float).reshape(-1), "A2": 1.0}

    if score == "sign":
        out = 2.0 * _interp_dual(taus_all, dsol, 0.5) - 1.0
        return {"ranks": out, "A2": 1.0}

    if score == "tau":
        r = _interp_dual(taus_all, dsol, tau)
        return {"ranks": r - (1.0 - tau), "A2": tau * (1.0 - tau)}

    if score == "normalscale":
        taus = taus_all
        jn = len(taus)
        dt = taus[1:] - taus[:-1]
        qt = _qnorm(taus[1 : jn - 1])
        phi = np.concatenate([[0.0], -_dnorm(qt) * qt, [0.0]])
        dphi = np.diff(phi)
        out = (dsol[:, 1:] - dsol[:, :-1]) @ (dphi / dt)
        return {"ranks": np.asarray(out, dtype=float).reshape(-1), "A2": 2.0}

    if score == "halfnormalscale":
        taus = taus_all
        jn = len(taus)
        dt = taus[1:] - taus[:-1]
        inner = taus[1 : jn - 1]
        qt = _qnorm(inner)
        phi = np.concatenate([[0.0], (inner - _dnorm(qt) * qt) * (inner > 0.5), [1.0]])
        dphi = np.diff(phi)
        dphi = np.where(dphi > 0.5, 0.0, dphi)
        out = (dsol[:, 1:] - dsol[:, :-1]) @ (dphi / dt)
        return {"ranks": np.asarray(out, dtype=float).reshape(-1), "A2": 1.25}

    if score == "lehmann":
        taus = taus_all
        jn = len(taus)
        dt = taus[1:] - taus[:-1]
        inner = taus[1 : jn - 1]
        phi = np.concatenate([[0.0], -(inner - 1.0) * np.log(1.0 - inner), [0.0]])
        dphi = np.diff(phi)
        out = (dsol[:, 1:] - dsol[:, :-1]) @ (dphi / dt)
        return {"ranks": np.asarray(out, dtype=float).reshape(-1), "A2": 1.0}

    if score == "interquartile":
        r25 = _interp_dual(taus_all, dsol, 0.25)
        r75 = _interp_dual(taus_all, dsol, 0.75)
        return {"ranks": 0.5 + r75 - r25, "A2": 0.25}

    raise ValueError("invalid score function")


def predict_rq_process(object_, newdata):
    """Quantiles at each breakpoint for new rows, as R's ``predict.rq.process`` (type "Qhat").

    ``object_`` is a dict with ``sol`` as returned by ``rq_fit_br_process``.
    ``newdata`` is the model matrix of the new rows, intercept included, because the
    formula interface is not translated. Returns an m x J array, as R does.
    """
    sol = np.asarray(object_["sol"], dtype=float)
    design = _as_matrix(newdata)
    if design.shape[1] != sol.shape[0] - 3:
        raise ValueError("newdata must have one column per coefficient of the process")
    return design @ sol[3:, :]
