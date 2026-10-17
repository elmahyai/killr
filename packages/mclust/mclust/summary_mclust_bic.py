"""Summaries for mclust BIC matrices (mclust 6.1.3, R/mclust.R ``summaryMclustBIC``).

The best entry of the BIC matrix is refitted. With one component, the fit is
``mvn``. With more components, the classes come from the hierarchical start
(``hclass``) or the quantile start (``qclass``) for one-dimensional data. They
go through ``me``, and one extra ``mstep`` runs when the mixing proportions
differ from the column means of ``z``.

When the BIC object has an initial ``subset``, R starts from that subset and
does not take the proportions test. ``summaryMclustBICn`` is the noise
variant (``R/mclust.R`` ``summaryMclustBICn``): the noise rows are the extra
component, ``G = 0`` is the noise-only fit, and ``Vinv`` is the noise density.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any

import numpy as np

from ._qclass import qclass
from .bic import bic
from .estep import estep
from .hclass import hclass
from .map_util import map as r_map
from .me import me
from .model_metadata import nMclustParams
from .mstep_loglik_icl import mstep
from .mvn import mvn
from .pick_bic import pickBIC
from .unmap_util import unmap


def _get(x: Any, name: str, default: Any = None) -> Any:
    if isinstance(x, Mapping):
        return x.get(name, default)
    return getattr(x, name, default)


def _matrix(object_: Any) -> tuple[np.ndarray, list[str], list[str]]:
    values = _get(object_, "values", object_)
    values = np.asarray(values, dtype=float)
    if values.ndim != 2:
        values = np.atleast_2d(values)
    rows = [str(v) for v in (_get(object_, "G") or range(1, values.shape[0] + 1))]
    cols = [str(v) for v in (_get(object_, "modelNames") or
                             [str(i) for i in range(values.shape[1])])]
    return values, rows, cols


def _best(object_: Any, G: Any, model_names: Any) -> list[dict[str, Any]]:
    """R: ``pickBIC(object[G, modelNames], k = 3)``, as ``modelName``/``G``/``criterion``."""
    values, rows, cols = _matrix(object_)
    if G is not None:
        keep = {str(v) for v in np.atleast_1d(G)}
        idx = [i for i, v in enumerate(rows) if v in keep]
        values, rows = values[idx], [rows[i] for i in idx]
    if model_names is not None:
        keep = {str(v) for v in np.atleast_1d(model_names)}
        idx = [i for i, v in enumerate(cols) if v in keep]
        values, cols = values[:, idx], [cols[i] for i in idx]
    picked = pickBIC(
        {"values": values, "G": [int(float(r)) for r in rows], "modelNames": cols}, k=3
    )
    if picked is None:
        return []
    out = []
    for value, name in zip(picked["values"], picked["names"] or []):
        if np.isnan(value):
            continue
        model, g = name.rsplit(",", 1)
        out.append({"modelName": model, "G": int(g), "criterion": float(value)})
    return out


def _normalise_data(data: Any) -> np.ndarray:
    x = np.asarray(data, dtype=float)
    if x.ndim == 1:
        return x[:, None]
    if x.ndim != 2:
        raise ValueError("data must be a vector or a matrix")
    return x


def _equal_pro(control: Any) -> bool:
    if control is None:
        return False
    if isinstance(control, Mapping):
        return bool(control.get("equalPro", False))
    return bool(getattr(control, "equalPro", False))


def _one_based(values: Any) -> np.ndarray:
    a = np.asarray(values)
    if a.dtype == bool:
        return np.flatnonzero(a) + 1
    return np.asarray(a, dtype=int).reshape(-1)


def _subset_rows(subset: np.ndarray, noise: np.ndarray | None) -> np.ndarray:
    """R: ``setdiff(subset, noise)``, keeping the order of ``subset``."""
    drop = set() if noise is None else set(noise.tolist())
    seen: list[int] = []
    for s in subset.tolist():
        if s not in drop and s not in seen:
            seen.append(s)
    return np.asarray(seen, dtype=int)


def _start_labels(hc_pairs: Any, groups: int, rows: np.ndarray, d: int) -> np.ndarray:
    """R: ``unmap(hclass(hcPairs, G))`` when there is a hierarchical start, else ``qclass``."""
    if d > 1 or hc_pairs is not None:
        cls = hclass(hc_pairs, [groups])[:, 0]
        return unmap(cls, groups=sorted(set(cls.tolist())))
    return unmap(qclass(rows[:, 0], groups), groups=list(range(1, groups + 1)))


def _summary_multi(object_: Any, x: np.ndarray, model: str, groups: int,
                   best: list[dict[str, Any]]) -> dict[str, Any]:
    """R: the ``G > 1`` branch of ``summaryMclustBIC``, with or without an initial subset."""
    n, d = x.shape
    init = _get(object_, "initialization") or {}
    hc_pairs = _get(init, "hcPairs")
    subset = _get(init, "subset")
    prior = _get(object_, "prior")
    control = _get(object_, "control")
    warn = _get(object_, "warn")
    data = x if d > 1 else x[:, 0]

    if subset is None:
        z = _start_labels(hc_pairs, groups, x, d)
        out = me(data, model, z, prior=prior, control=control, warn=warn)
        pro = np.asarray(out["parameters"]["pro"], dtype=float)
        col_means = np.mean(out["z"], axis=0)
        if float(np.sum((pro - col_means) ** 2)) > math.sqrt(np.finfo(float).eps):
            ms = mstep(data, model, z=out["z"], prior=prior, warn=warn)
            if ms.get("returnCode") == 0:
                out["parameters"] = ms["parameters"]
    else:
        sub_idx = _one_based(subset) - 1
        sub = x[sub_idx]
        sub_data = sub if d > 1 else sub[:, 0]
        z = _start_labels(hc_pairs, groups, sub, d)
        ms = mstep(sub_data, model, z, prior=prior, control=control, warn=warn)
        es = estep(data, model, ms["parameters"], warn=warn)
        out = me(data, model, es["z"], prior=prior, control=control, warn=warn)
        ms = mstep(data, model, out["z"], prior=prior, warn=warn)
        if ms.get("returnCode") == 0:
            out["parameters"] = ms["parameters"]

    zz = np.asarray(out["z"], dtype=float)
    classification = r_map(zz, warn=warn)
    uncertainty = 1.0 - np.max(zz, axis=1)
    G_fit = int(out.get("G", groups))
    value = bic(model, out["loglik"], n, d, G_fit, noise=False, equalPro=_equal_pro(control))
    return {
        "modelName": out.get("modelName", model), "n": n, "d": d, "G": G_fit,
        "bic": float(value), "loglik": out["loglik"], "parameters": out["parameters"],
        "z": zz, "classification": classification, "uncertainty": uncertainty,
        "bestBICvalues": best, "prior": prior, "control": control,
        "initialization": init,
    }


def _summary_noise(object_: Any, x: np.ndarray, model: str, groups: int,
                   best: list[dict[str, Any]]) -> dict[str, Any]:
    """R: ``summaryMclustBICn`` for the best entry, with the noise component."""
    n, d = x.shape
    init = _get(object_, "initialization") or {}
    hc_pairs = _get(init, "hcPairs")
    subset = _get(init, "subset")
    noise = _get(init, "noise")
    noise = None if noise is None else _one_based(noise)
    prior = _get(object_, "prior")
    control = _get(object_, "control")
    warn = _get(object_, "warn")
    vinv = float(_get(object_, "Vinv"))
    data = x if d > 1 else x[:, 0]
    criterion = best[0]["criterion"]

    if groups == 0:
        return {
            "modelName": model, "n": n, "d": d, "G": 0,
            "bic": criterion, "loglik": n * math.log(vinv), "Vinv": vinv,
            "parameters": None, "z": np.ones((n, 1)),
            "classification": np.zeros(n, dtype=int), "uncertainty": np.zeros(n),
            "bestBICvalues": best, "prior": prior, "control": control,
            "initialization": init,
        }

    G1 = groups + 1
    noise_mask = np.zeros(n, dtype=bool)
    if noise is not None:
        noise_mask[noise - 1] = True
    if subset is None:
        keep = ~noise_mask
        z = np.zeros((n, G1))
        z[keep, :groups] = _start_labels(hc_pairs, groups, x[keep], d)
        z[noise_mask, groups] = 1.0
        out = me(data, model, z, prior=prior, Vinv=vinv, control=control, warn=warn)
    else:
        sub_idx = _subset_rows(_one_based(subset), noise) - 1
        sub = x[sub_idx]
        sub_data = sub if d > 1 else sub[:, 0]
        z = _start_labels(hc_pairs, groups, sub, d)
        ms = mstep(sub_data, model, z, prior=prior, control=control, warn=warn)
        es = estep(data, model, ms["parameters"], warn=warn)
        ez = np.column_stack([np.asarray(es["z"], dtype=float), np.zeros(n)])
        ez[noise_mask, :] = np.concatenate([np.zeros(groups), [1.0]])
        out = me(data, model, ez, prior=prior, Vinv=vinv, control=control, warn=warn)

    zz = np.asarray(out["z"], dtype=float)
    classification = np.asarray(r_map(zz, warn=warn), dtype=int)
    classification[classification == G1] = 0
    uncertainty = 1.0 - np.max(zz, axis=1)
    return {
        "modelName": out.get("modelName", model), "n": n, "d": d,
        "G": int(out.get("G", groups)), "bic": criterion, "loglik": out["loglik"],
        "Vinv": vinv, "parameters": out["parameters"], "z": zz,
        "classification": classification, "uncertainty": uncertainty,
        "bestBICvalues": best, "prior": prior, "control": control,
        "initialization": init,
    }


def _summary(object_: Any, data: Any, G: Any, model_names: Any, noise: bool) -> dict[str, Any]:
    x = _normalise_data(data)
    best = _best(object_, G, model_names)
    if not best:
        return {"bestBICvalues": [], "prior": _get(object_, "prior"),
                "control": _get(object_, "control"),
                "initialization": _get(object_, "initialization")}
    winner = best[0]
    model = winner["modelName"]
    groups = int(winner["G"])
    if noise:
        return _summary_noise(object_, x, model, groups, best)
    if groups != 1:
        return _summary_multi(object_, x, model, groups, best)
    out = mvn(model, x, prior=_get(object_, "prior"))
    z = np.ones((len(x), 1))
    result = {
        "modelName": out.get("modelName", model), "n": len(x), "d": x.shape[1], "G": groups,
        "bic": float(2 * out["loglik"] - nMclustParams(model, x.shape[1], groups) * np.log(len(x))),
        "loglik": out["loglik"], "parameters": out.get("parameters"),
        "z": z, "classification": np.ones(len(x), dtype=int),
        "uncertainty": np.zeros(len(x)), "bestBICvalues": best,
    }
    result.update({k: v for k, v in out.items() if k not in result})
    # R: a one-component summary keeps the top BIC values as its bic.
    result["bic"] = np.asarray([item["criterion"] for item in best], dtype=float)
    return result


def summaryMclustBIC(object: Any, data: Any, G: Any = None,
                     modelNames: Any = None, **_: Any) -> dict[str, Any]:
    return _summary(object, data, G, modelNames, False)


def summaryMclustBICn(object: Any, data: Any, G: Any = None,
                      modelNames: Any = None, **_: Any) -> dict[str, Any]:
    return _summary(object, data, G, modelNames, True)


__all__ = ["summaryMclustBIC", "summaryMclustBICn"]
