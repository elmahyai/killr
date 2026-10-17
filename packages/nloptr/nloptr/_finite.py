"""Central differences and the derivative checker."""

from __future__ import annotations

import math
import sys
import warnings

import numpy as np

_HEPS = sys.float_info.epsilon ** (1.0 / 3.0)
_STEP = math.sqrt(sys.float_info.epsilon)


def _vector(x0, message: str) -> np.ndarray:
    if isinstance(x0, bool) or (
        isinstance(x0, np.ndarray) and np.issubdtype(x0.dtype, np.bool_)
    ):
        raise ValueError(message)
    if isinstance(x0, str):
        raise ValueError(message)
    try:
        values = np.asarray(x0, dtype=float)
    except (TypeError, ValueError) as exc:
        raise ValueError(message) from exc
    if values.ndim == 0:
        values = values.reshape(1)
    if values.ndim != 1:
        values = values.reshape(-1)
    return values


def nl_grad(x0, fn, heps=_HEPS, **kwargs):
    """Central-difference gradient. The step is the same on every coordinate."""
    point = _vector(x0, "Argument 'x0' must be a numeric value.")

    def call(x):
        return fn(x, **kwargs) if kwargs else fn(x)

    probe = call(point)
    if np.size(probe) != 1:
        raise ValueError(
            "Function 'f' must be a scalar function (return a single value)."
        )
    n = len(point)
    gradient = np.zeros(n)
    step = np.zeros(n)
    for i in range(n):
        step[i] = heps
        gradient[i] = (float(np.ravel(call(point + step))[0]) - float(np.ravel(call(point - step))[0])) / (2.0 * heps)
        step[i] = 0.0
    return gradient


def nl_jacobian(x0, fn, heps=_HEPS, **kwargs):
    """Central-difference Jacobian. One column per coordinate."""
    point = _vector(x0, "Argument 'x' must be a non-empty numeric vector.")
    if len(point) == 0:
        raise ValueError("Argument 'x' must be a non-empty numeric vector.")

    def call(x):
        return fn(x, **kwargs) if kwargs else fn(x)

    probe = np.atleast_1d(np.asarray(call(point), dtype=float).reshape(-1))
    jacobian = np.empty((len(probe), len(point)))
    step = np.zeros(len(point))
    for i in range(len(point)):
        step[i] = heps
        forward = np.atleast_1d(np.asarray(call(point + step), dtype=float).reshape(-1))
        backward = np.atleast_1d(np.asarray(call(point - step), dtype=float).reshape(-1))
        jacobian[:, i] = (forward - backward) / (2.0 * heps)
        step[i] = 0.0
    return jacobian


def finite_diff(func, x, indices=None, step_size=_STEP, **kwargs):
    """Forward difference used by the derivative checker."""
    point = np.asarray(x, dtype=float).reshape(-1)
    if indices is None:
        chosen = range(len(point))
    else:
        chosen = [int(i) - 1 for i in indices]
    steps = np.maximum(np.abs(point), 1.0) * step_size
    base = np.atleast_1d(np.asarray(func(point, **kwargs) if kwargs else func(point), dtype=float).reshape(-1))
    columns = []
    for i in chosen:
        moved = point.copy()
        moved[i] = point[i] + steps[i]
        actual = moved[i] - point[i]
        forward = np.atleast_1d(
            np.asarray(func(moved, **kwargs) if kwargs else func(moved), dtype=float).reshape(-1)
        )
        columns.append((forward - base) / actual)
    stacked = np.column_stack(columns) if columns else np.empty((len(base), 0))
    if stacked.shape[0] == 1:
        return stacked.reshape(-1)
    return stacked


def _r_scientific(value: float) -> str:
    if math.isnan(value):
        return "NaN"
    if math.isinf(value):
        return "Inf" if value > 0 else "-Inf"
    return format(float(value), ".6e")


def check_derivatives(
    x,
    func,
    func_grad,
    check_derivatives_tol=1e-4,
    check_derivatives_print="all",
    func_grad_name="grad_f",
    **kwargs,
):
    """Compare an analytic derivative with a forward difference."""
    analytic = np.asarray(func_grad(x, **kwargs) if kwargs else func_grad(x), dtype=float)
    finite = finite_diff(func, x, **kwargs)
    analytic_flat = np.ravel(analytic, order="F")
    finite_flat = np.ravel(np.asarray(finite, dtype=float), order="F")
    relative = np.where(
        finite_flat == 0,
        analytic_flat,
        np.abs((analytic_flat - finite_flat) / finite_flat),
    )
    flagged = relative > check_derivatives_tol
    if check_derivatives_print not in ("all", "errors", "none"):
        warnings.warn(
            f"Value '{check_derivatives_print}' for check_derivatives_print is unknown; "
            "use 'all' (default), 'errors', or 'none'."
        )
        check_derivatives_print = "none"
    print(
        f"Derivative checker results: {int(np.sum(flagged))} error(s) detected.",
        file=sys.stderr,
    )
    if check_derivatives_print == "all":
        _print_rows(func_grad_name, analytic, finite, relative, flagged, None)
    elif check_derivatives_print == "errors" and np.any(flagged):
        _print_rows(func_grad_name, analytic, finite, relative, flagged, flagged)
    return {
        "analytic": analytic if analytic.ndim > 1 else analytic_flat,
        "finite_difference": finite,
        "relative_error": relative.reshape(analytic.shape) if analytic.ndim > 1 else relative,
        "flag_derivative_warning": flagged.reshape(analytic.shape) if analytic.ndim > 1 else flagged,
    }


def _print_rows(name, analytic, finite, relative, flagged, mask):
    analytic_flat = np.ravel(analytic, order="F")
    finite_flat = np.ravel(np.asarray(finite), order="F")
    indices = _indices(analytic)
    lines = []
    for i, index in enumerate(indices):
        if mask is not None and not np.ravel(mask, order="F")[i]:
            continue
        mark = "*" if flagged[i] else " "
        lines.append(
            f"{mark} {name}[{index}] = {_r_scientific(analytic_flat[i])} ~ "
            f"{_r_scientific(finite_flat[i])}   [{_r_scientific(relative[i])}]"
        )
    if lines:
        print("\n" + "\n".join(lines) + "\n", file=sys.stderr)


def _indices(analytic: np.ndarray) -> list[str]:
    if analytic.ndim == 2:
        nrow, ncol = analytic.shape
        row_width = 1 + int(np.sum(nrow > 10 ** np.arange(1, 11)))
        col_width = 1 + int(np.sum(ncol > 10 ** np.arange(1, 11)))
        labels = []
        for col in range(1, ncol + 1):
            for row in range(1, nrow + 1):
                labels.append(f"{row:>{row_width}}, {col:>{col_width}}")
        return labels
    n = analytic.size
    width = 1
    return [f"{i:>{width}}" for i in range(1, n + 1)]
