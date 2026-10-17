"""GMMDR direction subset selection dispatcher (``MclustDRsubsel``)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Sequence

from mclust.mclust_options import mclust_options

__all__ = ["MclustDRsubsel"]


def MclustDRsubsel(
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
    """Subset selection for GMMDR directions based on Bayes factors.

    R sets ``hcUse = "VARS"`` for the whole call and restores it on exit, so the
    same is done here.
    """
    dr_type = object["type"] if isinstance(object, Mapping) else object.type
    if dr_type == "Mclust":
        from mclust.mclust_dr_subsel_cluster import MclustDRsubsel_cluster as fn
    elif dr_type in ("EDDA", "MclustDA"):
        from mclust.mclust_dr_subsel_classif import MclustDRsubsel_classif as fn
    else:
        raise ValueError("Not allowed 'MclustDR' type!")

    previous = mclust_options("hcUse")
    mclust_options(hcUse="VARS")
    try:
        return fn(
            object,
            g,
            model_names,
            bic_stop=bic_stop,
            bic_cutoff=bic_cutoff,
            mindir=mindir,
            verbose=verbose,
            **kwargs,
        )
    finally:
        mclust_options(hcUse=previous)
