"""Shared validation and dispatch for lmom parameter estimators."""

from __future__ import annotations

import numpy as np

import lmom_kernel


def call(kernel_name: str, xmom, minimum: int):
    values = np.asarray(xmom, dtype=float).ravel()
    if values.size < minimum:
        raise ValueError(f"{kernel_name} requires at least {minimum} L-moments")
    result, ifail = getattr(lmom_kernel, kernel_name)(np.ascontiguousarray(values))
    if ifail != 0:
        raise ValueError(f"{kernel_name} failed with ifail={ifail}")
    return np.asarray(result, dtype=float)
