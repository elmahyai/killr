"""One greedy subset-selection cycle for GMMDR (``MclustDRsubsel1cycle``)."""

from __future__ import annotations

import math
import sys
from typing import Any, Mapping, Sequence

import numpy as np

from mclust.bic_family import mclustBIC
from mclust.mclust_dr_bicreg import MclustDRBICreg

__all__ = ["MclustDRsubsel1cycle"]


def _is_mclust_dr(obj: Any) -> bool:
    if isinstance(obj, Mapping):
        return "dir" in obj and "numdir" in obj
    return hasattr(obj, "dir") and hasattr(obj, "numdir")


def _field(obj: Any, name: str) -> Any:
    if isinstance(obj, Mapping):
        return obj[name]
    return getattr(obj, name)


def _bic_table(data: np.ndarray, g: Sequence[int], model_names: Sequence[str]):
    """``mclustBIC(data, G = G, modelNames = ...)`` as (values, G labels, model labels)."""
    bic = mclustBIC(data, G=list(g), modelNames=list(model_names), verbose=False)
    values = np.atleast_2d(np.asarray(bic["values"], dtype=float))
    return values, [int(v) for v in bic["G"]], [str(v) for v in bic["modelNames"]]


def _default_model_names() -> list[str]:
    return [
        "EII", "VII", "EEI", "VEI", "EVI", "VVI", "EEE", "VEE", "EVE", "VVE", "EEV", "VEV",
        "EVV", "VVV",
    ]


def MclustDRsubsel1cycle(
    object: Any,
    g: Sequence[int] | None = None,
    model_names: Sequence[str] | None = None,
    *,
    bic_stop: float = 0,
    bic_cutoff: float = 0,
    verbose: bool = False,
) -> dict[str, Any]:
    """Single greedy subset-selection cycle from Bayes factors on GMMDR directions."""
    if not _is_mclust_dr(object):
        raise ValueError("first argument must be an object of class 'MclustDR'")
    if g is None:
        g = list(range(1, 10))
    if model_names is None:
        model_names = _default_model_names()
    g = [int(x) for x in g]
    model_names = list(model_names)

    d = int(_field(object, "numdir"))
    direction = np.asarray(_field(object, "dir"), dtype=float)
    if direction.ndim == 1:
        direction = direction.reshape(-1, 1)
    direction = direction[:, :d]
    dir_names = [f"Dir{i + 1}" for i in range(d)]

    eps = math.sqrt(sys.float_info.epsilon)
    bic_stop = float(bic_stop) + eps
    bic_cutoff = float(bic_cutoff) + eps
    model_1d = ["E", "V"] if any("V" in m for m in model_names) else ["E"]

    inc: list[int] = []
    excl = list(range(1, d + 1))
    tab_rows: list[dict[str, Any]] = []
    model1: dict[str, Any] = {"bic": 0.0}

    while excl:
        model2_rows: list[dict[str, Any]] = []
        for j in excl:
            cols = sorted(inc + [j])
            sub = direction[:, [c - 1 for c in cols]]
            names = model_names if inc else model_1d
            bic, bic_g, bic_models = _bic_table(sub, g, names)
            bic_max = np.nanmax(bic)
            # R: (max(bic) - bic < bic.cutoff) * 1; NA entries count as 0.
            bic_tab = ((bic_max - bic) < bic_cutoff).astype(float)
            row_ok = np.where(bic_tab.sum(axis=1) > 0)[0]
            if row_ok.size == 0:
                continue
            best_g = int(row_ok[0])
            col_ok = np.where(bic_tab[best_g, :] > 0)[0]
            best_mod = int(col_ok[0])
            bic_val = float(bic[best_g, best_mod])
            x_inc = direction[:, [c - 1 for c in inc]] if inc else None
            bic_diff = (
                bic_val
                - float(model1["bic"])
                - MclustDRBICreg(direction[:, j - 1], x_inc)
            )
            model2_rows.append(
                {
                    "Variable": dir_names[j - 1],
                    "model": bic_models[best_mod],
                    "G": bic_g[best_g],
                    "bic": bic_val,
                    "bic.diff": bic_diff,
                    "_j": j,
                }
            )
        if not model2_rows:
            break
        if verbose:
            print(model2_rows)
        diffs = [row["bic.diff"] for row in model2_rows]
        if max(diffs) < bic_stop and inc:
            break
        i = int(np.argmax(diffs))
        chosen = model2_rows[i]
        inc.append(int(chosen["_j"]))
        excl.remove(int(chosen["_j"]))
        tab_rows.append(
            {
                "Variable": chosen["Variable"],
                "Model": chosen["model"],
                "G": chosen["G"],
                "BIC": chosen["bic"],
                "BIC.dif": chosen["bic.diff"],
            }
        )
        model1 = chosen

    subsets = [inc[: k + 1] for k in range(len(tab_rows))]
    subset = subsets[-1] if subsets else []
    return {"subset": subset, "tab": tab_rows}
