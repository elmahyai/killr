"""Bootstrap of a linear model fit, and the samples taken from it.

Row resampling draws row indices with ``sample(..., replace=TRUE, prob=)``.
Residual resampling draws the residual vector the same way and adds it to
the original fitted values. The coefficient fit is a least-squares solve.
"""

import math

import numpy as np
from matplotlib import pyplot as plt

from simpleboot.one import r_quantile
from simpleboot.sampling import sample_indices, sample_replace


class LinearModel:
    """Gaussian linear model with an intercept, stored the way ``lm`` stores one."""

    def __init__(self, response, predictors, y_name, x_names, y, x):
        self.y_name = y_name
        self.x_names = list(x_names)
        self.y = np.asarray(y, dtype=float).reshape(-1)
        self.x = np.asarray(x, dtype=float)
        if self.x.ndim == 1:
            self.x = self.x.reshape(-1, 1)
        n = self.y.size
        design = np.column_stack([np.ones(n), self.x])
        coef, _, rank, _ = np.linalg.lstsq(design, self.y, rcond=None)
        self.coef = np.asarray(coef, dtype=float).reshape(-1)
        self.coef_names = ["(Intercept)", *self.x_names]
        self.rank = int(design.shape[1] if rank is None else rank)
        fitted = design @ self.coef
        self.fitted_values = fitted
        self.residuals = self.y - fitted
        self.response = response
        self.predictors = predictors

    def predict(self, newdata):
        columns = [_column(newdata, name) for name in self.x_names]
        n = columns[0].size
        design = np.column_stack([np.ones(n), *columns])
        return design @ self.coef


class LmSimpleBoot:
    def __init__(self, method, boot_list, orig_lm, new_xpts, weights):
        self.method = method
        self.boot_list = boot_list
        self.orig_lm = orig_lm
        self.new_xpts = new_xpts
        self.weights = np.asarray(weights, dtype=float).reshape(-1)
        self.classes = ("lm.simpleboot",)


def _column(frame, name):
    if isinstance(frame, dict):
        return np.asarray(frame[name], dtype=float).reshape(-1)
    return np.asarray(getattr(frame, name), dtype=float).reshape(-1)


def _parse_formula(formula):
    text = formula.replace(" ", "")
    if "~" not in text:
        raise ValueError("formula needs a response and a right-hand side")
    left, right = text.split("~", 1)
    terms = [term for term in right.split("+") if term and term != "1"]
    if not left or not terms:
        raise ValueError("formula needs one response and at least one predictor")
    return left, terms


def lm(formula, data):
    """Fit ``response ~ predictor + ...`` by least squares, dropping incomplete rows."""
    y_name, x_names = _parse_formula(formula)
    y = np.asarray(data[y_name], dtype=float).reshape(-1)
    columns = [np.asarray(data[name], dtype=float).reshape(-1) for name in x_names]
    mask = np.isfinite(y)
    for column in columns:
        mask &= np.isfinite(column)
    y = y[mask]
    x = np.column_stack([column[mask] for column in columns])
    return LinearModel(y_name, x_names, y_name, x_names, y, x)


def _frame_from_model(model):
    frame = {model.y_name: model.y.copy()}
    for i, name in enumerate(model.x_names):
        frame[name] = model.x[:, i].copy()
    return frame


def _refit(model, frame):
    y = np.asarray(frame[model.y_name], dtype=float).reshape(-1)
    x = np.column_stack([np.asarray(frame[name], dtype=float).reshape(-1) for name in model.x_names])
    return LinearModel(model.y_name, model.x_names, model.y_name, model.x_names, y, x)


def _new_xpts(model, ngrid):
    if len(model.x_names) != 1:
        return None
    name = model.x_names[0]
    low = float(np.min(model.x[:, 0]))
    high = float(np.max(model.x[:, 0]))
    grid = np.linspace(low, high, int(ngrid))
    return {name: grid}


def _lm_boot_resample(model, R, rows, new_xpts, weights):
    nobs = int(model.y.size)
    yhat = np.asarray(model.fitted_values, dtype=float)
    boot_list = []
    for _ in range(int(R)):
        if rows:
            chosen = sample_indices(nobs, nobs, weights)
            frame = _frame_from_model(model)
            for key, values in list(frame.items()):
                frame[key] = np.asarray(values, dtype=float)[np.asarray(chosen, dtype=int) - 1]
        else:
            frame = _frame_from_model(model)
            drawn = sample_replace(model.residuals, nobs, weights)
            frame[model.y_name] = yhat + np.asarray(drawn, dtype=float)
        fit = _refit(model, frame)
        rss = float(np.sum(fit.residuals ** 2))
        response = np.asarray(frame[model.y_name], dtype=float)
        syy = float(np.sum(response ** 2))
        entry = {
            "coef": fit.coef.copy(),
            "rss": rss,
            "rsquare": (syy - rss) / syy,
            "rstderr": math.sqrt(rss / (nobs - fit.rank)),
        }
        if new_xpts is not None:
            entry["fitted"] = np.asarray(fit.predict(new_xpts), dtype=float)
        boot_list.append(entry)
    return boot_list


