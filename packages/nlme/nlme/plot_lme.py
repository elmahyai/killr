"""Residual diagnostic plot for ``lme`` fits (nlme ``plot.lme``).

In R, ``plot.lme <- plot.nls``: a lattice plot of the Pearson residuals against
the fitted values, optionally with a reference line and labels on the points
whose residuals are large. The R code reads the residuals and fitted values
from the ``lme`` object with ``resid(., type = "pearson")`` and ``fitted(.)``.

``plot_lme`` takes the fitted ``lme`` object (``nlme.lme_family.LmeResult``) and
reads those two vectors itself. ``plot_lme_values`` is the same drawing for a
caller that already has the fitted values and Pearson residuals, such as a
fixture read from R.
"""

from __future__ import annotations

import sys
from pathlib import Path
from statistics import NormalDist

import numpy as np

_KILLPLOT_DIR = Path(__file__).resolve().parents[3] / "packages" / "killplot"
if str(_KILLPLOT_DIR) not in sys.path:
    sys.path.insert(0, str(_KILLPLOT_DIR))

from killplot.residual_fitted import residual_fitted_plot  # noqa: E402

__all__ = ["plot_lme", "plot_lme_values"]

# R's defaults when a label attribute is missing: the deparsed formula parts.
_DEFAULT_XLAB = "fitted(.)"
_DEFAULT_YLAB = 'resid(., type = "pearson")'


def plot_lme(object, *args, **kwargs):
    """R ``plot.lme(object, ...)`` for a fitted ``LmeResult``.

    Reads ``fitted(object)`` (the innermost level) and
    ``residuals(object, type = "pearson")`` (the innermost residual divided by the
    stored standard deviation), then draws them. ``id``, ``idLabels``,
    ``idResType``, ``xlab``, ``ylab``, and ``abline`` follow ``plot.nls``.
    R's lattice panels are drawn here with killplot's residual-fitted panel.
    """
    level = kwargs.pop("level", -1)
    id_res_type = kwargs.pop("idResType", "pearson")
    if id_res_type != "pearson":
        raise NotImplementedError("normalized residuals are waiting on corStruct")
    form = kwargs.pop("form", None)
    if form is not None:
        raise NotImplementedError("a 'form' argument to plot.lme is not translated")
    kwargs.pop("grid", None)

    fitted = np.asarray(object.fitted, dtype=np.float64)[:, level]
    pearson = np.asarray(object.residuals, dtype=np.float64)[:, level] / float(object.sigma)

    group_name = object.coefficients_random_names[-1]
    groups = [str(value) for value in object.groups[group_name]]
    labels = _axis_labels(object)
    abline = kwargs.pop("abline", (0.0, 0.0))
    return plot_lme_values(
        fitted,
        pearson,
        xlab=kwargs.pop("xlab", labels["xlab"]),
        ylab=kwargs.pop("ylab", labels["ylab"]),
        groups=groups,
        id=kwargs.pop("id", None),
        id_labels=kwargs.pop("idLabels", None),
        abline=abline,
        **kwargs,
    )


def _axis_labels(object) -> dict[str, str]:
    """R's axis labels: ``"Fitted values"`` with the response unit, and the residual label."""
    units = getattr(object, "units", None) or {}
    label = "Fitted values"
    unit = units.get("y") if isinstance(units, dict) else None
    if unit:
        label = f"{label} {unit}"
    return {"xlab": label, "ylab": "Standardized residuals"}



def _id_threshold(id_value: float) -> float:
    """R ``-qnorm(id / 2)``: the Pearson residual size that gets a label."""
    return NormalDist().inv_cdf(1.0 - float(id_value) / 2.0)


def plot_lme_values(
    fitted,
    residuals,
    *,
    xlab: str = _DEFAULT_XLAB,
    ylab: str = _DEFAULT_YLAB,
    groups=None,
    id=None,
    id_labels=None,
    id_residuals=None,
    abline=(0.0, 0.0),
    grid: bool = True,
    ax=None,
):
    """Draw ``plot.lme``'s panel for given fitted values and Pearson residuals.

    ``fitted`` and ``residuals`` are the plotted x and y, in row order.
    ``groups`` are the group labels per row (R ``getGroups``); they label the
    points when ``id_labels`` is not given. ``id`` is a number in (0, 1): points
    whose ``id_residuals`` (default ``residuals``) exceed ``qnorm(1 - id / 2)``
    in absolute value get a label. ``abline`` is the reference line
    ``(intercept, slope)``; pass None when R's ``form`` argument was given, since
    R then draws no line.

    Returns a dict with the plotted values, the labelled points (``id_index`` is
    1-based, as R prints it), the labels, and the ``fig`` and ``ax`` used.
    """
    x = np.asarray(fitted, dtype=float).reshape(-1)
    y = np.asarray(residuals, dtype=float).reshape(-1)
    if x.shape != y.shape:
        raise ValueError("fitted and residuals must have the same length")
    n = x.size

    mask = None
    labels = None
    if id is not None:
        if isinstance(id, (str, bool)) or not np.isscalar(id):
            raise TypeError("'id' can only be a formula or numeric")
        if float(id) <= 0 or float(id) >= 1:
            raise ValueError("'id' must be between 0 and 1")
        res_for_id = y if id_residuals is None else np.asarray(id_residuals, dtype=float).reshape(-1)
        if res_for_id.shape != x.shape:
            raise ValueError("id_residuals must have one entry per point")
        mask = np.abs(res_for_id) > _id_threshold(id)
        if id_labels is None:
            base = groups if groups is not None else [str(i) for i in range(1, n + 1)]
        else:
            base = id_labels
        base = [str(v) for v in base]
        if len(base) != n:
            raise ValueError("'idLabels' of incorrect length")
        labels = base

    if ax is None:
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(7, 7))
    else:
        fig = ax.figure

    residual_fitted_plot(
        ax,
        x,
        y,
        xlab=xlab,
        ylab=ylab,
        abline=abline,
        grid=grid,
        label_mask=mask,
        labels=labels,
    )
    labelled = np.flatnonzero(mask) if mask is not None else np.array([], dtype=int)
    return {
        "x": x,
        "y": y,
        "abline": None if abline is None else np.asarray(abline, dtype=float),
        "id_index": labelled + 1,
        "id_labels": [labels[i] for i in labelled] if labels is not None else [],
        "xlab": xlab,
        "ylab": ylab,
        "panels": 1,
        "fig": fig,
        "ax": ax,
    }
