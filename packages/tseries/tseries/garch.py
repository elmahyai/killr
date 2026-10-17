"""GARCH models from tseries garch.R."""

from __future__ import annotations

import warnings

import numpy as np

from dsumsl import fit_garch, ophess_garch, pred_garch


def _vector(x, label="x"):
    values = np.asarray(x, dtype=float)
    if values.ndim == 2 and values.shape[1] == 1:
        values = values.reshape(-1)
    if values.ndim != 1:
        raise ValueError(f"{label} is not a vector or univariate time series")
    if np.isnan(values).any():
        raise ValueError(f"NAs in {label}")
    return values


def garch(x, order=(1, 1), series=None, control=None, **control_kwargs):
    if control is None:
        from tseries import garch_control

        control = garch_control(**control_kwargs)
    elif control_kwargs:
        raise TypeError("garch() got both control and keyword control arguments")

    if not isinstance(order, (list, tuple, np.ndarray)):
        raise ValueError("order is not a vector")
    order = np.asarray(order, dtype=int).reshape(-1)
    if order.size != 2:
        raise ValueError("order is not a vector")
    p, q = int(order[0]), int(order[1])

    grad = control["grad"]
    agrad = grad == "analytical"

    values = _vector(x)
    ists = hasattr(x, "start") and hasattr(x, "frequency")
    xfreq = float(getattr(x, "frequency", 1.0)) if ists else 1.0
    xtsp = None
    if ists:
        xtsp = (float(x.start), float(x.end), float(x.frequency))

    if series is None:
        series = "x"

    n = values.size
    ncoef = p + q + 1
    small = 0.05
    coef = control["start"]
    if coef is None:
        coef = np.concatenate(
            [
                np.array([np.var(values, ddof=1) * (1.0 - small * (ncoef - 1))]),
                np.full(ncoef - 1, small),
            ]
        )
    coef = np.asarray(coef, dtype=float).reshape(-1)
    if coef.ndim != 1:
        raise ValueError("coef is not a vector")
    if coef.size != ncoef:
        raise ValueError("incorrect length of coef")

    coef, nlikeli = fit_garch(
        values,
        coef,
        p,
        q,
        int(control["maxiter"]),
        float(control["abstol"]),
        float(control["reltol"]),
        float(control["xtol"]),
        float(control["falsetol"]),
        agrad,
        bool(control["trace"]),
    )

    e_var = pred_garch(values, coef, p, q, False)
    hess = ophess_garch(values, coef, p, q).reshape(ncoef, ncoef, order="F")

    qr_kwargs = dict(control.get("qr") or {})
    qr_result = np.linalg.qr(hess, **qr_kwargs)
    r_mat = qr_result[1] if isinstance(qr_result, tuple) else qr_result
    rank = int(np.sum(np.abs(np.diag(r_mat)) > 0))
    if rank != ncoef:
        vc = np.full((ncoef, ncoef), np.nan)
        warnings.warn("singular information", RuntimeWarning, stacklevel=2)
    else:
        vc = np.linalg.inv(hess)

    maxpq = max(p, q)
    sigt = np.sqrt(e_var)
    sigt[:maxpq] = np.nan
    fitted = np.column_stack([sigt, -sigt])

    with np.errstate(divide="ignore", invalid="ignore"):
        residuals = values / sigt

    nam_coef = ["a0"]
    if q > 0:
        nam_coef.extend(f"a{k}" for k in range(1, q + 1))
    if p > 0:
        nam_coef.extend(f"b{k}" for k in range(1, p + 1))

    order_named = {"p": p, "q": q}

    return {
        "order": order_named,
        "coef": dict(zip(nam_coef, coef)),
        "n.likeli": float(nlikeli),
        "n.used": int(n),
        "residuals": residuals,
        "fitted.values": fitted,
        "series": series,
        "frequency": xfreq,
        "vcov": vc,
        "_tsp": xtsp,
        "_ists": ists,
    }
