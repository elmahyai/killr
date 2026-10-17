"""Approximate variance-covariance of gls variance parameters (nlme ``glsApVar``)."""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass, replace
from typing import Any

import numpy as np

import nlmegls
from nlme import var_power
from nlme.conlin import ConLin
from nlme.corar1 import CorAR1
from nlme.corar1 import coef as corar1_coef
from nlme.cornatural import CorNatural
from nlme.cornatural import coef as cornatural_coef
from nlme.corsymm import CorSymm
from nlme.corsymm import coef as corsymm_coef
from nlme.fdhess import fdHess
from nlme.glsstruct import GlsStruct
from nlme.recalc import recalc
from nlme.var_power import VarPower

__all__ = [
    "ConLin",
    "GlsApVarMatrix",
    "glsApVar",
    "coef_vector",
    "coef_names",
    "parameter_map",
    "set_coef",
    "corsymm_to_natural",
    "fullGlsLogLik",
]


@dataclass(frozen=True, slots=True)
class GlsApVarMatrix:
    """``glsApVar`` result: the matrix with ``Pars`` and ``natural`` attributes."""

    values: np.ndarray
    pars: np.ndarray
    pars_names: tuple[str, ...]
    natural: bool


def _component_coef(component: Any) -> tuple[np.ndarray, tuple[str | None, ...]]:
    """``coef(component)`` with the default ``unconstrained = TRUE``."""
    if isinstance(component, CorAR1):
        cv = corar1_coef(component, unconstrained=True)
    elif isinstance(component, CorNatural):
        cv = cornatural_coef(component, unconstrained=True)
    elif isinstance(component, CorSymm):
        cv = corsymm_coef(component, unconstrained=True)
    elif isinstance(component, VarPower):
        cv = var_power.coef(component, unconstrained=True)
    else:
        raise NotImplementedError(
            f"coef is not translated for {type(component).__name__} in glsStruct"
        )
    values = np.asarray(cv.values, dtype=np.float64).reshape(-1)
    return values, tuple(cv.names)


def coef_vector(gls_st: GlsStruct) -> np.ndarray:
    """``coef(glsSt)``: the unconstrained coefficients of each component, in order."""
    parts = [_component_coef(comp)[0] for comp in gls_st.components.values()]
    if not parts:
        return np.zeros(0, dtype=np.float64)
    return np.concatenate(parts)


def coef_names(gls_st: GlsStruct) -> tuple[str, ...]:
    """Names of ``coef(glsSt)``. An unnamed coefficient takes its component name."""
    names: list[str] = []
    for name, comp in gls_st.components.items():
        _, comp_names = _component_coef(comp)
        for item in comp_names:
            names.append(item if item is not None else name)
    return tuple(names)


def parameter_map(gls_st: GlsStruct) -> np.ndarray:
    """``attr(glsSt, "pmap")``: rows are coefficients, columns are components."""
    if gls_st.pmap is not None:
        return np.asarray(gls_st.pmap, dtype=bool)
    lengths = [len(_component_coef(comp)[0]) for comp in gls_st.components.values()]
    total = sum(lengths)
    pmap = np.zeros((total, len(lengths)), dtype=bool)
    row = 0
    for col, length in enumerate(lengths):
        pmap[row : row + length, col] = True
        row += length
    return pmap


def _set_component_coef(component: Any, values: np.ndarray) -> Any:
    """``coef<-`` for one component: returns a new component, the input is not changed."""
    if isinstance(component, CorAR1):
        return replace(component, value=float(values[0]))
    if isinstance(component, CorNatural):
        return replace(component, value=np.asarray(values, dtype=np.float64))
    if isinstance(component, CorSymm):
        values = np.asarray(values, dtype=np.float64).reshape(-1)
        expected = int(component.max_cov or 0)
        expected = expected * (expected - 1) // 2
        if values.size != expected:
            raise ValueError("cannot change the length of the parameter of a corSymm object")
        return replace(component, value=values.copy())
    if isinstance(component, VarPower):
        return var_power.set_coef(component, values)
    raise NotImplementedError(f"coef<- is not translated for {type(component).__name__}")


