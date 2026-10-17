"""Numerically stable logistic inverse-link function."""

from ._common import expit_array


def expit(x):
    result = expit_array(x)
    return float(result) if result.ndim == 0 else result

