"""Likelihood ratio tests of nominal effects (ordinal nominal_test.clm)."""

from __future__ import annotations

from typing import Any

import numpy as np
from scipy.stats import chi2

from ordinal._clm_fitter import clm_fit_nr
from ordinal._clm_rho import ClmLike, ClmRho, rho_from_arrays
from ordinal.control import clm_control


class NominalTestAnova:
    """Anova table returned by nominal_test."""

    def __init__(self, frame: dict[str, np.ndarray], rownames: list[str], heading: list[str]):
        self._frame = frame
        self._rownames = rownames
        self._heading = heading

    @property
    def heading(self):
        return self._heading

    def __len__(self):
        return len(self._rownames)

    def __getitem__(self, key):
        if isinstance(key, str):
            return self._frame[key]
        if isinstance(key, int):
            key = self._rownames[key]
        if isinstance(key, str):
            return {name: self._frame[col][idx] for col, idx in self._row_index(key).items()}
        raise KeyError(key)

    def _row_index(self, name: str) -> dict[str, int]:
        try:
            idx = self._rownames.index(name)
        except ValueError as exc:
            raise KeyError(name) from exc
        return {col: idx for col in self._frame}

    def values(self) -> np.ndarray:
        cols = ["Df", "logLik", "AIC", "LRT", "Pr(>Chi)"]
        return np.concatenate([np.asarray(self._frame[c], dtype=float) for c in cols])


def _aic(loglik: float, edf: float) -> float:
    return -2.0 * loglik + 2.0 * edf


def _term_labels(object) -> list[str]:
    if hasattr(object, "term_labels"):
        return list(object.term_labels)
    terms = getattr(object, "terms", None)
    if terms is not None and hasattr(terms, "term_labels"):
        return list(terms.term_labels)
    raise TypeError("object has no term labels for nominal_test")


def _scale_term_labels(object) -> list[str]:
    if hasattr(object, "S_term_labels") and object.S_term_labels:
        return list(object.S_term_labels)
    s_terms = getattr(object, "S_terms", None)
    if s_terms is not None and hasattr(s_terms, "term_labels"):
        return list(s_terms.term_labels)
    return []


def _nom_term_labels(object) -> list[str]:
    if hasattr(object, "nom_term_labels") and object.nom_term_labels:
        return list(object.nom_term_labels)
    nom = getattr(object, "nom_terms", None)
    if nom is not None and hasattr(nom, "term_labels"):
        return list(nom.term_labels)
    return []


def _resolve_scope(object, scope) -> list[str]:
    termsnm = list(_term_labels(object))
    scale_labels = _scale_term_labels(object)
    if scale_labels:
        for label in scale_labels:
            if label not in termsnm:
                termsnm.append(label)
    if scope is not None:
        if not isinstance(scope, (list, tuple)):
            raise TypeError("scope must be a character vector of term names")
        scope = [str(s) for s in scope]
        missing = [s for s in scope if s not in termsnm]
        if missing:
            raise ValueError("scope is not a subset of term labels")
    else:
        scope = termsnm
    nom_labels = _nom_term_labels(object)
    if nom_labels:
        scope = [s for s in scope if s not in nom_labels]
    return scope


def _formula_location(object) -> str:
    if hasattr(object, "formula_location"):
        return str(object.formula_location)
    return ""


def _has_call_nominal(object) -> bool:
    call = getattr(object, "call", None)
    if call is None:
        return bool(getattr(object, "call_nominal", None))
    return getattr(call, "nominal", None) is not None or bool(getattr(object, "call_nominal", None))


def _has_call_scale(object) -> bool:
    call = getattr(object, "call", None)
    if call is None:
        return bool(getattr(object, "call_scale", None))
    return getattr(call, "scale", None) is not None or bool(getattr(object, "call_scale", None))


def _nom_formula_deparse(object) -> str:
    if getattr(object, "nom_formula", None):
        return str(object.nom_formula)
    return ""


