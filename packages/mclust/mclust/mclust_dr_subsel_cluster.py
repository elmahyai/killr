"""Clustering GMMDR subset selection (``MclustDRsubsel_cluster``)."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

import numpy as np

from mclust.mclust_dr import mclust_dr
from mclust.mclust_dr_recoverdir import MclustDRrecoverdir
from mclust.mclust_dr_subsel1cycle import MclustDRsubsel1cycle, _default_model_names
from mclust.mclust_object import Mclust

__all__ = ["MclustDRsubsel_cluster"]


def _field(obj: Any, name: str) -> Any:
    if isinstance(obj, Mapping):
        return obj[name]
    return getattr(obj, name)


def MclustDRsubsel_cluster(
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
    """Subset selection for an ``Mclust``-type ``MclustDR`` object."""
    del kwargs
    if g is None:
        g = list(range(1, 10))
    if model_names is None:
        model_names = _default_model_names()
    g = [int(v) for v in g]
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
    verbose = int(verbose)

    ncycle = 0
    while numdir < numdir0:
        ncycle += 1
        if verbose > 0:
            print(f"\nCycle {ncycle} ...")
        out = MclustDRsubsel1cycle(
            drmodel,
            g,
            model_names,
            bic_stop=bic_stop,
            bic_cutoff=bic_cutoff,
            verbose=verbose > 1,
        )
        if verbose > 0:
            print(out["tab"])
        subset = out["subset"]
        subdir = direction[:, [int(i) - 1 for i in subset]]
        # R: modelNames = if (length(subset) > 1) modelNames else c("E", "V")
        names = model_names if len(subset) > 1 else ["E", "V"]
        mod = Mclust(subdir, G=g, modelNames=names, verbose=False)
        numdir0 = numdir
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
