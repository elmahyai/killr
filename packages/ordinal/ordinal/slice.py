"""Likelihood slices for cumulative link models (ordinal slice.clm)."""

from __future__ import annotations

from typing import Any

import numpy as np

from ordinal._clm_nll import clm_nll
from ordinal._clm_rho import ClmLike, ClmRho


class SliceClm:
    """List-like slice result with one data frame per parameter."""

    def __init__(
        self,
        frames: dict[str, dict[str, np.ndarray]],
        original_fit: Any,
        mle: np.ndarray,
    ):
        self._frames = frames
        self.original_fit = original_fit
        self.mle = mle
        self._names = list(frames.keys())

    def __len__(self):
        return len(self._frames)

    def __getitem__(self, key):
        if isinstance(key, int):
            key = self._names[key]
        return self._frames[key]

    def keys(self):
        return self._frames.keys()

    def items(self):
        return self._frames.items()


def _coef(object, na_rm=True):
    if isinstance(object, ClmLike):
        values = object.coef
        names = object._coef_names
    elif hasattr(object, "coef"):
        values = object.coef
        if callable(values):
            values = values()
        values = np.asarray(values, dtype=float).reshape(-1)
        names = getattr(values, "names", None)
    else:
        raise TypeError("object has no coefficients")
    if na_rm:
        mask = np.isfinite(values)
        values = values[mask]
    else:
        values = values.copy()
    if names is not None and len(names) == len(values):
        par_names = [str(n) for n in names]
    elif isinstance(object, ClmLike):
        par_names = object._coef_names[: values.size]
    else:
        par_names = [str(i + 1) for i in range(values.size)]
    return values, par_names


def _get_clm_rho(object) -> ClmRho:
    if hasattr(object, "get_clm_rho"):
        return object.get_clm_rho()
    if hasattr(object, "_get_clm_rho"):
        return object._get_clm_rho()
    raise TypeError("object does not provide a clm rho environment")


def slice(
    object,
    parm=None,
    lambda_=3,
    grid=100,
    quad_approx=True,
    **kwargs,
):
    if isinstance(object, ClmLike) or hasattr(object, "logLik") and hasattr(object, "Hessian"):
        return slice_clm(
            object,
            parm=parm,
            lambda_=lambda_,
            grid=grid,
            quad_approx=quad_approx,
        )
    raise TypeError(f"no slice method for object of type {type(object).__name__}")


def slice_clm(
    object,
    parm=None,
    lambda_=3,
    grid=100,
    quad_approx=True,
):
    lambda_ = float(lambda_)
    if not (np.isfinite(lambda_) and lambda_ > 0):
        raise ValueError("invalid 'lambda' argument")
    grid = int(round(float(grid)))
    if grid < 1:
        raise ValueError("invalid 'grid' argument")

    par, par_names = _coef(object, na_rm=True)
    npar = par.size
    if parm is None:
        parm = np.arange(1, npar + 1, dtype=int)
    else:
        parm = np.asarray(parm)
        if parm.dtype.kind in {"U", "S", "O"}:
            idx = []
            for name in parm.tolist():
                try:
                    idx.append(par_names.index(str(name)) + 1)
                except ValueError as exc:
                    raise ValueError("invalid 'parm' argument") from exc
            parm = np.asarray(idx, dtype=int)
        else:
            parm = np.asarray(np.round(parm), dtype=int)
    if parm.size != np.unique(parm).size:
        raise ValueError("invalid 'parm' argument")
    if np.any(parm < 1) or np.any(parm > npar):
        raise ValueError("invalid 'parm' argument")
    if parm.size == 0:
        raise ValueError("invalid 'parm' argument")

    ml = float(object.logLik)
    parm_list = np.atleast_1d(parm).astype(int).tolist()
    parm_names = [par_names[i - 1] for i in parm_list]

    rho = _get_clm_rho(object)
    par_vec = par.copy()
    rho.par = par_vec.copy()
    nll0 = clm_nll(rho, par_vec)
    if not np.isclose(-nll0, ml, rtol=0, atol=1e-8):
        raise ValueError("rho log-likelihood does not match the fitted object")

    hess = np.asarray(object.Hessian, dtype=float)
    curv = np.sqrt(1.0 / np.diag(hess))
    par_range = par_vec[:, None] + curv[:, None] * np.array([-lambda_, lambda_])

    par_seq = [
        np.linspace(par_range[ind - 1, 0], par_range[ind - 1, 1], grid)
        for ind in parm_list
    ]

    loglik_slices = []
    for i, ind in enumerate(parm_list):
        rho.par = par_vec.copy()
        vals = []
        for par_val in par_seq[i]:
            trial = par_vec.copy()
            trial[ind - 1] = par_val
            rho.par = trial
            vals.append(-clm_nll(rho, trial) - ml)
        loglik_slices.append(np.asarray(vals, dtype=float))

    frames: dict[str, dict[str, np.ndarray]] = {}
    for i, name in enumerate(parm_names):
        frame = {name: par_seq[i], "logLik": loglik_slices[i]}
        frames[name] = frame

    if quad_approx:
        for i, ind in enumerate(parm_list):
            name = parm_names[i]
            mle_i = par_vec[ind - 1]
            curv_i = curv[ind - 1]
            frames[name]["quad"] = -((par_seq[i] - mle_i) ** 2 / curv_i**2 / 2.0)

    return SliceClm(
        frames=frames,
        original_fit=object,
        mle=par_vec[parm - 1],
    )


def slice_values(result: SliceClm, parm=None) -> np.ndarray:
    """Flatten parameter, logLik, and quad columns for checks."""
    if parm is None:
        keys = list(result.keys())
    else:
        keys = [list(result.keys())[int(i) - 1] for i in np.atleast_1d(parm)]
    parts = []
    for name in keys:
        frame = result[name]
        parts.append(np.asarray(frame[name], dtype=float))
        parts.append(np.asarray(frame["logLik"], dtype=float))
        if "quad" in frame:
            parts.append(np.asarray(frame["quad"], dtype=float))
    return np.concatenate(parts)