def _scale_formula_deparse(object) -> str:
    if getattr(object, "scale_formula", None):
        return str(object.scale_formula)
    return ""


def _refit_nominal(object, term: str, convergence: str = "silent") -> dict[str, Any] | None:
    refits = getattr(object, "_refit_nominal_rhos", None)
    if refits is None or term not in refits:
        return None
    rho, start = refits[term]
    rho = _copy_rho(rho)
    rho.par = np.asarray(start, dtype=float).reshape(-1).copy()
    ctrl = clm_control(convergence=convergence)
    try:
        return clm_fit_nr(rho, control=ctrl)
    except ValueError:
        return None


def _copy_rho(rho: ClmRho) -> ClmRho:
    s = None if rho.s is None else np.asarray(rho.s, dtype=float).copy()
    return rho_from_arrays(
        b1=rho.b1,
        b2=rho.b2,
        o1=rho.o1,
        o2=rho.o2,
        wts=rho.wts,
        n_psi=rho.n_psi,
        k=rho.k,
        soff=rho.soff,
        s=s,
        link=rho.link,
        lambda_=rho.lambda_,
        nlambda=rho.nlambda,
        par=rho.par.copy(),
    )


def nominal_test(object, scope=None, trace=False, **kwargs):
    if isinstance(object, ClmLike) or (
        hasattr(object, "logLik") and hasattr(object, "edf") and _term_labels(object)
    ):
        return nominal_test_clm(object, scope=scope, trace=trace, **kwargs)
    raise TypeError(f"no nominal_test method for object of type {type(object).__name__}")


def nominal_test_clm(object, scope=None, trace=False, **_kwargs):
    del _kwargs
    scope = _resolve_scope(object, scope)
    if not scope:
        print("\nno additional terms to add to nominal\n")
    ns = len(scope)
    rownames = ["<none>"] + scope
    ans = np.full((ns + 1, 3), np.nan, dtype=float)
    edf0 = float(getattr(object, "edf", np.nan))
    if np.isnan(edf0) and hasattr(object, "coef"):
        edf0 = float(np.asarray(object.coef, dtype=float).size)
    loglik0 = float(object.logLik)
    ans[0, :] = [edf0, loglik0, _aic(loglik0, edf0)]
    n0 = int(getattr(object, "nobs", getattr(object, "n", np.nan)))
    for i, term in enumerate(scope):
        if trace:
            print(f"trying + {term} ")
        nfit = _refit_nominal(object, term, convergence="silent")
        if nfit is not None and int(nfit["convergence"]["code"]) >= 0:
            ans[i + 1, :] = [nfit["edf"], nfit["logLik"], _aic(nfit["logLik"], nfit["edf"])]
            nnew = int(nfit["nobs"])
            if np.isfinite(n0) and np.isfinite(nnew) and nnew != n0:
                raise ValueError("number of rows in use has changed: remove missing values?")
    dfs = ans[:, 0] - ans[0, 0]
    dfs[0] = np.nan
    lr = 2.0 * (ans[:, 1] - ans[0, 1])
    lr[0] = np.nan
    pvals = lr.copy()
    mask = np.isfinite(lr) & np.isfinite(dfs)
    pvals[mask] = chi2.sf(lr[mask], dfs[mask])
    pvals[~mask] = np.nan
    frame = {
        "Df": dfs,
        "logLik": ans[:, 1],
        "AIC": ans[:, 2],
        "LRT": lr,
        "Pr(>Chi)": pvals,
    }
    head = ["Tests of nominal effects", f"\nformula: {_formula_location(object)}"]
    if _has_call_scale(object):
        head.append(f"scale:   {_scale_formula_deparse(object)}")
    if _has_call_nominal(object):
        head.append(f"nominal: {_nom_formula_deparse(object)}")
    return NominalTestAnova(frame=frame, rownames=rownames, heading=head)


def nominal_test_values(result: NominalTestAnova) -> np.ndarray:
    """Flatten anova columns in R column order."""
    return result.values()
