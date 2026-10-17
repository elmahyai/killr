"""Shared checks for the pracma special-function ports."""

from __future__ import annotations

import numpy as np

from pracma._util import PracmaError, as_1d


def stop_unless(ok, message):
    if not ok:
        raise PracmaError(message)


def is_complex_value(value) -> bool:
    if isinstance(value, (bool, np.bool_)):
        return False
    if isinstance(value, (complex, np.complexfloating)):
        return True
    if isinstance(value, (list, tuple)):
        return any(is_complex_value(item) for item in value)
    if value is None:
        return False
    array = np.asarray(value)
    return array.dtype != object and np.issubdtype(array.dtype, np.complexfloating)


def is_numeric_value(value) -> bool:
    if value is None or isinstance(value, (bool, np.bool_, complex, np.complexfloating)):
        return False
    if isinstance(value, (int, float, np.integer, np.floating)):
        return True
    if isinstance(value, (list, tuple)):
        return all(is_numeric_value(item) or is_complex_value(item) for item in value) and not is_complex_value(value)
    array = np.asarray(value)
    if array.dtype == object or array.dtype == bool:
        return False
    return np.issubdtype(array.dtype, np.number) and not np.issubdtype(array.dtype, np.complexfloating)


def flatten(value, dtype=None):
    """Column-major flatten, matching R's c()."""
    array = np.asarray(value if dtype is None else np.asarray(value))
    if dtype is not None:
        array = np.asarray(array, dtype=dtype)
    return np.ravel(array, order="F")


def real_vector(value):
    """A real vector. Complex input is rejected by the caller before this."""
    if value is None:
        return np.array([], dtype=float)
    return as_1d(value)


def length_of(value) -> int:
    if value is None:
        return 0
    if isinstance(value, (int, float, complex, np.integer, np.floating, np.complexfloating)):
        return 1
    return int(np.asarray(value).size)


def is_na(value) -> bool:
    if isinstance(value, (complex, np.complexfloating)):
        return bool(np.isnan(np.real(value)) or np.isnan(np.imag(value)))
    try:
        return bool(np.isnan(value))
    except TypeError:
        return False


def real_if_closed(values, was_real: bool):
    array = np.asarray(values)
    if was_real and np.all(np.imag(np.asarray(array, dtype=np.complex128)) == 0):
        return np.real(array).astype(float)
    return array