def set_coef(gls_st: GlsStruct, values: Sequence[float] | np.ndarray) -> GlsStruct:
    """``coef(glsSt) <- values``: a new glsStruct with the mapped parameters replaced."""
    vec = np.asarray(values, dtype=np.float64).reshape(-1)
    pmap = parameter_map(gls_st)
    new_components = dict(gls_st.components)
    for col, name in enumerate(gls_st.components):
        mask = pmap[:, col]
        if not np.any(mask):
            continue
        new_components[name] = _set_component_coef(gls_st.components[name], vec[mask])
    return replace(gls_st, components=new_components)


def fullGlsLogLik(
    pars: np.ndarray,
    gls_st: GlsStruct,
    conLin: ConLin,
    dims: dict,
    n: int,
) -> float:
    """``glsApVar.fullGlsLogLik``: the log-likelihood at the variance parameters ``pars``."""
    point = np.asarray(pars, dtype=np.float64).reshape(-1)
    fixed_sigma = bool(gls_st.fixedSigma)
    if not fixed_sigma:
        lsigma = float(point[-1])
        fit_pars = point[:-1]
        sigma = 0.0
    else:
        fit_pars = point
        sigma = float(conLin.sigma)
    obj = set_coef(gls_st, fit_pars)
    con = recalc(obj, replace(conLin))
    xy = np.asarray(con.Xy, dtype=np.float64).reshape(-1, order="F")
    log_lik, _lrss = nlmegls.gls_loglik(
        xy.tolist(),
        int(dims["N"]),
        int(dims["p"]),
        int(dims["REML"]),
        0.0,
        0.0,
        float(sigma),
    )
    if not fixed_sigma:
        aux = 2.0 * (_lrss - lsigma)
        return float(con.logLik + log_lik + (n * aux - math.exp(aux)) / 2.0)
    return float(log_lik)


def corsymm_to_natural(component: CorSymm) -> CorNatural:
    """``class(cSt) <- c("corNatural", "corStruct")``: same slots, values kept as stored.

    R changes only the class. The caller sets the values with ``coef<-``, as R does.
    """
    return CorNatural(
        value=np.asarray(component.value, dtype=np.float64).copy(),
        formula=component.formula,
        fixed=component.fixed,
        max_cov=component.max_cov,
        covariate=component.covariate,
        dim=component.dim,
        groups=component.groups,
        factor=component.factor,
        log_det=component.log_det,
    )


def glsApVar(
    glsSt: GlsStruct,
    sigma: float,
    conLin: ConLin,
    relStep: float | None = None,
    minAbsPar: float | Sequence[float] = 0,
    natural: bool = True,
) -> GlsApVarMatrix | str | None:
    """Approximate variance-covariance of the non-coefficient parameters of a gls fit.

    Returns ``None`` when the structure has no parameters, as R does. Returns the
    string message when the Hessian is not negative definite.
    """
    gls_coef = coef_vector(glsSt)
    if gls_coef.size == 0:
        return None
    if natural and isinstance(glsSt.components.get("corStruct"), CorSymm):
        # R: cStNatPar <- coef(cSt, unconstrained = FALSE); class(cSt) <- corNatural;
        # coef(cSt) <- log((1 + cStNatPar) / (1 - cStNatPar)).
        cs = glsSt.components["corStruct"]
        nat = np.asarray(corsymm_coef(cs, unconstrained=False).values, dtype=np.float64)
        cn = _set_component_coef(corsymm_to_natural(cs), np.log((1.0 + nat) / (1.0 - nat)))
        glsSt = replace(glsSt, components={**glsSt.components, "corStruct": cn})
        gls_coef = coef_vector(glsSt)
    dims = conLin.dims
    n = int(dims["N"]) - int(dims["REML"]) * int(dims["p"])
    con = replace(conLin, logLik=0.0)
    names = coef_names(glsSt)
    if glsSt.fixedSigma:
        pars = gls_coef.copy()
        pars_names = names
    else:
        pars = np.concatenate([gls_coef, np.array([math.log(float(sigma))], dtype=np.float64)])
        pars_names = names + ("lSigma",)
    hess = fdHess(
        pars,
        fullGlsLogLik,
        glsSt,
        con,
        dims,
        n,
        relStep=relStep,
        minAbsPar=minAbsPar,
    )["Hessian"]
    hess = np.asarray(hess, dtype=np.float64)
    if not np.all(np.linalg.eigvalsh(hess) < 0):
        return "Non-positive definite approximate variance-covariance"
    values = np.linalg.solve(-hess, np.eye(hess.shape[0], dtype=np.float64))
    return GlsApVarMatrix(values, pars.copy(), pars_names, natural)
