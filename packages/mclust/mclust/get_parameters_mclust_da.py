"""getParameters.MclustDA — extract per-class parameters from an MclustDA fit."""

from __future__ import annotations

import copy
from typing import Any, Mapping, MutableSequence, Sequence

import numpy as np

__all__ = ["getParameters_MclustDA"]


def getParameters_MclustDA(object: Mapping[str, Any]) -> list[Any]:
    """Return a list of per-class parameter lists like R ``getParameters.MclustDA``."""
    models = object["models"]
    if isinstance(models, Mapping):
        model_list: Sequence[Mapping[str, Any]] = [models[k] for k in models]
    else:
        model_list = list(models)

    nclass = len(model_list)
    par: MutableSequence[Any] = [None] * nclass
    outer_pro: int | None = None

    for i in range(nclass):
        mod = model_list[i]
        pi = copy.deepcopy(mod["parameters"])
        if pi.get("pro") is None:
            outer_pro = 1

        variance = pi.get("variance")
        if isinstance(variance, Mapping) and int(variance.get("d", 0)) < 2:
            g = int(mod["G"])
            sigma_src = np.asarray(variance["sigma"], dtype=float).reshape(-1)
            reps = int(np.ceil(g / max(sigma_src.size, 1)))
            sigma = np.tile(sigma_src, reps)[:g]
            var_copy = dict(variance)
            var_copy["sigma"] = sigma
            variance = var_copy
            pi["variance"] = variance

        if isinstance(pi.get("variance"), Mapping):
            pi["variance"] = np.asarray(pi["variance"]["sigma"], dtype=float)
        par[i] = pi

    if outer_pro is not None:
        par.append(outer_pro)
    return list(par)
