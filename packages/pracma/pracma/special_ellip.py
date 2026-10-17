"""Complete elliptic integrals and Jacobi elliptic functions."""

from __future__ import annotations

import numpy as np

from pracma._util import PracmaError
from pracma.special_common import is_complex_value, is_numeric_value, stop_unless
from pracma.trig import sech


def ellipke(m, tol=np.finfo(float).eps):
    stop_unless(is_numeric_value(m), "is.numeric(m) is not TRUE")
    values = np.ravel(np.asarray(m, dtype=float), order="F")
    if np.any(values < 0) or np.any(values > 1):
        raise PracmaError("Some elements of argument 'm' are out of range.")
    a0 = 1.0
    b0 = np.sqrt(1.0 - values)
    s0 = np.array(values, copy=True)
    step = 0
    limit = 1.0
    a1 = a0
    while limit > tol:
        a1 = (a0 + b0) / 2.0
        b1 = np.sqrt(a0 * b0)
        c1 = (a0 - b0) / 2.0
        step += 1
        w1 = (2.0 ** step) * c1 ** 2
        limit = float(np.max(w1)) if w1.size else 0.0
        s0 = s0 + w1
        a0 = a1
        b0 = b1
    k = np.pi / (2.0 * a1)
    e = k * (1.0 - s0 / 2.0)
    at_one = values == 1
    if np.any(at_one):
        e = np.array(e, copy=True)
        k = np.array(k, copy=True)
        e[at_one] = 1.0
        k[at_one] = np.inf
    return {"k": k, "e": e}


def ellipj(u, m, tol=np.finfo(float).eps):
    stop_unless(is_numeric_value(u), "is.numeric(u) is not TRUE")
    stop_unless(
        is_numeric_value(m) or is_complex_value(m),
        "is.numeric(m) || is.complex(m) is not TRUE",
    )
    uu = np.ravel(np.asarray(u, dtype=float), order="F")
    mm = np.ravel(np.asarray(m, dtype=float), order="F")
    if uu.size == 1 and mm.size != 1:
        uu = np.repeat(uu, mm.size)
    elif mm.size == 1 and uu.size != 1:
        mm = np.repeat(mm, uu.size)
    elif uu.size != mm.size:
        raise PracmaError("Arguments 'u' and 'm' must be of the same length.")
    if np.any(mm < 0) or np.any(mm > 1):
        raise PracmaError("Some elements of argument 'm' are out of range.")
    width = uu.size
    a = [None, np.ones(width)]
    b = [None, np.sqrt(1.0 - mm)]
    cc = [None, np.sqrt(mm)]
    count = np.zeros(width)
    i = 1
    while np.any(np.abs(cc[i]) > tol):
        i += 1
        a.append(0.5 * (a[i - 1] + b[i - 1]))
        b.append(np.sqrt(a[i - 1] * b[i - 1]))
        cc.append(0.5 * (a[i - 1] - b[i - 1]))
        mask = (np.abs(cc[i]) <= tol) & (np.abs(cc[i - 1]) > tol)
        count[mask] = i - 1
    phin = [None] * (i + 1)
    phin[i] = (2.0 ** count) * a[i] * uu
    while i > 1:
        i -= 1
        inds = np.flatnonzero(count >= i)
        phin[i] = np.array(phin[i + 1], copy=True)
        if inds.size:
            angle = phin[i + 1][inds] % (2.0 * np.pi)
            phin[i][inds] = 0.5 * (
                np.arcsin(cc[i + 1][inds] * np.sin(angle) / a[i + 1][inds]) + phin[i + 1][inds]
            )
    sn = np.sin(phin[1] % (2.0 * np.pi))
    cn = np.cos(phin[1] % (2.0 * np.pi))
    dn = np.sqrt(1.0 - mm * sn ** 2)
    at_one = np.flatnonzero(mm == 1)
    if at_one.size:
        sn[at_one] = np.tanh(uu[at_one])
        hyperbolic = np.asarray(sech(uu[at_one]), dtype=float)
        cn[at_one] = hyperbolic
        dn[at_one] = hyperbolic
    dn[mm == 0] = 1.0
    return {"sn": sn, "cn": cn, "dn": dn}
