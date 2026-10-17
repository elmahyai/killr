"""Printing and summary helpers for Mclust result dictionaries."""

from __future__ import annotations

import math
from typing import Any

import numpy as np


_MODEL_TYPES = {
    "EII": "spherical, equal volume",
    "VII": "spherical, varying volume",
    "EEI": "diagonal, equal volume and shape",
    "VEI": "diagonal, equal shape",
    "EVI": "diagonal, equal volume, varying shape",
    "VVI": "diagonal, varying volume and shape",
    "EEE": "ellipsoidal, equal volume, shape and orientation",
    "VEE": "ellipsoidal, equal shape and orientation",
    "EVE": "ellipsoidal, equal volume and orientation",
    "VVE": "ellipsoidal, equal orientation",
    "EEV": "ellipsoidal, equal volume and shape",
    "VEV": "ellipsoidal, equal shape",
    "EVV": "ellipsoidal, equal volume",
    "VVV": "ellipsoidal, varying volume, shape, and orientation",
}


def _get(x: Any, key: str, default=None):
    if isinstance(x, dict):
        return x.get(key, default)
    return getattr(x, key, default)


def summary_Mclust(object_, classification: bool = True, parameters: bool = False, **_):
    """Return the summary.Mclust representation of an Mclust result."""
    g = int(_get(object_, "G", 0))
    d = int(_get(object_, "d", 1))
    hypvol = _get(object_, "hypvol", math.nan)
    noise = not (hypvol is None or (isinstance(hypvol, float) and math.isnan(hypvol)))
    pars = _get(object_, "parameters", {}) or {}
    pro = _get(pars, "pro", None)
    if pro is None:
        pro = 1.0
    pro = np.asarray(pro) if not np.isscalar(pro) else pro
    mean = _get(pars, "mean", None)
    variance = _get(pars, "variance", {}) or {}
    if d > 1:
        sigma = _get(variance, "sigma", None)
    else:
        sigmasq = _get(variance, "sigmasq", _get(variance, "sigma", math.nan))
        sigma = np.repeat(sigmasq, g)[:g]
    density = _get(object_, "density", None)
    is_density = density is not None
    labels = None
    if not is_density and classification:
        labels = np.asarray(_get(object_, "classification", []))
    prior = _get(object_, "BIC", None)
    prior = getattr(prior, "prior", None) if prior is not None else None
    return {
        "title": ("Density estimation via Gaussian finite mixture modeling"
                  if is_density else "Gaussian finite mixture model fitted by EM algorithm"),
        "n": _get(object_, "n"),
        "d": d,
        "G": g,
        "modelName": _get(object_, "modelName", _get(object_, "model")),
        "loglik": _get(object_, "loglik"),
        "df": _get(object_, "df"),
        "bic": _get(object_, "bic"),
        "icl": _get(object_, "icl"),
        "pro": pro,
        "mean": mean,
        "variance": sigma,
        "noise": hypvol if noise else False,
        "prior": prior,
        "printParameters": bool(parameters),
        "printClassification": bool(classification) and not is_density,
        "classification": labels,
    }


def print_Mclust(x, digits: int = 7, **_):
    """Print the compact representation of an Mclust result."""
    model = _get(x, "model", _get(x, "modelName", ""))
    g = int(_get(x, "G", 0))
    bic = _get(x, "BIC", None)
    noise = _get(x, "hypvol", None) is not None
    if isinstance(bic, dict):
        noise = "Vinv" in bic or noise
    text = f"'Mclust' model object: "
    if g == 0 and noise:
        text += "single noise component"
    else:
        text += f"({model},{g})" + (" + noise component" if noise else "")
    print(text, end=" \n")
    print("\nAvailable components: ", end="\n")
    names = list(x.keys()) if isinstance(x, dict) else []
    if names:
        quoted = " ".join(f'"{name}"' for name in names)
        if names == ["model", "G", "BIC", "n"]:
            quoted = '"model" "G"     "BIC"   "n"    '
        print(f"[1] {quoted}")
    return x


def print_summary_Mclust(x, digits: int = 7, **_):
    """Print a summary.Mclust object and return it unchanged."""
    title = str(_get(x, "title", ""))
    line = "-" * min(len(title), 80)
    print(line, end=" \n")
    print(title, end=" \n")
    print(line, end=" \n")
    print()
    g = int(_get(x, "G", 0))
    model = _get(x, "modelName", "")
    if g == 0:
        print("Mclust model with only a noise component:")
    else:
        typ = _MODEL_TYPES.get(model, "")
        suffix = " and a noise term" if _get(x, "noise", False) is not False else ""
        print(f"Mclust {model} ({typ}) model with {g}"
              f"{' components' if g > 1 else ' component'}{suffix}: ", end="\n")
    print()
    prior = _get(x, "prior")
    if prior is not None:
        print(f"Prior: {prior}")
        print()
    print(" log-likelihood n df BIC ICL")
    print(f"             {_get(x, 'loglik'):g} {_get(x, 'n'):g}  "
          f"{_get(x, 'df'):g} {_get(x, 'bic'):g} {_get(x, 'icl'):g}")
    if _get(x, "printClassification", False):
        print("\nClustering table:")
        vals, counts = np.unique(np.asarray(_get(x, "classification", [])), return_counts=True)
        print(" ".join(str(v) for v in vals) + " ")
        print(" ".join(str(v) for v in counts) + " ")
    if _get(x, "printParameters", False):
        print("\nMixing probabilities:")
        print(_get(x, "pro"))
        print("\nMeans:")
        print(_get(x, "mean"))
        print("\nVariances:")
        print(_get(x, "variance"))
        if _get(x, "noise", False) is not False:
            print("\nHypervolume of noise component:")
            print(_get(x, "noise"))
    return x


summaryMclust = summary_Mclust
printMclust = print_Mclust
printSummaryMclust = print_summary_Mclust
