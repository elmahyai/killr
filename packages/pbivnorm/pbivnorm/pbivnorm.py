"""Python wrapper for the :mod:`pbivnorm` Rust kernel.

The R interface treats its arguments as vectors, recycles them to a common
length by default, and replaces infinite limits by the largest finite double
before calling the Fortran routine.  The Rust binding intentionally accepts
only equal-length NumPy vectors, so those R-level operations live here.
"""

from __future__ import annotations

import warnings

import numpy as np

from pbivnorm import pbivnorm as _rust_pbivnorm

if not callable(_rust_pbivnorm):
    _rust_pbivnorm = _rust_pbivnorm.pbivnorm

__all__ = ["pbivnorm"]


def _vector(value: object) -> np.ndarray:
    """Convert an R-like vector input to a flattened float64 NumPy array."""
    return np.asarray(value, dtype=np.float64).reshape(-1)


def pbivnorm(
    x: object,
    y: object | None = None,
    rho: object = 0,
    recycle: bool = True,
) -> np.ndarray:
    """Return bivariate standard-normal lower-tail probabilities.

    ``x``, ``y``, and ``rho`` are recycled to the longest input, matching
    ``pbivnorm(..., recycle = TRUE)`` in R.  A two-column ``x`` matrix is also
    accepted; in that form its columns supply ``x`` and ``y`` and an
    explicitly supplied ``y`` is ignored with a warning.
    """
    x_array = np.asarray(x, dtype=np.float64)
    if x_array.ndim == 2:
        if x_array.shape[1] != 2:
            raise ValueError("'x' must have two columns if specified as a matrix")
        if y is not None:
            warnings.warn(
                "'x' was specified as a matrix, so 'y' will be ignored",
                stacklevel=2,
            )
        x_array, y = x_array[:, 0], x_array[:, 1]
    elif x_array.ndim > 2:
        x_array = x_array.reshape(-1)

    if y is None:
        raise TypeError("missing required argument: 'y'")

    x_array = _vector(x_array)
    y_array = _vector(y)
    rho_array = _vector(rho)
    lengths = (x_array.size, y_array.size, rho_array.size)
    if not lengths or max(lengths) == 0:
        raise ValueError("'x', 'y', and 'rho' must not be empty")
    if np.any(np.abs(rho_array) > 1):
        raise ValueError("'rho' must be a valid correlation (-1 <= rho <= 1)")

    if recycle:
        size = max(lengths)
        x_array = np.resize(x_array, size)
        y_array = np.resize(y_array, size)
        rho_array = np.resize(rho_array, size)
    elif len(set(lengths)) != 1:
        raise ValueError(
            "'x', 'y', and 'rho' must be the same length when recycling is disallowed"
        )

    # This is the exact finite-double substitution used by the R wrapper.
    limit = np.finfo(np.float64).max
    x_array = np.where(x_array == np.inf, limit, x_array)
    x_array = np.where(x_array == -np.inf, -limit, x_array)
    y_array = np.where(y_array == np.inf, limit, y_array)
    y_array = np.where(y_array == -np.inf, -limit, y_array)
    return np.asarray(_rust_pbivnorm(x_array, y_array, rho_array), dtype=np.float64)
