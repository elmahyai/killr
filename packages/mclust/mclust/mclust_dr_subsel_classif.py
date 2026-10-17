"""Classification GMMDR subset selection (``MclustDRsubsel_classif``).

Each candidate subset is refit with the translated ``MclustDA`` (EDDA or
MclustDA, as the object's ``type``), and the refit is reduced again with
``mclust_dr``. No R session is used.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

import numpy as np

from mclust.mclust_da import mclust_da
from mclust.mclust_dr import mclust_dr
from mclust.mclust_dr_bicreg import MclustDRBICreg
from mclust.mclust_dr_recoverdir import MclustDRrecoverdir
from mclust.mclust_options import mclust_options

__all__ = ["MclustDRsubsel_classif"]


def _field(obj: Any, name: str) -> Any:
    if isinstance(obj, Mapping):
        return obj[name]
    return getattr(obj, name)


def _one_d_names(model_names: Sequence[str]) -> list[str]:
    """R: c("E", "V") when any name has a V, else "E"."""
    return ["E", "V"] if any("V" in m for m in model_names) else ["E"]


def _mclust_drc_subsel1cycle(
    object: Any,
    g: Sequence[int],
    model_names: Sequence[str],
    *,
    bic_stop: float,
    verbose: bool,
) -> dict[str, Any]:
    """R: MclustDRCsubsel1cycle, one greedy Bayes-factor cycle on MclustDA refits."""
    del verbose
    d = int(_field(object, "numdir"))
    direction = np.asarray(_field(object, "dir"), dtype=float)
    if direction.ndim == 1:
        direction = direction.reshape(-1, 1)
    direction = direction[:, :d]
    dir_names = [f"[,{i + 1}]" for i in range(d)]
    eps = float(np.sqrt(np.finfo(float).eps))
    bic_stop = float(bic_stop) + eps
    model_1d = _one_d_names(model_names)
    classification = _field(object, "classification")
    model_type = str(_field(object, "type"))

    inc: list[int] = []
    excl = list(range(d))
    tab_rows: list[dict[str, Any]] = []
    model1_bic = 0.0

    while excl:
        model2_rows: list[dict[str, Any]] = []
        for j in excl:
            cols = sorted(inc + [j])
            mod = mclust_da(
                direction[:, cols],
                classification,
                G=list(g),
                model_names=list(model_names) if inc else model_1d,
                model_type=model_type,
            )
            bic_val = float(mod["bic"])
            x_inc = direction[:, inc] if inc else None
            bic_diff = bic_val - model1_bic - MclustDRBICreg(direction[:, j], x_inc)
            models = mod["models"]
            model_list = list(models.values()) if isinstance(models, Mapping) else list(models)
            model_rows = {
                "Variable": dir_names[j],
                "model": "|".join(str(m["modelName"]) for m in model_list),
                "G": "|".join(str(m["G"]) for m in model_list),
                "bic": bic_val,
                "bic.dif": bic_diff,
                "_j": j,
            }
            model2_rows.append(model_rows)
        diffs = [row["bic.dif"] for row in model2_rows]
        if max(diffs) < bic_stop and inc:
            break
        i = int(np.argmax(diffs))
        chosen = model2_rows[i]
        inc.append(int(chosen["_j"]))
        excl.remove(int(chosen["_j"]))
        tab_rows.append({k: chosen[k] for k in ("Variable", "model", "G", "bic", "bic.dif")})
        model1_bic = float(chosen["bic"])

    subsets = [inc[: k + 1] for k in range(len(tab_rows))]
    return {"subset": subsets[-1] if subsets else [], "tab": tab_rows}


def MclustDRsubsel_classif(
    object: Any,
    g: Sequence[int] | None = None,
    model_names: Sequence[str] | None = None,
    *,
    bic_stop: float = 0,
    bic_cutoff: float = 0,
    mindir: int = 1,
    verbose: bool = False,
    **kwargs: Any,
):
    """R: MclustDRsubsel_classif. ``bic_cutoff`` and ``kwargs`` are accepted and unused, as in R."""
    del bic_cutoff, kwargs
    if g is None:
        g = list(range(1, 10))
    if model_names is None:
        model_names = list(mclust_options("emModelNames"))
    g = [int(x) for x in g]
    model_names = list(model_names)

    drmodel = object
    lambda_ = float(_field(drmodel, "lambda"))
    numdir = int(_field(drmodel, "numdir"))
    numdir0 = numdir + 1
    direction = np.asarray(_field(drmodel, "dir"), dtype=float)
    if direction.ndim == 1:
        direction = direction.reshape(-1, 1)
    direction = direction[:, :numdir]
    mindir = max(1, int(mindir))
    mclust_type = str(_field(drmodel, "type"))
    original_class = _field(object, "classification")

    while numdir < numdir0:
        if int(verbose) > 0:
            print("\nCycle ...")
        out = _mclust_drc_subsel1cycle(
            drmodel,
            g,
            model_names,
            bic_stop=bic_stop,
            verbose=int(verbose) > 1,
        )
        subset = out["subset"]
        subdir = direction[:, subset]
        names = model_names if len(subset) > 1 else _one_d_names(model_names)
        numdir0 = numdir
        mod = mclust_da(
            subdir,
            original_class,
            G=g,
            model_names=names,
            model_type=mclust_type,
        )
        drmodel0 = mclust_dr(mod, lambda_=lambda_)
        if int(drmodel0["numdir"]) < mindir:
            break
        drmodel = drmodel0
        numdir = int(drmodel["numdir"])
        direction = np.asarray(drmodel["dir"], dtype=float)
        if direction.ndim == 1:
            direction = direction.reshape(-1, 1)
        direction = direction[:, :numdir]

    obj = dict(drmodel) if isinstance(drmodel, Mapping) else drmodel._store.copy()
    data = _field(object, "x")
    obj["basisx"] = MclustDRrecoverdir(drmodel, data=data, std=False)
    obj["std.basisx"] = MclustDRrecoverdir(drmodel, data=data, std=True)
    obj["_class"] = ("MclustDRsubsel", "MclustDR")
    return obj
