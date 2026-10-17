"""Box-Cox profile log-likelihood for linear models (MASS boxcox)."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import numpy as np

from mass.errors import MassError

_TREES = {
    "Girth": [
        8.3,
        8.6,
        8.8,
        10.5,
        10.7,
        10.8,
        11,
        11,
        11.1,
        11.2,
        11.3,
        11.4,
        11.4,
        11.7,
        12,
        12.9,
        12.9,
        13.3,
        13.7,
        13.8,
        14,
        14.2,
        14.5,
        16,
        16.3,
        17.3,
        17.5,
        17.9,
        18,
        18,
        20.6,
    ],
    "Height": [
        70,
        65,
        63,
        72,
        81,
        83,
        66,
        75,
        80,
        75,
        79,
        76,
        76,
        69,
        75,
        74,
        85,
        86,
        71,
        64,
        78,
        80,
        74,
        72,
        77,
        81,
        82,
        80,
        80,
        80,
        87,
    ],
    "Volume": [
        10.3,
        10.3,
        10.2,
        16.4,
        18.8,
        19.7,
        15.6,
        18.2,
        22.6,
        19.9,
        24.2,
        21,
        21.4,
        21.3,
        19.1,
        22.2,
        33.8,
        27.4,
        25.7,
        24.9,
        34.5,
        31.7,
        36.3,
        38.3,
        42.6,
        55.4,
        55.7,
        58.3,
        51.5,
        51,
        77,
    ],
}


def trees() -> dict[str, list[float]]:
    """The ``trees`` data frame from R, for the boxcox example."""
    return {key: list(values) for key, values in _TREES.items()}


@dataclass
class BoxcoxLm:
    """Fitted lm object with the pieces ``boxcox.default`` needs."""

    y: np.ndarray
    x: np.ndarray
    formula: str | None = None
    data: dict[str, Any] | None = None


def _pnorm(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def _pchisq(q: float, df: float, *, lower_tail: bool = True) -> float:
    if math.isnan(q) or math.isnan(df) or df <= 0:
        return math.nan
    if df == 1.0:
        root = math.sqrt(max(q, 0.0))
        if lower_tail:
            return 2.0 * _pnorm(root) - 1.0
        return 2.0 * (1.0 - _pnorm(root))
    raise MassError("only df=1 is needed for boxcox")


def _qchisq(p: float, df: float) -> float:
    if df != 1.0:
        raise MassError("only df=1 is needed for boxcox")
    # Invert pchisq for df=1 via qnorm on sqrt(x).
    if p <= 0:
        return 0.0
    if p >= 1:
        return math.inf
    z = _pnorm_inv(p)
    return z * z


def _pnorm_inv(p: float) -> float:
    if p <= 0:
        return -math.inf
    if p >= 1:
        return math.inf
    # Rational approximation for the inverse normal (Acklam).
    a = [
        -3.969683028665376e01,
        2.209460984245205e02,
        -2.759285104469687e02,
        1.383577518672690e02,
        -3.066479806614716e01,
        2.506628277459239e00,
    ]
    b = [
        -5.447609879822406e01,
        1.615858368580409e02,
        -1.556989775060846e02,
        6.680131188771972e01,
        -1.328068155288572e01,
    ]
    c = [
        -7.784894002430293e-03,
        -3.223964580411021e-01,
        -2.400758277161838e00,
        -2.549732539343734e00,
        4.374664141464968e00,
        2.938163982698783e00,
    ]
    d = [
        7.784695709041462e-03,
        3.224671290700398e-01,
        2.445134137142996e00,
        3.754408661907416e00,
    ]
    plow = 0.02425
    if p < plow:
        q = math.sqrt(-2.0 * math.log(p))
        return (
            (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5])
            / ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0)
        )
    if p > 1.0 - plow:
        q = math.sqrt(-2.0 * math.log(1.0 - p))
        return -(
            (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5])
            / ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0)
        )
    q = p - 0.5
    r = q * q
    return (
        (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5])
        * q
        / (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1.0)
    )


def _eval_response(left: str, data: dict[str, Any]) -> np.ndarray:
    left = left.strip()
    if not left:
        raise MassError("formula needs a response")
    if "+" in left:
        parts = [piece.strip() for piece in left.split("+")]
        total = None
        for piece in parts:
            if piece in data:
                col = np.asarray(data[piece], dtype=float).reshape(-1)
            else:
                col = np.full(1, float(piece))
            total = col if total is None else total + col
        return np.asarray(total, dtype=float)
    if left not in data:
        raise MassError(f"object '{left}' not found")
    return np.asarray(data[left], dtype=float).reshape(-1)


def _eval_term(term: str, data: dict[str, Any], n: int) -> np.ndarray:
    term = term.strip()
    if term.startswith("log(") and term.endswith(")"):
        name = term[4:-1].strip()
        if name not in data:
            raise MassError(f"object '{name}' not found")
        col = np.asarray(data[name], dtype=float).reshape(-1)
        if col.shape[0] != n:
            raise MassError(f"column '{name}' has length {col.shape[0]}, not {n}")
        return np.log(col)
    if term not in data:
        raise MassError(f"object '{term}' not found")
    col = np.asarray(data[term], dtype=float).reshape(-1)
    if col.shape[0] != n:
        raise MassError(f"column '{term}' has length {col.shape[0]}, not {n}")
    return col


def _model_matrix(data: dict[str, Any], formula: str) -> tuple[np.ndarray, np.ndarray]:
    if "~" not in formula:
        raise MassError("formula needs a '~'")
    left, right = formula.split("~", 1)
    y = _eval_response(left, data)
    n = y.shape[0]
    intercept = True
    terms: list[str] = []
    for raw in right.split("+"):
        piece = raw.strip()
        if not piece:
            continue
        if piece in {"1", ""}:
            continue
        if piece in {"0", "-1"}:
            intercept = False
            continue
        if piece.startswith("-") and piece[1:].strip() == "1":
            intercept = False
            continue
        terms.append(piece)
    columns: list[np.ndarray] = []
    if intercept:
        columns.append(np.ones(n))
    for term in terms:
        columns.append(_eval_term(term, data, n))
    x = np.column_stack(columns)
    return x, y


def _lm_boxcox(formula: str, data: dict[str, Any], **kwargs) -> BoxcoxLm:
    if kwargs:
        raise MassError(f"unused arguments: {', '.join(sorted(kwargs))}")
    x, y = _model_matrix(data, formula)
    return BoxcoxLm(y=y, x=x, formula=formula, data=data)


def _qr_resid(x: np.ndarray, yt: np.ndarray) -> np.ndarray:
    q, r = np.linalg.qr(x, mode="reduced")
    coef = np.linalg.solve(r, q.T @ yt)
    return yt - x @ coef


def _fmm_spline(x: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    n = len(x)
    b = np.zeros(n)
    c = np.zeros(n)
    d = np.zeros(n)
    if n < 2:
        return b, c, d
    if n == 2:
        slope = (y[1] - y[0]) / (x[1] - x[0])
        b[:] = slope
        return b, c, d
    nm1 = n - 1
    d[0] = x[1] - x[0]
    c[1] = (y[1] - y[0]) / d[0]
    for i in range(1, nm1):
        d[i] = x[i + 1] - x[i]
        b[i] = 2.0 * (d[i - 1] + d[i])
        c[i + 1] = (y[i + 1] - y[i]) / d[i]
        c[i] = c[i + 1] - c[i]
    b[0] = -d[0]
    b[nm1] = -d[n - 2]
    c[0] = 0.0
    c[nm1] = 0.0
    if n != 3:
        c[0] = c[2] / (x[3] - x[1]) - c[1] / (x[2] - x[0])
        c[nm1] = c[n - 2] / (x[nm1] - x[n - 3]) - c[n - 3] / (x[n - 2] - x[n - 4])
        c[0] = c[0] * d[0] * d[0] / (x[3] - x[0])
        c[nm1] = -c[nm1] * d[n - 2] * d[n - 2] / (x[nm1] - x[n - 4])
    for i in range(1, n):
        t = d[i - 1] / b[i - 1]
        b[i] = b[i] - t * d[i - 1]
        c[i] = c[i] - t * c[i - 1]
    c[nm1] = c[nm1] / b[nm1]
    for i in range(n - 2, -1, -1):
        c[i] = (c[i] - d[i] * c[i + 1]) / b[i]
    b[nm1] = (y[nm1] - y[n - 2]) / d[n - 2] + d[n - 2] * (c[n - 2] + 2.0 * c[nm1])
    for i in range(nm1):
        b[i] = (y[i + 1] - y[i]) / d[i] - d[i] * (c[i + 1] + 2.0 * c[i])
        d[i] = (c[i + 1] - c[i]) / d[i]
        c[i] = 3.0 * c[i]
    c[nm1] = 3.0 * c[nm1]
    d[nm1] = d[n - 2]
    return b, c, d


def _spline_eval(
    x: np.ndarray,
    y: np.ndarray,
    b: np.ndarray,
    c: np.ndarray,
    d: np.ndarray,
    xout: np.ndarray,
) -> np.ndarray:
    n = len(x)
    out = np.empty(len(xout), dtype=np.float64)
    for t, value in enumerate(xout):
        v = float(value)
        if v <= x[0]:
            i = 0
        elif v >= x[-1]:
            i = n - 2
        else:
            lo = 0
            hi = n - 1
            while hi - lo > 1:
                mid = (lo + hi) // 2
                if v < x[mid]:
                    hi = mid
                else:
                    lo = mid
            i = lo
        dx = v - x[i]
        out[t] = y[i] + dx * (b[i] + dx * (c[i] + dx * d[i]))
    return out


def _spline(x: np.ndarray, y: np.ndarray, *, n: int = 100) -> tuple[np.ndarray, np.ndarray]:
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    xout = np.linspace(float(np.min(x)), float(np.max(x)), n)
    b, c, d = _fmm_spline(x, y)
    yout = _spline_eval(x, y, b, c, d, xout)
    return xout, yout


def _boxcox_default(
    object: BoxcoxLm,
    *,
    lambda_: np.ndarray | None = None,
    plotit: bool = True,
    interp: bool | None = None,
    eps: float = 1 / 50,
    xlab: str | None = None,
    ylab: str = "log-Likelihood",
    **kwargs,
) -> dict[str, np.ndarray]:
    if kwargs:
        raise MassError(f"unused arguments: {', '.join(sorted(kwargs))}")
    y = np.asarray(object.y, dtype=float).reshape(-1)
    x = np.asarray(object.x, dtype=float)
    if y.shape[0] != x.shape[0]:
        raise MassError("y and model matrix have incompatible lengths")
    if np.any(y <= 0):
        raise MassError("response variable must be positive")
    if lambda_ is None:
        lambda_ = np.arange(-2.0, 2.0 + 1e-9, 0.1)
    xl = np.asarray(lambda_, dtype=float).reshape(-1)
    m = xl.size
    if interp is None:
        interp = bool(plotit and m < 100)
    n = y.size
    y_scaled = y / np.exp(np.mean(np.log(y)))
    logy = np.log(y_scaled)
    loglik = np.empty(m, dtype=float)
    for i, la in enumerate(xl):
        if abs(la) > eps:
            yt = (y_scaled**la - 1.0) / la
        else:
            yt = logy * (1.0 + (la * logy) / 2.0 * (1.0 + (la * logy) / 3.0 * (1.0 + (la * logy) / 4.0)))
        resid = _qr_resid(x, yt)
        loglik[i] = -n / 2.0 * math.log(float(np.sum(resid**2)))
    if interp:
        xl, loglik = _spline(xl, loglik, n=100)
        m = xl.size
    if plotit:
        import matplotlib.pyplot as plt

        mx = int(np.flatnonzero(loglik == np.max(loglik))[0])
        lmax = float(loglik[mx])
        lim = lmax - _qchisq(19 / 20, 1) / 2.0
        fig, ax = plt.subplots()
        ax.plot(xl, loglik)
        ax.set_ylim(min(float(np.min(loglik)), lim), max(float(np.max(loglik)), lim))
        if xlab is not None:
            ax.set_xlabel(xlab)
        else:
            ax.set_xlabel("$\\lambda$")
        ax.set_ylabel(ylab)
        ax.axhline(lim, linestyle=":", color="black")
        plims = ax.get_ylim()
        xlims = ax.get_xlim()
        pin = ax.figure.get_size_inches()
        scal = (0.1 * (plims[1] - plims[0])) / pin[1]
        scx = (0.1 * (xlims[1] - xlims[0])) / pin[0]
        ax.text(xl[0] + scx, lim + scal, " 95%", clip_on=False)
        la = float(xl[mx])
        if mx > 0 and mx < m - 1:
            ax.axvline(la, ymin=0, ymax=(lmax - plims[0]) / (plims[1] - plims[0]), linestyle=":", color="black")
        ind = np.flatnonzero(loglik > lim)
        if ind.size:
            i0, i1 = int(ind[0]), int(ind[-1])
            if loglik[0] < lim and i0 > 0:
                xseg = xl[i0 - 1] + (lim - loglik[i0 - 1]) * (xl[i0] - xl[i0 - 1]) / (loglik[i0] - loglik[i0 - 1])
                ax.axvline(xseg, ymin=0, ymax=(lim - plims[0]) / (plims[1] - plims[0]), linestyle=":", color="black")
            if loglik[-1] < lim and i1 + 1 < m:
                i = i1 + 1
                xseg = xl[i - 1] + (lim - loglik[i - 1]) * (xl[i] - xl[i - 1]) / (loglik[i] - loglik[i - 1])
                ax.axvline(xseg, ymin=0, ymax=(lim - plims[0]) / (plims[1] - plims[0]), linestyle=":", color="black")
        plt.show()
    return {"x": xl, "y": loglik}


def boxcox(
    object,
    /,
    *,
    lambda_=None,
    plotit: bool = True,
    interp: bool | None = None,
    eps: float = 1 / 50,
    xlab: str | None = None,
    ylab: str = "log-Likelihood",
    data: dict[str, Any] | None = None,
    **kwargs,
):
    """Profile log-likelihood for the Box-Cox power transformation."""
    if isinstance(object, str):
        if data is None:
            raise MassError("data is required when object is a formula")
        fit = _lm_boxcox(object, data, **kwargs)
        return _boxcox_default(
            fit,
            lambda_=lambda_,
            plotit=plotit,
            interp=interp,
            eps=eps,
            xlab=xlab,
            ylab=ylab,
        )
    if isinstance(object, BoxcoxLm):
        if object.y is None or object.x is None:
            if object.formula is None or object.data is None:
                raise MassError("object does not have both 'qr' and 'y' components")
            updated = _lm_boxcox(object.formula, object.data, **kwargs)
            object = updated
        return _boxcox_default(
            object,
            lambda_=lambda_,
            plotit=plotit,
            interp=interp,
            eps=eps,
            xlab=xlab,
            ylab=ylab,
        )
    raise MassError("boxcox is implemented for formulas and BoxcoxLm fits")
