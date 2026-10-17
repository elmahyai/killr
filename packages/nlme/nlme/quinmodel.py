"""Quinidine one-compartment oral model (nlme ``quinModel``)."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np

from onecomp import one_comp_open


def _as_f64_vector(name: str, values: Sequence[float] | np.ndarray) -> np.ndarray:
    arr = np.asarray(values, dtype=np.float64)
    if arr.ndim != 1:
        raise ValueError(f"'{name}' must be a vector")
    return arr


def quinModel(
    Subject: Sequence[float] | np.ndarray,
    time: Sequence[float] | np.ndarray,
    conc: Sequence[float] | np.ndarray,
    dose: Sequence[float] | np.ndarray,
    interval: Sequence[float] | np.ndarray,
    lV: Sequence[float] | np.ndarray,
    lKa: Sequence[float] | np.ndarray,
    lCl: Sequence[float] | np.ndarray,
) -> np.ndarray:
    """Predict quinidine concentrations for the Quinidine model."""
    subject = _as_f64_vector("Subject", Subject)
    tim = _as_f64_vector("time", time)
    con = _as_f64_vector("conc", conc)
    dos = _as_f64_vector("dose", dose)
    inter = _as_f64_vector("interval", interval)
    lv = _as_f64_vector("lV", lV)
    lka = _as_f64_vector("lKa", lKa)
    lcl = _as_f64_vector("lCl", lCl)
    nn = subject.size
    n = (tim.size, con.size, dos.size, inter.size, lv.size, lka.size, lcl.size)
    if any(size != nn for size in n):
        raise ValueError("all arguments must have the same length")
    v = np.exp(lv)
    ka = np.exp(lka)
    ke = np.exp(lcl - lv)
    inmat = np.concatenate((subject, tim, con, dos, inter, v, ka, ke))
    return np.asarray(one_comp_open(inmat, nn), dtype=np.float64)
