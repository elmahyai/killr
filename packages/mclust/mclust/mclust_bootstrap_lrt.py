"""Port of R ``mclustBootstrapLRT`` (mclust 6.1.3, R/bootstrap.R).

Sequential parametric-bootstrap likelihood-ratio test for the number of
mixture components. The random draws come from the same R-compatible stream
as ``sim`` (``boot.rng``), so with the same seed the result matches R.

``verbose`` is accepted and ignored: R prints a text progress bar only when it
is TRUE, and that output is not part of the result.
"""

from __future__ import annotations

import warnings
from typing import Any

import numpy as np

from mclust.bic_family import mclustBIC, summaryMclustBIC
from mclust.em import em
from mclust.estep import estep
from mclust.model_metadata import checkModelName
from mclust.mvn import mvnX, mvnXXX
from mclust.sim import sim

__all__ = ["mclust_bootstrap_lrt", "mclustBootstrapLRT"]


def _boot_data(sample: Any, d: int) -> np.ndarray:
    """R ``bootSample[, -1]``: drop the label column; a single column becomes a vector."""
    arr = np.asarray(sample, dtype=float)
    return arr[:, 1] if d == 1 else arr[:, 1:]


def mclust_bootstrap_lrt(
    data: Any,
    model_name: str | None = None,
    nboot: int = 999,
    level: float = 0.05,
    max_g: Any = None,
    verbose: Any = None,
    **kwargs: Any,
) -> dict[str, Any] | None:
    """Bootstrap sequential LRT for the number of components (R ``mclustBootstrapLRT``).

    Returns a dict with ``G``, ``modelName``, ``obs``, ``boot`` (nboot x steps),
    and ``p.value``, with class ``mclustBootstrapLRT``. Returns None, with a
    warning, when only one component can be fitted (as R does).
    """
    _ = verbose
    if kwargs:
        raise NotImplementedError(
            "mclustBootstrapLRT extra '...' arguments are not translated: "
            + ", ".join(sorted(kwargs))
        )
    if model_name is None:
        raise ValueError(
            "A 'modelName' must be provided. Please see help(mclustModelNames) "
            "which describes the available models."
        )
    model = str(model_name)
    checkModelName(model)
    if "X" in model:
        raise ValueError("Specified 'modelName' is only valid for one-component mixture.")

    # R: G is 1:9 by default, or 1:(maxG + 1).
    if max_g is None:
        G = list(range(1, 10))
    else:
        G = list(range(1, int(float(max_g)) + 2))
    BIC = mclustBIC(data, G=G, modelNames=model, warn=False, verbose=False)
    names = [str(v) for v in BIC["modelNames"]]
    if model not in names:
        raise ValueError(
            "'modelName' not compatibile with data. Please see help(mclustModelNames) "
            "which describes the available models."
        )
    column = np.asarray(BIC["values"], dtype=float)[:, names.index(model)]
    # R: G <- G[!is.na(BIC)]
    G_fit = [int(g) for g, v in zip(BIC["G"], column) if not np.isnan(v)]
    if not G_fit:
        raise ValueError(f"no model {model} can be fitted.")
    if all(g == 1 for g in G_fit):
        warnings.warn("only 1-component model could be fitted. No LRT is performed!")
        return None
    if np.any(np.isnan(column)):
        warnings.warn("some model(s) could not be fitted!")

    x = np.asarray(data, dtype=float)
    d = 1 if x.ndim == 1 or x.shape[1] == 1 else int(x.shape[1])
    steps = max(G_fit) - 1
    obs = np.zeros(steps)
    p_value = np.zeros(steps)
    boot = np.full((nboot, steps), np.nan)

    g = 0
    keep_going = True
    while g < steps and keep_going:
        g += 1
        mod0 = summaryMclustBIC(BIC, data, G=g, modelNames=model)
        mod1 = summaryMclustBIC(BIC, data, G=g + 1, modelNames=model)
        obs[g - 1] = 2 * (mod1["loglik"] - mod0["loglik"])
        b = 0
        while b < nboot:
            b += 1
            sample = sim(mod0["modelName"], mod0["parameters"], n=mod0["n"])
            boot_x = _boot_data(sample, d)
            name0 = mod0["modelName"]
            if name0 == "X":
                loglik0 = mvnX(boot_x, warn=False)["loglik"]
            elif name0 in ("XII", "XXI", "XXX"):
                # R calls mvnXXX for all three single-component names.
                loglik0 = mvnXXX(boot_x, warn=False)["loglik"]
            else:
                param0 = em(boot_x, name0, mod0["parameters"], warn=False)["parameters"]
                loglik0 = estep(boot_x, name0, param0, warn=False)["loglik"]
            param1 = em(boot_x, mod1["modelName"], mod1["parameters"], warn=False)["parameters"]
            loglik1 = estep(boot_x, mod1["modelName"], param1, warn=False)["loglik"]
            lrts = 2 * (loglik1 - loglik0)
            if np.isnan(lrts):
                # R: b <- b - 1; next
                b -= 1
                continue
            boot[b - 1, g - 1] = lrts
        p_value[g - 1] = (1 + np.sum(boot[:, g - 1] >= obs[g - 1])) / (nboot + 1)
        if max_g is None and p_value[g - 1] > level:
            keep_going = False

    out = {
        "G": list(range(1, g + 1)),
        "modelName": model,
        "obs": obs[:g].copy(),
        "boot": boot[:, :g].copy(),
        "p.value": p_value[:g].copy(),
        "class": "mclustBootstrapLRT",
    }
    return out


mclustBootstrapLRT = mclust_bootstrap_lrt
