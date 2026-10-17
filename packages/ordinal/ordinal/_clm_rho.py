"""Model environment for slice likelihood evaluation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from ordinal._clm_nll import clm_nll


@dataclass
class ClmRho:
    b1: np.ndarray
    b2: np.ndarray
    o1: np.ndarray
    o2: np.ndarray
    wts: np.ndarray
    n_psi: int
    k: int
    soff: np.ndarray
    sigma: np.ndarray
    s: np.ndarray | None
    link: str
    lambda_: float
    nlambda: bool
    par: np.ndarray

    def nll(self, par=None):
        return clm_nll(self, par)


def rho_from_arrays(
    *,
    b1,
    b2,
    o1,
    o2,
    wts,
    n_psi,
    k,
    soff,
    s=None,
    link="logit",
    lambda_=1.0,
    nlambda=False,
    par=None,
):
    b1 = np.asarray(b1, dtype=float)
    b2 = np.asarray(b2, dtype=float)
    o1 = np.asarray(o1, dtype=float).reshape(-1)
    o2 = np.asarray(o2, dtype=float).reshape(-1)
    wts = np.asarray(wts, dtype=float).reshape(-1)
    soff = np.asarray(soff, dtype=float).reshape(-1)
    sigma = soff.copy()
    if s is None or (hasattr(s, "size") and np.size(s) == 0):
        s_arr = None
    else:
        s_arr = np.asarray(s, dtype=float)
        if s_arr.size == 0:
            s_arr = None
    if par is None:
        par = np.zeros(b1.shape[1] + (0 if s_arr is None else s_arr.shape[1]), dtype=float)
    return ClmRho(
        b1=b1,
        b2=b2,
        o1=o1,
        o2=o2,
        wts=wts,
        n_psi=int(n_psi),
        k=int(k),
        soff=soff,
        sigma=sigma,
        s=s_arr,
        link=str(link),
        lambda_=float(lambda_),
        nlambda=bool(nlambda),
        par=np.asarray(par, dtype=float).reshape(-1),
    )


class ClmLike:
    """Minimal clm fit carrying coefficients and a rho environment for slice."""

    def __init__(
        self,
        coef: np.ndarray,
        loglik: float,
        hessian: np.ndarray,
        coef_names: list[str],
        rho: ClmRho,
        gradient: np.ndarray | None = None,
        info: dict | None = None,
        nobs: int | None = None,
        *,
        edf: float | None = None,
        term_labels: list[str] | None = None,
        formula_location: str | None = None,
        refit_nominal_rhos: dict[str, tuple[ClmRho, np.ndarray]] | None = None,
    ):
        self.coef = np.asarray(coef, dtype=float).reshape(-1)
        self.logLik = float(loglik)
        self.Hessian = np.asarray(hessian, dtype=float)
        self._coef_names = list(coef_names)
        self._rho = rho
        self.edf = float(edf if edf is not None else self.coef.size)
        if gradient is not None:
            self.gradient = np.asarray(gradient, dtype=float).reshape(-1)
        if info is not None:
            self.info = dict(info)
        if nobs is not None:
            self.nobs = int(nobs)
        if term_labels is not None:
            self.term_labels = list(term_labels)
        if formula_location is not None:
            self.formula_location = formula_location
        if refit_nominal_rhos is not None:
            self._refit_nominal_rhos = refit_nominal_rhos

    def get_clm_rho(self) -> ClmRho:
        return self._rho


def _rho_arrays_from_npz(data, prefix: str) -> tuple[ClmRho, np.ndarray]:
    s_key = f"{prefix}_S"
    s_raw = data[s_key] if s_key in data else np.empty(0)
    s_arr = None if s_raw.size == 0 else np.asarray(s_raw, dtype=float)
    rho = rho_from_arrays(
        b1=data[f"{prefix}_B1"],
        b2=data[f"{prefix}_B2"],
        o1=data[f"{prefix}_o1"],
        o2=data[f"{prefix}_o2"],
        wts=data[f"{prefix}_wts"],
        n_psi=int(np.asarray(data[f"{prefix}_n_psi"]).item()),
        k=int(np.asarray(data[f"{prefix}_k"]).item()),
        soff=data[f"{prefix}_Soff"],
        s=s_arr,
        link=str(data["link"].item()),
        lambda_=float(np.asarray(data["lambda"]).reshape(-1)[0]) if data["lambda"].size else 1.0,
        nlambda=bool(int(np.asarray(data["nlambda"]).item())),
        par=data[f"{prefix}_par"],
    )
    start = np.asarray(data[f"{prefix}_par"], dtype=float).reshape(-1)
    return rho, start


def clm_like_from_npz(path: str) -> ClmLike:
    data = np.load(path, allow_pickle=True)
    par = np.asarray(data["par"], dtype=float)
    rho = rho_from_arrays(
        b1=data["B1"],
        b2=data["B2"],
        o1=data["o1"],
        o2=data["o2"],
        wts=data["wts"],
        n_psi=int(np.asarray(data["n.psi"]).item()),
        k=int(np.asarray(data["k"]).item()),
        soff=data["Soff"],
        s=None if data["S"].size == 0 or data["S"].dtype == object else data["S"],
        link=str(data["link"].item()),
        lambda_=float(np.asarray(data["lambda"]).reshape(-1)[0]) if data["lambda"].size else 1.0,
        nlambda=bool(int(np.asarray(data["nlambda"]).item())),
        par=par,
    )
    names = [str(x) for x in data["par_names"].tolist()]
    gradient = None
    if "gradient" in data:
        gradient = np.asarray(data["gradient"], dtype=float)
    info = None
    if "info_nobs" in data:
        info = {
            "nobs": int(np.asarray(data["info_nobs"]).item()),
            "logLik": str(np.asarray(data["info_logLik"]).item()),
            "niter": str(np.asarray(data["info_niter"]).item()),
            "max.grad": str(np.asarray(data["info_max_grad"]).item()),
            "cond.H": str(np.asarray(data["info_cond_H"]).item()),
        }
    nobs = int(np.asarray(data["info_nobs"]).item()) if "info_nobs" in data else None
    term_labels = None
    formula_location = None
    refit_nominal_rhos = None
    if "term_labels" in data:
        term_labels = [str(x) for x in data["term_labels"].tolist()]
    if "formula_location" in data:
        formula_location = str(np.asarray(data["formula_location"]).item())
    if "refit_nominal_terms" in data:
        refit_nominal_rhos = {}
        for term in data["refit_nominal_terms"].tolist():
            term = str(term)
            prefix = f"refit_{term}"
            refit_nominal_rhos[term] = _rho_arrays_from_npz(data, prefix)
    edf = float(np.asarray(data["edf"]).item()) if "edf" in data else None
    return ClmLike(
        coef=par,
        loglik=float(np.asarray(data["logLik"]).item()),
        hessian=np.asarray(data["Hessian"], dtype=float),
        coef_names=names,
        rho=rho,
        gradient=gradient,
        info=info,
        nobs=nobs,
        edf=edf,
        term_labels=term_labels,
        formula_location=formula_location,
        refit_nominal_rhos=refit_nominal_rhos,
    )
