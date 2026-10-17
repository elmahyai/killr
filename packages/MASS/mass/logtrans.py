"""Log-addition profile log-likelihood for linear models (MASS logtrans)."""

from __future__ import annotations

import math
from typing import Any

import numpy as np

from mass.boxcox import BoxcoxLm, _model_matrix, _qr_resid, _qchisq, _spline
from mass.errors import MassError


def _lm_logtrans(formula: str, data: dict[str, Any], **kwargs) -> BoxcoxLm:
    if kwargs:
        raise MassError(f"unused arguments: {', '.join(sorted(kwargs))}")
    x, y = _model_matrix(data, formula)
    return BoxcoxLm(y=y, x=x, formula=formula, data=data)


def _logtrans_default(
    object: BoxcoxLm,
    *,
    alpha: np.ndarray | None = None,
    plotit: bool = True,
    interp: bool | None = None,
    xlab: str = "alpha",
    ylab: str = "log Likelihood",
    **kwargs,
) -> dict[str, np.ndarray]:
    if kwargs:
        raise MassError(f"unused arguments: {', '.join(sorted(kwargs))}")
    y = np.asarray(object.y, dtype=float).reshape(-1)
    x = np.asarray(object.x, dtype=float)
    if y.shape[0] != x.shape[0]:
        raise MassError("y and model matrix have incompatible lengths")
    if alpha is None:
        alpha = np.arange(0.5, 6.0 + 1e-9, 0.25) - float(np.min(y))
    xl = np.asarray(alpha, dtype=float).reshape(-1)
    m = xl.size
    if np.any(y + np.min(xl) <= 0):
        raise MassError("Response variable must be positive after additions")
    if interp is None:
        interp = bool(plotit and m < 100)
    n = y.size
    loglik = np.empty(m, dtype=float)
    for i, al in enumerate(xl):
        yt = np.log(y + al)
        rs = _qr_resid(x, yt)
        loglik[i] = -n / 2.0 * math.log(float(np.sum(rs**2))) - float(np.sum(yt))
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
        ax.set_xlabel(xlab)
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
            ax.axvline(
                la,
                ymin=0,
                ymax=(lmax - plims[0]) / (plims[1] - plims[0]),
                linestyle=":",
                color="black",
            )
        ind = np.flatnonzero(loglik > lim)
        if ind.size:
            i0, i1 = int(ind[0]), int(ind[-1])
            if loglik[0] < lim and i0 > 0:
                xseg = xl[i0 - 1] + (lim - loglik[i0 - 1]) * (xl[i0] - xl[i0 - 1]) / (
                    loglik[i0] - loglik[i0 - 1]
                )
                ax.axvline(
                    xseg,
                    ymin=0,
                    ymax=(lim - plims[0]) / (plims[1] - plims[0]),
                    linestyle=":",
                    color="black",
                )
            if loglik[-1] < lim and i1 + 1 < m:
                i = i1 + 1
                xseg = xl[i - 1] + (lim - loglik[i - 1]) * (xl[i] - xl[i - 1]) / (
                    loglik[i] - loglik[i - 1]
                )
                ax.axvline(
                    xseg,
                    ymin=0,
                    ymax=(lim - plims[0]) / (plims[1] - plims[0]),
                    linestyle=":",
                    color="black",
                )
        plt.show()
    return {"x": xl, "y": loglik}


def logtrans(
    object,
    /,
    *,
    alpha: np.ndarray | None = None,
    plotit: bool = True,
    interp: bool | None = None,
    xlab: str = "alpha",
    ylab: str = "log Likelihood",
    data: dict[str, Any] | None = None,
    **kwargs,
):
    """Profile log-likelihood for the log(y + alpha) transformation."""
    if isinstance(object, str):
        if data is None:
            raise MassError("data is required when object is a formula")
        fit = _lm_logtrans(object, data, **kwargs)
        return _logtrans_default(
            fit,
            alpha=alpha,
            plotit=plotit,
            interp=interp,
            xlab=xlab,
            ylab=ylab,
        )
    if isinstance(object, BoxcoxLm):
        if object.y is None or object.x is None:
            if object.formula is None or object.data is None:
                raise MassError("object does not have both 'qr' and 'y' components")
            object = _lm_logtrans(object.formula, object.data, **kwargs)
        return _logtrans_default(
            object,
            alpha=alpha,
            plotit=plotit,
            interp=interp,
            xlab=xlab,
            ylab=ylab,
        )
    raise MassError("logtrans is implemented for formulas and BoxcoxLm fits")
