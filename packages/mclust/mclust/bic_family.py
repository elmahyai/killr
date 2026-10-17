"""BIC computation, model selection, and display methods for mclust."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import numpy as np

from ._bic_objects import with_initial_partition
from ._qclass import qclass
from .em_control import em_control
from .hc import hc
from .bic import bic
from .estep import estep
from .hclass import hclass
from .me import me
from .mclust_options import mclust_options
from .model_metadata import nMclustParams
from .mstep_loglik_icl import mstep
from .mvn import mvn
from .utility_functions import hypvol
from .summary_mclust_bic import (
    summaryMclustBIC as _summaryMclustBIC,
    summaryMclustBICn as _summaryMclustBICn,
)
from .unmap_util import unmap

__all__ = [
    "mclustModel",
    "mclustBIC",
    "print_mclustBIC",
    "summary_mclustBIC",
]

# R: the diagonal models kept when n <= d, and the models dropped with a prior.
_DIAGONAL_MODELS = ("EII", "VII", "EEI", "VEI", "EVI", "VVI")
_PRIOR_EXCLUDED = ("EVE", "VEE", "VVE", "EVV")


def _summary(object_: Any, data: Any, G: Any, model_names: Any,
             noise: bool = False) -> dict[str, Any]:
    result = (_summaryMclustBICn if noise else _summaryMclustBIC)(
        object_, data=data, G=G, modelNames=model_names
    )
    values = np.atleast_2d(np.asarray(_get(object_, "values", object_), dtype=float))
    rows = _names(object_, "G", values.shape[0], [str(i) for i in range(1, values.shape[0] + 1)])
    cols = _names(object_, "modelNames", values.shape[1], [str(i) for i in range(values.shape[1])])
    if G is not None:
        keep = {str(v) for v in np.atleast_1d(G)}
        indices = [i for i, row in enumerate(rows) if row in keep]
        values, rows = values[indices, :], [rows[i] for i in indices]
    if model_names is not None:
        keep = {str(v) for v in np.atleast_1d(model_names)}
        indices = [i for i, col in enumerate(cols) if col in keep]
        values, cols = values[:, indices], [cols[i] for i in indices]
    flat = np.where(np.isfinite(values), values, -np.inf).ravel(order="F")
    best = []
    for index in np.argsort(-flat, kind="stable")[:3]:
        i, j = np.unravel_index(index, values.shape, order="F")
        if np.isfinite(values[i, j]):
            best.append({"modelName": cols[j], "G": int(rows[i]),
                         "criterion": float(values[i, j])})
    result["bestBICvalues"] = best
    if best and result.get("G") == 1:
        # R: a one-component summary keeps the top BIC values as its bic.
        result["bic"] = np.asarray([item["criterion"] for item in best], dtype=float)
    return result


def summaryMclustBIC(object: Any, data: Any, G: Any = None,
                     modelNames: Any = None, **kwargs: Any) -> dict[str, Any]:
    return _summary(object, data, G, modelNames, False)


def summaryMclustBICn(object: Any, data: Any, G: Any = None,
                      modelNames: Any = None, **kwargs: Any) -> dict[str, Any]:
    return _summary(object, data, G, modelNames, True)


def _get(x: Any, name: str, default: Any = None) -> Any:
    if isinstance(x, Mapping):
        return x.get(name, default)
    return getattr(x, name, default)


def _as_data(data: Any) -> tuple[np.ndarray, int, int]:
    x = np.asarray(data, dtype=float)
    if x.ndim == 1:
        return x, int(x.size), 1
    if x.ndim != 2:
        raise ValueError("data must be a vector or a matrix")
    return x, int(x.shape[0]), int(x.shape[1])


def _names(object_: Any, name: str, size: int, defaults: list[str]) -> list[str]:
    values = _get(object_, name)
    if values is None:
        return defaults[:size]
    return [str(value) for value in np.atleast_1d(values)]


def _bic(loglik: float, n: int, d: int, g: int, model: str | None = None,
         noise: bool = False, equal_pro: bool = False) -> float:
    # R: bic(modelName, loglik, n, d, G, ...) penalises with the requested model.
    name = model if model is not None else ("X" if d == 1 else "XII")
    return float(2.0 * loglik - nMclustParams(
        name, d, g, noise=noise, equalPro=equal_pro
    ) * np.log(n))


_EMPTY = -float(np.finfo(float).max)  # R: EMPTY <- -.Machine$double.xmax
_SMALL = float(np.sqrt(np.finfo(float).epsneg))  # R: sqrt(.Machine$double.neg.eps)


def _equal_pro(control: Any) -> bool:
    if isinstance(control, Mapping):
        return bool(control.get("equalPro", False))
    return bool(getattr(control, "equalPro", False))


def _one_based(values: Any) -> np.ndarray:
    """R ``which()`` for logical input; numeric input is already 1-based."""
    a = np.asarray(values)
    if a.dtype == bool:
        return np.flatnonzero(a) + 1
    return np.asarray(a, dtype=int).reshape(-1)


def _sample_subset(n: int, size: int) -> np.ndarray:
    """R: ``sample(seq.int(n), size = size, replace = FALSE)``, 1-based."""
    try:
        from boot.rng import sample_int
    except ImportError:
        import sys
        from pathlib import Path

        sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "boot"))
        from boot.rng import sample_int
    return np.asarray(sample_int(n, size, replace=False), dtype=int)


def _hc_start(values: np.ndarray, n_all: int, d: int) -> Any:
    """R: ``hc(data, modelName = hcModelName or EII, use = hcUse)`` with its default partition.

    R's ``hc`` default partition is ``1:n`` (the ``dupPartition`` default is not reached,
    because ``hc`` forwards only the arguments that were supplied). ``n_all`` is the
    full number of rows, as R's ``n > d`` test uses it.
    """
    model = str(mclust_options("hcModelName")) if n_all > d else "EII"
    pairs = hc(values, modelName=model, use=mclust_options("hcUse"))
    return with_initial_partition(pairs, np.arange(1, values.shape[0] + 1))


def _missing_group_fix(z: np.ndarray) -> np.ndarray:
    """R: ``z[z < small] <- small`` then each row divided by its sum."""
    z = np.where(z < _SMALL, _SMALL, z)
    return z / z.sum(axis=1, keepdims=True)


def mclustBIC(
    data: Any,
    G: Any = None,
    modelNames: Any = None,
    prior: Any = None,
    control: Any = None,
    initialization: Any = None,
    Vinv: Any = None,
    warn: Any = None,
    x: Any = None,
    verbose: bool = False,
    **_: Any,
) -> dict[str, Any]:
    """BIC matrix for mixtures with G and modelNames, as R's ``mclustBIC``.

    The three starts of R's ``mclustBIC`` are translated: the hierarchical start on
    all rows, the hierarchical start on an initial ``subset`` (drawn with R's RNG
    when ``n > mclust.options("subset")``), and the noise model, where ``noise``
    rows are a fixed extra component with density ``Vinv``.
    """
    if x is not None:
        values = np.asarray(_get(x, "values", x), dtype=float)
        rows = _names(x, "G", values.shape[0], [str(i) for i in range(1, values.shape[0] + 1)])
        cols = _names(x, "modelNames", values.shape[1], list(mclust_options("emModelNames")))
        wanted_g = rows if G is None else [str(v) for v in np.atleast_1d(G)]
        wanted_m = cols if modelNames is None else [str(v) for v in np.atleast_1d(modelNames)]
        ri = [rows.index(v) for v in wanted_g if v in rows]
        ci = [cols.index(v) for v in wanted_m if v in cols]
        out = values[np.ix_(ri, ci)]
        return {
            "values": out, "G": [int(v) if v.lstrip("-").isdigit() else v for v in wanted_g if v in rows],
            "modelNames": [v for v in wanted_m if v in cols],
            "prior": _get(x, "prior", prior), "control": _get(x, "control", control),
            "initialization": _get(x, "initialization", initialization),
        }

    from .mclust_object import checkDataMatrix

    values = np.asarray(checkDataMatrix(data), dtype=float)
    n, d = int(values.shape[0]), int(values.shape[1])
    if d < 1:
        raise ValueError("no available data for fitting")
    if control is None:
        control = em_control()
    if warn is None:
        warn = mclust_options("warn")
    equal_pro = _equal_pro(control)

    init = dict(initialization) if isinstance(initialization, Mapping) else {}
    hc_pairs = init.get("hcPairs")
    subset = init.get("subset")
    noise = init.get("noise")
    noise = None if noise is None else _one_based(noise)
    subset = None if subset is None else _one_based(subset)
    nnoise = 0 if noise is None else int(noise.size)

    # R: default modelNames, then the prior filter, then the one-dimensional collapse.
    if modelNames is not None:
        models = [str(v) for v in np.atleast_1d(modelNames)]
    elif d == 1:
        models = ["E", "V"]
    else:
        models = list(mclust_options("emModelNames"))
        if n <= d:
            models = [m for m in models if m in _DIAGONAL_MODELS]
    if prior is not None:
        models = [m for m in models if m not in _PRIOR_EXCLUDED]
    if d == 1 and any(len(m) > 1 for m in models):
        has_e = any(m.startswith("E") for m in models)
        has_v = any(m.startswith("V") for m in models)
        models = [name for name, flag in (("E", has_e), ("V", has_v)) if flag]
    if not models:
        raise ValueError("no model names supplied")

    # R: G defaults to 1:9, or 0:9 with noise; values above the rows available are dropped.
    if G is None:
        groups = list(range(0, 10)) if noise is not None else list(range(1, 10))
    else:
        groups = sorted({int(v) for v in np.atleast_1d(G)})
    limit = n - nnoise if noise is not None else n
    groups = [g for g in groups if g <= limit]
    if not groups:
        raise ValueError("no available number of components")

    # R: an initial subset is drawn when none is given, there is no hcPairs, and n is large.
    if subset is None and hc_pairs is None and n > int(mclust_options("subset")):
        subset = _sample_subset(n, int(mclust_options("subset")))

    Vinv_out = Vinv
    if noise is not None and (Vinv is None or float(Vinv) <= 0):
        # R: Vinv <- hypvol(data, reciprocal = TRUE)
        Vinv = hypvol(values, reciprocal=True)
        Vinv_out = Vinv
    if noise is not None:
        Vinv_out = float(Vinv)
        Vinv = float(Vinv)

    l, m = len(groups), len(models)
    BIC = np.full((l, m), _EMPTY)
    RET = np.full((l, m), _EMPTY)
    row_of = {g: i for i, g in enumerate(groups)}
    work = list(groups)

    def result(init_out: dict[str, Any], early: bool = False) -> dict[str, Any]:
        values_out = BIC.copy()
        if early:
            values_out[values_out == _EMPTY] = np.nan
        return {
            "values": values_out, "G": list(groups), "modelNames": models,
            "prior": prior, "control": control, "initialization": init_out,
            "Vinv": Vinv_out, "warn": warn, "n": n, "d": d, "oneD": d == 1,
            "criterion": "BIC", "returnCodes": RET.copy(), "class": "mclustBIC",
        }

    if noise is None:
        # R: the standard model, no noise component.
        if work[0] == 1:
            i1 = row_of[1]
            for j, mdl in enumerate(models):
                if BIC[i1, j] == _EMPTY:
                    out = mvn(mdl, values, prior=prior, warn=warn)
                    BIC[i1, j] = bic(mdl, out["loglik"], n, d, 1, equalPro=False)
                    RET[i1, j] = float(out.get("returnCode", 0.0))
            if l == 1:
                return result({"hcPairs": hc_pairs, "subset": subset, "noise": None}, early=True)
            work = work[1:]

        if subset is None:
            # R: all rows form the initial hierarchical clustering.
            if hc_pairs is None and d != 1:
                hc_pairs = _hc_start(values, n, d)
            clss = hclass(hc_pairs, work) if (d > 1 or hc_pairs is not None) else None
            for j, g in enumerate(work):
                cl = clss[:, j] if clss is not None else qclass(values[:, 0], g)
                z = unmap(cl, groups=list(range(1, int(np.max(cl)) + 1)))
                if warn and np.any(z.max(axis=0) == 0):
                    z = _missing_group_fix(z)
                i = row_of[g]
                for jm, mdl in enumerate(models):
                    if BIC[i, jm] == _EMPTY:
                        out = me(values, mdl, z, prior=prior, control=control, warn=warn)
                        BIC[i, jm] = bic(mdl, out["loglik"], n, d, g, equalPro=equal_pro)
                        RET[i, jm] = float(out["returnCode"])
        else:
            # R: the hierarchical start is taken on the initial subset only.
            sub = values[subset - 1]
            if hc_pairs is None and d != 1:
                hc_pairs = _hc_start(sub, n, d)
            clss = hclass(hc_pairs, work) if (d > 1 or hc_pairs is not None) else None
            for j, g in enumerate(work):
                cl = clss[:, j] if clss is not None else qclass(sub[:, 0], g)
                z = unmap(cl, groups=list(range(1, int(np.max(cl)) + 1)))
                if warn and np.any(z.max(axis=0) == 0):
                    z = _missing_group_fix(z)
                i = row_of[g]
                for jm, mdl in enumerate(models):
                    if np.isnan(BIC[i, jm]):
                        continue
                    ms = mstep(sub, mdl, z, prior=prior, control=control, warn=warn)
                    es = estep(values, mdl, ms["parameters"], warn=warn)
                    out = me(values, mdl, es["z"], prior=prior, control=control, warn=warn)
                    BIC[i, jm] = bic(mdl, out["loglik"], n, d, g, equalPro=equal_pro)
                    RET[i, jm] = float(out["returnCode"])
        return result({"hcPairs": hc_pairs, "subset": subset, "noise": None})

    # R: the noise model. The noise rows are fixed to the extra component.
    if nnoise == n:
        raise ValueError("All observations cannot be initialised as noise!")
    noise_mask = np.zeros(n, dtype=bool)
    noise_mask[noise - 1] = True
    if subset is None:
        keep = ~noise_mask
        if work[0] == 0:
            BIC[row_of[0], :] = 2.0 * (n * np.log(Vinv)) - np.log(n)
            if l == 1:
                return result({"hcPairs": hc_pairs, "subset": None, "noise": noise}, early=True)
            work = work[1:]
        if hc_pairs is None and d != 1:
            hc_pairs = _hc_start(values[keep], n, d)
        clss = hclass(hc_pairs, work) if (d > 1 or hc_pairs is not None) else None
        kmax = max(work) + 1 if work else 1
        for j, g in enumerate(work):
            k = g
            z = np.zeros((n, kmax))
            cl = clss[:, j] if clss is not None else qclass(values[keep, 0], k)
            z[keep, :k] = unmap(cl, groups=list(range(1, int(np.max(cl)) + 1)))
            if warn and np.any(z[keep, :k].max(axis=0) == 0):
                # R: z[-noise, 1:k] <- max(...) then row-normalised; the result is 1/k.
                z[keep, :k] = 1.0 / k
            z[noise_mask, k] = 1.0
            i = row_of[g]
            for jm, mdl in enumerate(models):
                if BIC[i, jm] == _EMPTY:
                    out = me(values, mdl, z[:, : k + 1], prior=prior, Vinv=Vinv,
                             control=control, warn=warn)
                    BIC[i, jm] = bic(mdl, out["loglik"], n, d, k, noise=True, equalPro=equal_pro)
                    RET[i, jm] = float(out["returnCode"])
        return result({"hcPairs": hc_pairs, "subset": subset, "noise": noise})

    # R: the noise model with an initial subset.
    seen: list[int] = []
    for s in subset.tolist():
        if s not in seen and s not in set(noise.tolist()):
            seen.append(s)
    subset = np.asarray(seen, dtype=int)
    if subset.size == 0:
        raise ValueError("No observations in the initial subset after removing the noise!")
    if work[0] == 0:
        BIC[row_of[0], :] = 2.0 * (n * np.log(Vinv)) - np.log(n)
        if l == 1:
            return result({"hcPairs": hc_pairs, "subset": subset, "noise": noise}, early=True)
        work = work[1:]
    sub = values[subset - 1]
    if hc_pairs is None and d != 1:
        hc_pairs = _hc_start(sub, n, d)
    clss = hclass(hc_pairs, work) if (d > 1 or hc_pairs is not None) else None
    for j, g in enumerate(work):
        k = g
        cl = clss[:, j] if clss is not None else qclass(sub[:, 0], k)
        z = unmap(cl, groups=list(range(1, int(np.max(cl)) + 1)))
        if warn and np.any(z.max(axis=0) == 0):
            z = _missing_group_fix(z)
        i = row_of[g]
        for jm, mdl in enumerate(models):
            if BIC[i, jm] != _EMPTY:
                continue
            ms = mstep(sub, mdl, z, prior=prior, control=control, warn=warn)
            es = estep(values, mdl, ms["parameters"], warn=warn)
            if np.isnan(float(es["loglik"])):
                BIC[i, jm] = np.nan
                RET[i, jm] = float(es.get("returnCode", -1.0))
                continue
            ez = np.column_stack([np.asarray(es["z"], dtype=float), np.zeros(n)])
            ez[noise - 1, :] = np.concatenate([np.zeros(k), [1.0]])
            out = me(values, mdl, ez, prior=prior, Vinv=Vinv, control=control, warn=warn)
            BIC[i, jm] = bic(mdl, out["loglik"], n, d, k, noise=True, equalPro=equal_pro)
            RET[i, jm] = float(out["returnCode"])
    return result({"hcPairs": hc_pairs, "subset": subset, "noise": noise})


def mclustModel(data: Any, BICvalues: Any, G: Any = None,
                modelNames: Any = None, **kwargs: Any) -> dict[str, Any]:
    """Select the best BIC model and return its fitted-model summary."""
    initialization = _get(BICvalues, "initialization")
    noise = _get(initialization, "noise") if initialization is not None else None
    summary = (summaryMclustBICn if noise is not None else summaryMclustBIC)(
        BICvalues, data=data, G=G, modelNames=modelNames, **kwargs
    )
    for key in ("classification", "uncertainty", "prior", "control", "initialization"):
        summary.pop(key, None)
    summary.pop("bestBICvalues", None)
    return summary


def _format(value: float, digits: int = 6) -> str:
    if np.isnan(value):
        return "NA"
    if np.isposinf(value):
        return "Inf"
    if np.isneginf(value):
        return "-Inf"
    return f"{value:.{digits}g}"


def print_mclustBIC(x: Any, pick: int = 3, digits: int = 6, **_: Any) -> str:
    """Render the BIC matrix and its highest scoring models."""
    values = np.asarray(_get(x, "values", x), dtype=float)
    values = np.atleast_2d(values)
    rows = _names(x, "G", values.shape[0], [str(i) for i in range(1, values.shape[0] + 1)])
    cols = _names(x, "modelNames", values.shape[1], [str(i) for i in range(values.shape[1])])
    lines = ["Bayesian Information Criterion (BIC): "]
    lines.append("  " + " ".join(cols))
    for row, label in zip(values, rows):
        lines.append(f"{label} " + " ".join(f"{_format(float(v), digits):>3}" for v in row))
    finite = np.where(np.isfinite(values), values, -np.inf).ravel(order="F")
    order = np.argsort(-finite, kind="stable")[: max(0, int(pick))]
    lines += ["", f"Top {pick} models based on the BIC criterion: "]
    labels: list[str] = []
    scores: list[str] = []
    for index in order:
        i, j = np.unravel_index(index, values.shape, order="F")
        if np.isfinite(values[i, j]):
            labels.append(f"{cols[j]},{rows[i]}")
            scores.append(_format(float(values[i, j]), digits))
    lines.append(" ".join(labels) + " ")
    if scores:
        lines.append(f"{scores[0]:>5}" + "".join(" " + f"{score:>6}" for score in scores[1:]) + " ")
    else:
        lines.append(" ")
    return "\n".join(lines)

