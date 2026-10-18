"""Forecast fan. The bands are the normal intervals from predict."""

import numpy as np

from .dynamics import predict


def fanchart(x, cis=None, names=None):
    """Return the forecast bands a fan chart fills, and draw them.

    ``x`` is the dict returned by ``predict``. Each entry of the result is the
    lower and upper path at that interval, including the last observed value.
    """
    if cis is None:
        cis = np.arange(0.1, 1.0, 0.1)
    cis = np.asarray(cis, dtype=float)
    if np.min(cis) <= 0 or np.max(cis) >= 1:
        raise ValueError("confidence intervals must lie in (0, 1)")
    model = x["model"]
    chosen = list(model.names if names is None else names)
    endog = model.y
    n_ahead = x["fcst"].shape[0]
    bands = []
    for level in cis:
        step = predict(model, n_ahead=n_ahead, ci=float(level))
        bands.append(step)
    _draw(endog, chosen, bands, model.names)
    return {"cis": cis, "bands": bands}


def _draw(endog, chosen, bands, names):
    import importlib

    import matplotlib.pyplot as plt

    try:
        fan = importlib.import_module("killplot").fan
    except AttributeError:
        # packages/killplot shadows the installed package with the project folder.
        fan = importlib.import_module("killplot.killplot").fan

    colors = np.sqrt(np.linspace(0.05, 1.0, len(bands)))
    figure, axes = plt.subplots(len(chosen), 1, squeeze=False, figsize=(6, 2.2 * len(chosen)))
    for row, name in enumerate(chosen):
        column = names.index(name)
        series = endog[:, column]
        lower = np.vstack([
            np.concatenate([[series[-1]], band["lower"][:, column]]) for band in bands
        ])
        upper = np.vstack([
            np.concatenate([[series[-1]], band["upper"][:, column]]) for band in bands
        ])
        fan(axes[row, 0], series, lower, upper, colors)
        axes[row, 0].set_title(name)
    figure.tight_layout()
    return figure
