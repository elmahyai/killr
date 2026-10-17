"""Vector recycling used by the extraDistr C++ loops."""

import math
import warnings

import numpy as np


def as_vec(value):
    if isinstance(value, (str, bytes)):
        raise TypeError("numeric argument expected")
    if np.isscalar(value):
        return np.asarray([value], dtype=float)
    return np.atleast_1d(np.asarray(value, dtype=float)).reshape(-1)


def first_flag(value, default=False):
    if isinstance(value, (list, tuple, np.ndarray)):
        if len(value) == 0:
            return default
        value = value[0]
    return bool(value)


def sample_size(n):
    if isinstance(n, (list, tuple, np.ndarray)):
        return len(n)
    return int(n)


def _columns(cols):
    arrays = [as_vec(col) for col in cols]
    if any(len(array) == 0 for array in arrays):
        return 0, arrays
    return max(len(array) for array in arrays), arrays


def _at(array, index):
    return float(array[index % len(array)])


def _warn(message, thrown):
    if thrown[0]:
        warnings.warn(message, stacklevel=3)
        thrown[0] = False


def density(log, function, *cols):
    """function(*scalars, thrown) returns the log-density."""
    n, arrays = _columns(cols)
    if n == 0:
        return np.asarray([], dtype=float)
    thrown = [False]
    out = np.empty(n, dtype=float)
    use_log = first_flag(log)
    for i in range(n):
        value = function(*(_at(array, i) for array in arrays), thrown)
        out[i] = value if use_log else math.exp(value)
    _warn("NaNs produced", thrown)
    return out


def probability(lower_tail, log_p, function, *cols):
    """function(*scalars, thrown) returns F(x) on the probability scale."""
    n, arrays = _columns(cols)
    if n == 0:
        return np.asarray([], dtype=float)
    thrown = [False]
    out = np.empty(n, dtype=float)
    lower = first_flag(lower_tail, True)
    logged = first_flag(log_p)
    for i in range(n):
        value = function(*(_at(array, i) for array in arrays), thrown)
        if not lower:
            value = 1.0 - value
        out[i] = math.log(value) if logged else value
    _warn("NaNs produced", thrown)
    return out


def quantile(lower_tail, log_p, function, p, *cols):
    """function(p, *scalars, thrown) returns the quantile. p is exp'd and flipped first."""
    n, arrays = _columns((p, *cols))
    if n == 0:
        return np.asarray([], dtype=float)
    thrown = [False]
    out = np.empty(n, dtype=float)
    lower = first_flag(lower_tail, True)
    logged = first_flag(log_p)
    p_array = arrays[0]
    rest = arrays[1:]
    for i in range(n):
        prob = _at(p_array, i)
        if logged:
            prob = math.exp(prob)
        if not lower:
            prob = 1.0 - prob
        out[i] = function(prob, *(_at(array, i) for array in rest), thrown)
    _warn("NaNs produced", thrown)
    return out


def generate(n, function, *cols):
    """function(*scalars, thrown) returns one draw or nan."""
    count = sample_size(n)
    if count < 0:
        raise ValueError("invalid arguments")
    n_cols, arrays = _columns(cols) if cols else (1, [])
    out = np.empty(count, dtype=float)
    if cols and n_cols == 0:
        warnings.warn("NAs produced", stacklevel=2)
        out.fill(np.nan)
        return out
    thrown = [False]
    for i in range(count):
        args = tuple(_at(array, i) for array in arrays)
        out[i] = function(*args, thrown)
    _warn("NAs produced", thrown)
    return out
