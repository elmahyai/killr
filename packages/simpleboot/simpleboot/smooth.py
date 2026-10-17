"""Bootstrap of a one-predictor loess fit.

The local fit is the direct tricube regression used by
``loess(..., surface="direct")``: neighborhood size
``floor(n * span + 1e-5)``, squared-distance radius, and a weighted
quadratic. The default R surface interpolates those fits, so a point on
the boundary can differ. Residual resampling follows the package source,
which adds the resampled residual to the predictor.
"""

import math

import numpy as np
from matplotlib import pyplot as plt

from simpleboot.sampling import sample_indices, sample_replace


class LoessFit:
    def __init__(self, y, x, y_name, x_name, span=0.75, degree=2):
        self.y = np.asarray(y, dtype=float).reshape(-1)
        self.x = np.asarray(x, dtype=float).reshape(-1)
        self.y_name = y_name
        self.x_name = x_name
        self.span = float(span)
        self.degree = int(degree)
        self.pars = {"span": self.span}
        self.fitted_values = _loess_values(self.x, self.y, self.x, self.span, self.degree, limit=False)
        self.residuals = self.y - self.fitted_values

    def predict(self, newdata):
        if isinstance(newdata, dict):
            grid = np.asarray(newdata[self.x_name], dtype=float).reshape(-1)
        else:
            grid = np.asarray(newdata, dtype=float).reshape(-1)
        return _loess_values(self.x, self.y, grid, self.span, self.degree, limit=True)


class LoessSimpleBoot:
    def __init__(self, method, boot_list, orig, new_xpts, R):
        self.method = method
        self.boot_list = boot_list
        self.orig_loess = orig
        self.new_xpts = new_xpts
        self.R = int(R)
        self.classes = ("loess.simpleboot",)


def loess(formula, data, span=0.75, degree=2):
    """One-predictor loess. ``formula`` is ``response ~ predictor``."""
    text = formula.replace(" ", "")
    left, right = text.split("~", 1)
    y = np.asarray(data[left], dtype=float).reshape(-1)
    x = np.asarray(data[right], dtype=float).reshape(-1)
    mask = np.isfinite(y) & np.isfinite(x)
    return LoessFit(y[mask], x[mask], left, right, span=span, degree=degree)


def _local(x, y, x0, span, degree):
    """One direct local fit, with the same singular-value cutoff as ``ehg127``."""
    n = int(x.size)
    nf = min(n, int(math.floor(n * span + 1e-5)))
    if nf <= degree:
        raise ValueError("span is too small")
    dist = (x - x0) ** 2
    order = np.argsort(dist, kind="mergesort")
    rho = float(dist[order[nf - 1]]) * max(1.0, span)
    if rho <= 0.0:
        return float(y[order[0]])
    chosen = order[:nf]
    ratio = np.sqrt(dist[chosen] / rho)
    inside = ratio < 1.0
    base = np.zeros(nf)
    base[inside] = (1.0 - ratio[inside] ** 3) ** 3
    w = np.sqrt(np.maximum(base, 0.0))
    mask = w > 0.0
    center = x[chosen][mask] - x0
    response = y[chosen][mask]
    weight = w[mask]
    columns = [weight]
    if degree >= 1:
        columns.append(weight * center)
    if degree >= 2:
        columns.append(weight * center ** 2)
    design = np.column_stack(columns)
    scales = np.sqrt(np.sum(design ** 2, axis=0))
    scales = np.where(scales > 0.0, scales, 1.0)
    balanced = design / scales
    target = weight * response
    u, sigma, vt = np.linalg.svd(balanced, full_matrices=False)
    tol = float(sigma[0]) * 100.0 * np.finfo(float).eps if sigma.size else 0.0
    coef = np.zeros(balanced.shape[1])
    for j, value in enumerate(sigma):
        if value > tol:
            coef += (float(np.dot(u[:, j], target)) / value) * vt[j]
    coef = coef / scales
    return float(coef[0])


def _loess_values(x, y, grid, span, degree, limit=False):
    points = np.asarray(grid, dtype=float).reshape(-1)
    low = float(np.min(x))
    high = float(np.max(x))
    out = np.empty(points.size, dtype=float)
    for i, point in enumerate(points):
        if limit and (point < low or point > high):
            out[i] = np.nan
        else:
            out[i] = _local(x, y, float(point), span, degree)
    return out


def _lo_boot_resample(fit, R, rows, new_xpts, weights):
    y_name = fit.y_name
    x_name = fit.x_name
    nobs = int(fit.y.size)
    boot_list = []
    for _ in range(int(R)):
        if rows:
            chosen = np.asarray(sample_indices(nobs, nobs, weights), dtype=int) - 1
            y = fit.y[chosen]
            x = fit.x[chosen]
        else:
            residual = fit.y - fit.fitted_values
            drawn = np.asarray(sample_replace(residual, nobs, weights), dtype=float)
            # The source adds the resampled residual to the predictor.
            y = fit.x + drawn
            x = fit.x.copy()
        refit = LoessFit(y, x, y_name, x_name, span=fit.span, degree=fit.degree)
        boot_list.append(
            {
                "rss": float(np.sum(refit.residuals ** 2)),
                "fitted": np.asarray(refit.predict(new_xpts), dtype=float),
            }
        )
    return boot_list


def loess_boot(lo_object, R, rows=True, new_xpts=None, ngrid=100, weights=None):
    """Bootstrap a loess fit by resampling rows or residuals."""
    if new_xpts is None:
        grid = np.linspace(float(np.min(lo_object.x)), float(np.max(lo_object.x)), int(ngrid))
        new_xpts = {lo_object.x_name: grid}
    if weights is None:
        weights = np.ones(lo_object.x.size)
    boot_list = _lo_boot_resample(lo_object, R, rows, new_xpts, weights)
    return LoessSimpleBoot("rows" if rows else "residuals", boot_list, lo_object, new_xpts, R)


def fitted_loess_simpleboot(object, **_ignored):
    from simpleboot.linear import samples

    return samples(object, "fitted")


def print_loess_simpleboot(x, **_ignored):
    fit = x.orig_loess
    text = (
        f"BOOTSTRAP OF LOESS (method = {x.method})\n\n"
        "Original Model Fit\n"
        "------------------\n"
        f"loess({fit.y_name} ~ {fit.x_name}, span = {fit.span:g}, n = {fit.x.size})\n"
    )
    print(text, end="")
    return text


def plot_loess_simpleboot(x, add=False, all_lines=False, ax=None, **kwargs):
    """Draw the original smooth and either a two-sd band or every bootstrap curve."""
    from simpleboot.linear import samples

    grid = np.asarray(next(iter(x.new_xpts.values())), dtype=float)
    bmat = samples(x, "fitted")
    n = bmat.shape[1]
    center = np.sum(bmat, axis=1) / n
    std = np.sqrt(np.sum((bmat - center[:, None]) ** 2, axis=1) / (n - 1))
    orig = np.asarray(x.orig_loess.predict(x.new_xpts), dtype=float)
    created = ax is None
    if created:
        _, ax = plt.subplots()
    if not add:
        ax.plot(x.orig_loess.x, x.orig_loess.y, "o", **kwargs)
    ax.plot(grid, orig, color="C0")
    if not all_lines:
        ax.plot(grid, orig + 2 * std, linestyle=":", color="C0")
        ax.plot(grid, orig - 2 * std, linestyle=":", color="C0")
    else:
        for entry in x.boot_list:
            ax.plot(grid, entry["fitted"], color="C0", linewidth=0.6)
    return None
