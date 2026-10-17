"""Confidence intervals for a gls fit (nlme ``intervals.gls``).

Translated: the coefficient intervals (``which = "coef"``), the residual
standard error when the fit has no ``apVar`` (``which = "var-cov"`` or ``"all"``
with ``apVar = NULL``, as for an unstructured gls fit), and the variance-covariance
intervals when ``apVar`` is a matrix. The last case uses the translated
``glsApVar`` result: normal-quantile intervals on the unconstrained parameters,
mapped back to the natural scale of each structure through ``coef<-`` and
``coef(, unconstrained = FALSE)``.

``apVar`` with a ``corSymm`` correlation and ``natural = TRUE`` converts the
structure to ``corNatural`` as R does, through ``corsymm_to_natural``.

Not translated: ``apVar`` with a ``corSymm`` correlation and ``natural = FALSE``
(``coef<-`` for corSymm is not translated), and a structure other than corAR1,
corNatural, corSymm (natural), or varPower.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, replace

import numpy as np
from scipy import stats

from nlme import var_power
from nlme.corar1 import CorAR1
from nlme.corar1 import coef as corar1_coef
from nlme.cornatural import CorNatural
from nlme.cornatural import coef as cornatural_coef
from nlme.corsymm import CorSymm
from nlme.corsymm import coef as corsymm_coef
from nlme.gls import GlsObject
from nlme.glsapvar import corsymm_to_natural, parameter_map, set_coef
from nlme.glsstruct import GlsStruct
from nlme.var_power import VarPower

__all__ = ["GlsIntervals", "intervals"]


@dataclass(frozen=True, slots=True)
class GlsIntervals:
    """``intervals.gls`` result. Columns are ``lower``, ``est.``, ``upper``.

    ``structures`` holds one ``(k, 3)`` array per structure component in
    ``glsSt`` order (R: ``val[[namG]]``), with its row names in ``structure_names``.
    """

    level: float
    coef: np.ndarray | None
    coef_names: tuple[str, ...]
    sigma: np.ndarray | None
    structures: dict[str, np.ndarray] = field(default_factory=dict)
    structure_names: dict[str, tuple[str, ...]] = field(default_factory=dict)


def intervals(
    object: GlsObject,
    level: float = 0.95,
    which: str = "all",
) -> GlsIntervals:
    if which not in ("all", "coef", "var-cov"):
        raise ValueError('which must be one of "all", "coef", "var-cov"')
    dims = object.dims
    n = int(dims["N"])
    p = int(dims["p"])
    reml = int(dims["REML"])
    coef_out = None
    names: tuple[str, ...] = tuple(object.coef_names)
    if which != "var-cov":
        len_ = -stats.t.ppf((1.0 - level) / 2.0, n - p) * np.sqrt(np.diag(object.varBeta))
        est = np.asarray(object.coefficients, dtype=np.float64)
        coef_out = np.column_stack([est - len_, est, est + len_])
    sigma_out = None
    structures: dict[str, np.ndarray] = {}
    structure_names: dict[str, tuple[str, ...]] = {}
    if which != "coef":
        if object.apVar is None:
            fix_sig = bool(object.fixedSigma)
            if not fix_sig:
                nr = n - reml * p
                est_s = object.sigma * math.sqrt(nr)
                sigma_out = np.array(
                    [
                        est_s / math.sqrt(stats.chi2.ppf((1.0 + level) / 2.0, nr)),
                        object.sigma,
                        est_s / math.sqrt(stats.chi2.ppf((1.0 - level) / 2.0, nr)),
                    ],
                    dtype=np.float64,
                )
            else:
                sigma_out = np.array([object.sigma, object.sigma, object.sigma], dtype=np.float64)
        else:
            if isinstance(object.apVar, str):
                raise ValueError(
                    f"cannot get confidence intervals on var-cov components: {object.apVar}"
                )
            structures, structure_names, sigma_out = _apvar_intervals(object, level)
    return GlsIntervals(
        level=float(level),
        coef=coef_out,
        coef_names=names,
        sigma=sigma_out,
        structures=structures,
        structure_names=structure_names,
    )


def _natural_coef(component: object) -> tuple[np.ndarray, tuple[str | None, ...]]:
    """``coef(component, unconstrained = FALSE)`` for one structure component."""
    if isinstance(component, CorAR1):
        cv = corar1_coef(component, unconstrained=False)
    elif isinstance(component, CorNatural):
        cv = cornatural_coef(component, unconstrained=False)
    elif isinstance(component, CorSymm):
        cv = corsymm_coef(component, unconstrained=False)
    elif isinstance(component, VarPower):
        # R coef.varPower ignores unconstrained: the stored values are the powers.
        cv = var_power.coef(component, unconstrained=False)
    else:
        raise NotImplementedError(
            f"intervals on {type(component).__name__} with apVar is not translated"
        )
    return np.asarray(cv.values, dtype=np.float64).reshape(-1), tuple(cv.names)


def _apvar_intervals(
    object: GlsObject, level: float
) -> tuple[dict[str, np.ndarray], dict[str, tuple[str, ...]], np.ndarray]:
    """The variance-covariance part of ``intervals.gls`` when ``apVar`` is a matrix."""
    aV = object.apVar
    len_ = -stats.norm.ppf((1.0 - level) / 2.0) * np.sqrt(np.diag(aV.values))
    est = np.asarray(aV.pars, dtype=np.float64).reshape(-1)
    nP = est.size
    gls_st: GlsStruct = object.modelStruct
    pmap = parameter_map(gls_st)
    # R drops components whose coefficients are all fixed (no pmap column with any TRUE).
    keep = np.any(pmap, axis=0)
    if not np.all(keep):
        kept = {
            name: comp
            for (name, comp), flag in zip(gls_st.components.items(), keep, strict=True)
            if flag
        }
        gls_st = replace(gls_st, components=kept, pmap=pmap[:, keep])
        pmap = pmap[:, keep]
    # R: if (corSymm and natural) class(cSt) <- c("corNatural", "corStruct"). The values
    # are set by coef<- in the loop below.
    if isinstance(gls_st.components.get("corStruct"), CorSymm) and aV.natural:
        cs = corsymm_to_natural(gls_st.components["corStruct"])
        gls_st = replace(gls_st, components={**gls_st.components, "corStruct": cs})
    comp_names = list(gls_st.components)

    aux = np.column_stack([est - len_, est, est + len_])
    if not bool(object.fixedSigma):
        # last parameter is log(sigma)
        sigma_out = np.exp(aux[nP - 1])
        aux = aux[: nP - 1]
    else:
        sigma_out = np.array([object.sigma, object.sigma, object.sigma], dtype=np.float64)

    # R: for each of lower, est., upper set coef(glsSt) to the unconstrained values, then
    # read back coef(glsSt, unconstrained = FALSE).
    row_names: tuple[str, ...] = ()
    for i in range(3):
        st_i = set_coef(gls_st, aux[:, i])
        values = []
        names: list[str] = []
        for comp_name in comp_names:
            cv_values, cv_names = _natural_coef(st_i.components[comp_name])
            values.append(cv_values)
            names.extend("" if n is None else str(n) for n in cv_names)
        natural = np.concatenate(values) if values else np.zeros(0, dtype=np.float64)
        if natural.size != aux.shape[0]:
            raise ValueError("glsSt parameter count does not match the apVar parameters")
        aux[:, i] = natural
        row_names = tuple(names)

    structures: dict[str, np.ndarray] = {}
    structure_names: dict[str, tuple[str, ...]] = {}
    for col, name in enumerate(comp_names):
        mask = pmap[:, col]
        structures[name] = aux[mask]
        structure_names[name] = tuple(n for n, flag in zip(row_names, mask, strict=True) if flag)
    return structures, structure_names, sigma_out
