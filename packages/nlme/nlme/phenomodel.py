"""Phenobarbital one-compartment IV model (nlme ``phenoModel``)."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np

from onecomp import one_comp_first


def _as_f64_vector(name: str, values: Sequence[float] | np.ndarray) -> np.ndarray:
    arr = np.asarray(values, dtype=np.float64)
    if arr.ndim != 1:
        raise ValueError(f"'{name}' must be a vector")
    return arr


def phenoModel(
    Subject: Sequence[float] | np.ndarray,
    time: Sequence[float] | np.ndarray,
    dose: Sequence[float] | np.ndarray,
    lCl: Sequence[float] | np.ndarray,
    lV: Sequence[float] | np.ndarray,
) -> np.ndarray:
    """Predict phenobarbital concentrations for the Phenobarb model."""
    subject = _as_f64_vector("Subject", Subject)
    tim = _as_f64_vector("time", time)
    dos = _as_f64_vector("dose", dose)
    lcl = _as_f64_vector("lCl", lCl)
    lv = _as_f64_vector("lV", lV)
    nn = subject.size
    if tim.size != nn or dos.size != nn or lcl.size != nn or lv.size != nn:
        raise ValueError("Subject, time, dose, lCl, and lV must have the same length")
    v = np.exp(lv)
    cl = np.exp(lcl)
    inmat = np.concatenate((subject, tim, dos, v, cl))
    return np.asarray(one_comp_first(inmat, nn), dtype=np.float64)