def lm_boot(lm_object, R, rows=True, new_xpts=None, ngrid=100, weights=None):
    """Bootstrap an ``lm`` fit by resampling rows or residuals."""
    if new_xpts is None and len(lm_object.x_names) == 1:
        new_xpts = _new_xpts(lm_object, ngrid)
    nobs = int(lm_object.y.size)
    if weights is None:
        weights = np.ones(nobs)
    boot_list = _lm_boot_resample(lm_object, R, rows, new_xpts, weights)
    return LmSimpleBoot("rows" if rows else "residuals", boot_list, lm_object, new_xpts, weights)


def samples(object, name="fitted"):
    """Stack one field from each bootstrap fit.

    ``coef`` and ``fitted`` come back with the parameter or grid point down
    the rows and the replicate across the columns, matching ``sapply``.
    """
    choices = ("fitted", "coef", "rsquare", "rss")
    if name not in choices:
        matches = [choice for choice in choices if choice.startswith(name)]
        if len(matches) != 1:
            raise ValueError(f"name should be one of {', '.join(choices)}")
        name = matches[0]
    classes = getattr(object, "classes", ())
    if "lm.simpleboot" not in classes and "loess.simpleboot" not in classes:
        raise ValueError("only use with 'lm.simpleboot' or 'loess.simpleboot' object")
    boot_list = object.boot_list
    if name not in boot_list[0]:
        raise ValueError(f"bootstrap model does not have '{name}' values")
    columns = [np.asarray(entry[name], dtype=float).reshape(-1) for entry in boot_list]
    return np.column_stack(columns)


def perc_lm(lm_boot_obj, p):
    """Percentiles of the bootstrapped coefficients, one row of ``samples`` at a time."""
    cmat = samples(lm_boot_obj, "coef")
    levels = np.atleast_1d(np.asarray(p, dtype=float))
    rows = [np.asarray(r_quantile(cmat[i, :], levels), dtype=float).reshape(-1) for i in range(cmat.shape[0])]
    stacked = np.column_stack(rows)
    return np.squeeze(stacked)


def summary_lm_simpleboot(object, **_ignored):
    """Add the bootstrap standard deviation of each coefficient."""
    params = samples(object, "coef")
    n = params.shape[1]
    center = np.sum(params, axis=1) / n
    stdev = np.sqrt(np.sum((params - center[:, None]) ** 2, axis=1) / (n - 1))
    summary = LmSimpleBoot(object.method, object.boot_list, object.orig_lm, object.new_xpts, object.weights)
    summary.classes = ("summary.lm.simpleboot",)
    summary.stdev_params = stdev
    summary.coef_names = list(object.orig_lm.coef_names)
    return summary


def _format_lm(model):
    coefs = "  ".join(f"{name}={value:.6g}" for name, value in zip(model.coef_names, model.coef))
    formula = f"{model.y_name} ~ {' + '.join(model.x_names)}"
    return f"Call:\nlm(formula = {formula})\n\nCoefficients:\n{coefs}\n"


def print_lm_simpleboot(x, **_ignored):
    text = (
        f"BOOTSTRAP OF LINEAR MODEL  (method = {x.method})\n\n"
        "Original Model Fit\n"
        "------------------"
        f"{_format_lm(x.orig_lm)}"
    )
    print(text, end="")
    return text


def print_summary_lm_simpleboot(x, **_ignored):
    print_lm_simpleboot(x)
    print("Bootstrap SD's:")
    labels = getattr(x, "coef_names", [str(i) for i in range(x.stdev_params.size)])
    body = "  ".join(f"{name}={value:.6g}" for name, value in zip(labels, x.stdev_params))
    print(body)
    print()
    return body


def fitted_lm_simpleboot(object, **_ignored):
    return samples(object, "fitted")


def model_frame_lm_simpleboot(formula, **_ignored):
    return _frame_from_model(formula.orig_lm)


def plot_lm_simpleboot(x, add=False, ax=None, **kwargs):
    """Scatter the original fit and draw a band two bootstrap standard deviations out."""
    frame = model_frame_lm_simpleboot(x)
    if len(x.orig_lm.x_names) > 1:
        raise ValueError("cannot plot bootstrap regressions with dimension > 2")
    xpts = x.new_xpts
    bmat = samples(x, "fitted")
    n = bmat.shape[1]
    center = np.sum(bmat, axis=1) / n
    std = np.sqrt(np.sum((bmat - center[:, None]) ** 2, axis=1) / (n - 1))
    orig_pred = np.asarray(x.orig_lm.predict(xpts), dtype=float)
    created = ax is None
    if created:
        _, ax = plt.subplots()
    name = x.orig_lm.x_names[0]
    grid = np.asarray(xpts[name], dtype=float)
    if not add:
        ax.plot(frame[name], frame[x.orig_lm.y_name], "o", **kwargs)
    intercept = float(x.orig_lm.coef[0])
    slope = float(x.orig_lm.coef[1])
    ax.axline((0.0, intercept), slope=slope, color="C0")
    ax.plot(grid, orig_pred + 2 * std, linestyle=":", color="C0")
    ax.plot(grid, orig_pred - 2 * std, linestyle=":", color="C0")
    return None
