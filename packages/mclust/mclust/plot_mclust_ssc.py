"""Plotting method for semi-supervised ``MclustSSC`` fits."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np

from .mclust_1d_plot import mclust1Dplot
from .mclust_2d_plot import mclust2Dplot
from .plot_mclust_bic import plot_mclustBIC
from .plot_log import PlotLog

__all__ = ["plot_MclustSSC", "plot_mclustSSC"]


def _get(x: Any, name: str, default: Any = None) -> Any:
    return x.get(name, default) if isinstance(x, Mapping) else getattr(x, name, default)


def _parameters_for_dims(parameters: Mapping[str, Any], dims: np.ndarray) -> dict[str, Any]:
    pars = dict(parameters)
    mean = np.asarray(pars["mean"], dtype=float)
    if mean.ndim == 1:
        mean = mean.reshape(-1, 1)
    variance = dict(pars["variance"])
    sigma = np.asarray(variance.get("sigma"), dtype=float)
    pars["mean"] = mean[dims, :]
    if sigma.ndim == 3:
        variance["sigma"] = sigma[np.ix_(dims, dims, np.arange(sigma.shape[2]))]
    variance["d"] = int(dims.size)
    pars["variance"] = variance
    return pars


def plot_MclustSSC(
    x: Any,
    what: str | Sequence[str] = ("BIC", "classification", "uncertainty"),
    *,
    dimens: Sequence[int] | None = None,
    addEllipses: bool = True,
    ax: Any = None,
    log: PlotLog | None = None,
    **kwargs: Any,
) -> PlotLog:
    """Draw BIC, classification, and uncertainty plots for an SSC fit.

    This follows the non-interactive R method: requested plots are drawn in
    the order supplied, with the default order ``BIC``, classification, and
    uncertainty.  One- and two-dimensional data use the corresponding
    mclust plotting primitive.
    """
    del kwargs
    log = log or PlotLog()
    requested = [what] if isinstance(what, str) else list(what)
    data = np.asarray(_get(x, "data"), dtype=float)
    if data.ndim == 1:
        data = data[:, None]
    d_all = data.shape[1]
    dims = np.arange(d_all, dtype=int) if dimens is None else np.asarray(dimens, dtype=int).ravel() - 1
    dims = dims[(dims >= 0) & (dims < d_all)]
    if dims.size == 0:
        raise ValueError("invalid 'dimens' value(s) provided")
    classification = _get(x, "classification")
    z = _get(x, "z")
    parameters = _get(x, "parameters")
    for kind in requested:
        if kind == "BIC":
            bic = np.atleast_2d(np.asarray(_get(x, "BIC"), dtype=float))
            plot_mclustBIC({"values": bic, "G": [int(_get(x, "G", 1))],
                            "modelNames": [str(i + 1) for i in range(bic.shape[1])]},
                           canvas=log)
        elif kind in ("classification", "uncertainty"):
            if dims.size == 1:
                mclust1Dplot(data[:, dims], parameters=_parameters_for_dims(parameters, dims),
                             z=z, classification=classification, what=kind, ax=ax, log=log)
            elif dims.size == 2:
                mclust2Dplot(data[:, dims], parameters=_parameters_for_dims(parameters, dims),
                             z=z, classification=classification, what=kind,
                             addEllipses=addEllipses, ax=ax, log=log)
            else:
                raise NotImplementedError("plot.MclustSSC supports at most two dimensions")
        else:
            raise ValueError("what must contain BIC, classification, or uncertainty")
    return log


plot_mclustSSC = plot_MclustSSC
