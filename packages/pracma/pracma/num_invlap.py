"""Fourier-series inversion of a Laplace transform."""

from __future__ import annotations

import math

import numpy as np

from pracma._util import PracmaError
from pracma.elementary import linspace
from pracma.num_helpers import is_r_numeric


def invlap(Fs, t1, t2, nnt, a=6, ns=20, nd=19):
    if not is_r_numeric(t1) or np.asarray(t1).size != 1:
        raise PracmaError("is.numeric(t1) is not TRUE" if not is_r_numeric(t1) else "length(t1) == 1 is not TRUE")
    if not is_r_numeric(t2) or np.asarray(t2).size != 1:
        raise PracmaError("is.numeric(t2) is not TRUE" if not is_r_numeric(t2) else "length(t2) == 1 is not TRUE")
    if not is_r_numeric(nnt) or np.asarray(nnt).size != 1:
        raise PracmaError("is.numeric(nnt) is not TRUE" if not is_r_numeric(nnt) else "length(nnt) == 1 is not TRUE")
    count = int(np.asarray(nnt).reshape(-1)[0])
    times = np.asarray(linspace(t1, t2, count), dtype=float)
    if float(np.asarray(t1).reshape(-1)[0]) == 0:
        times = times[1:]
        count = count - 1
    terms = int(ns) + 1 + int(nd)
    alfa = np.zeros(terms, dtype=complex)
    beta = np.zeros(terms, dtype=complex)
    for n in range(1, terms + 1):
        alfa[n - 1] = a + (n - 1) * math.pi * 1j
        beta[n - 1] = -math.exp(a) * ((-1) ** n)
    index = np.arange(1, int(nd) + 1)
    pieces = np.array([
        math.gamma(nd + 1) / math.gamma(nd + 2 - n) / math.gamma(n) for n in index
    ])
    bdif = np.cumsum(pieces)[::-1] / 2 ** int(nd)
    beta[0] = beta[0] / 2
    start = int(ns) + 1
    beta[start:start + int(nd)] = beta[start:start + int(nd)] * bdif
    ft = np.zeros(count)
    for kt, tt in enumerate(times):
        s = alfa / tt
        bt = beta / tt
        ft[kt] = float(np.sum(np.real(bt * np.asarray(Fs(s), dtype=complex))))
    return {"x": times, "y": ft}
