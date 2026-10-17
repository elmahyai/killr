"""Numerical gradient, Hessian, and Jacobian matrices.

These follow rootSolve's forward and centered differences. The Hessian
asks gradient for the reference value with gradient's own defaults, and
passes ``centered`` only to the perturbed calls. It does not pass its
own ``pert``.
"""

import numpy as np

from rootSolve._vec import Matrix, as_vector, column_major, perturb, unlist


def _call_values(function, argument, kwargs):
    try:
        values, names = unlist(function(argument, **kwargs))
    except TypeError as exc:
        raise ValueError("function value should be numeric") from exc
    if names is not None and any(name is None for name in names):
        names = None
    return values, names


def _difference_names(values, names, step_name):
    if names:
        return names
    if len(values) == 1 and step_name:
        return [step_name]
    return None


def gradient(f, x, centered=False, pert=1e-8, **kwargs):
    """Gradient matrix of ``f`` at ``x``.

    A forward difference is the default. ``centered=True`` uses the
    average of the forward and backward differences. ``pert`` is the
    perturbation factor in ``max(abs(x) * pert, pert)``.
    """
    point = as_vector(x, "x")
    reference, _ = _call_values(f, point.copy(), kwargs)
    count_x = len(point)
    count_f = len(reference)
    steps = perturb(point, pert)
    columns = np.zeros((count_f, count_x))
    row_names = None
    for index in range(count_x):
        trial = point.copy()
        trial[index] = trial.values[index] + steps.values[index]
        forward, forward_names = _call_values(f, trial, kwargs)
        delta = [
            (forward[row] - reference[row]) / steps.values[index]
            for row in range(count_f)
        ]
        if centered:
            trial = point.copy()
            trial[index] = trial.values[index] - steps.values[index]
            backward, _ = _call_values(f, trial, kwargs)
            delta = [
                (delta[row] - (backward[row] - reference[row]) / steps.values[index]) / 2
                for row in range(count_f)
            ]
        columns[:, index] = delta
        step_name = steps.names[index] if steps.names else None
        row_names = _difference_names(delta, forward_names, step_name)
    return Matrix(columns, rownames=row_names, colnames=point.names)


def hessian(f, x, centered=False, pert=1e-8, **kwargs):
    """Hessian of ``f`` by differencing its gradient.

    The reference gradient uses gradient's defaults. Each perturbed
    gradient receives ``centered`` and does not receive ``pert``.
    A gradient matrix is written into each column in column-major order.
    """
    point = as_vector(x, "x")
    reference = gradient(f, point.copy(), **kwargs)
    count_x = len(point)
    flat = column_major(reference.data)
    steps = perturb(point, pert)
    columns = np.zeros((flat.size, count_x))
    for index in range(count_x):
        trial = point.copy()
        trial[index] = trial.values[index] + steps.values[index]
        forward = gradient(f, trial, centered=centered, **kwargs)
        delta = (column_major(forward.data) - flat) / steps.values[index]
        if centered:
            trial = point.copy()
            trial[index] = trial.values[index] - steps.values[index]
            backward = gradient(f, trial, centered=centered, **kwargs)
            delta = (
                delta - (column_major(backward.data) - flat) / steps.values[index]
            ) / 2
        columns[:, index] = delta
    return Matrix(columns, colnames=point.names)


def _model_rates(func, time, y, parms, kwargs, count):
    raw = func(time, y, parms, **kwargs)
    try:
        values, _ = unlist(raw)
    except TypeError as exc:
        raise ValueError("dy-values should either be NULL or numeric") from exc
    if len(values) < count:
        values = values + [float("nan")] * (count - len(values))
    return values[:count]


def jacobian_full(y, func, dy=None, time=0, parms=None, pert=1e-8, **kwargs):
    """Full square Jacobian of an ODE rate function.

    ``func(time, y, parms)`` returns the rates, or a list whose first
    element is the rates. Only the first ``length(y)`` values are kept.
    """
    state = as_vector(y, "y")
    count = len(state)
    if dy is None:
        reference = _model_rates(func, time, state.copy(), parms, kwargs, count)
    else:
        try:
            reference, _ = unlist(dy)
        except TypeError as exc:
            raise ValueError("dy-values should either be NULL or numeric") from exc
        if len(reference) != count:
            raise ValueError("function should return at least one value for each y")
    steps = perturb(state, pert)
    columns = np.zeros((count, count))
    for index in range(count):
        trial = state.copy()
        trial[index] = trial.values[index] + steps.values[index]
        rates = _model_rates(func, time, trial, parms, kwargs, count)
        columns[:, index] = [
            (rates[row] - reference[row]) / steps.values[index] for row in range(count)
        ]
    return Matrix(columns, colnames=state.names)


def jacobian_band(y, func, bandup=1, banddown=1, dy=None, time=0, parms=None, pert=1e-8, **kwargs):
    """Banded Jacobian, stored with ``bandup + banddown + 1`` rows.

    Several states are perturbed together, one for each band diagonal.
    ``seq`` with a start past the last state raises the same error R's
    ``seq`` raises.
    """
    state = as_vector(y, "y")
    count = len(state)
    if dy is None:
        reference = _model_rates(func, time, state.copy(), parms, kwargs, count)
    else:
        try:
            reference, _ = unlist(dy)
        except TypeError as exc:
            raise ValueError("dy-values should either be NULL or numeric") from exc
        if len(reference) != count:
            raise ValueError("function should return at least one value for each y")
    nband = bandup + banddown + 1
    columns = np.zeros((nband, count))
    steps = perturb(state, pert)
    for start in range(1, nband + 1):
        if start > count and nband > 0:
            raise ValueError("wrong sign in 'by' argument")
        chosen = list(range(start - 1, count, nband))
        trial = state.copy()
        for index in chosen:
            trial[index] = trial.values[index] + steps.values[index]
        rates = _model_rates(func, time, trial, parms, kwargs, count)
        for index in chosen:
            first = max(index - bandup, 0)
            last = min(index + banddown, count - 1)
            for row in range(first, last + 1):
                slot = row - index + bandup
                columns[slot, index] = (rates[row] - reference[row]) / steps.values[index]
    return Matrix(columns, colnames=state.names)
