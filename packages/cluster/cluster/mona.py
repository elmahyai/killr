"""Monothetic analysis of binary data, from ``src/mona.c``."""

from __future__ import annotations

import math

import numpy as np


def _as_binary(x):
    data = np.asarray(x, dtype=float)
    if data.ndim != 2:
        raise ValueError("x must be a matrix or data frame.")
    n, p = data.shape
    if p < 2:
        raise ValueError("mona() needs at least p >= 2 variables (in current implementation)")
    coded = np.empty((n, p), dtype=int)
    for column in range(p):
        raw = data[:, column]
        present = sorted({float(v) for v in raw if not math.isnan(float(v))})
        if len(present) != 2:
            raise ValueError(
                "All variables must be binary (e.g., a factor with 2 levels, both present)."
            )
        mapping = {present[0]: 0, present[1]: 1}
        for row, value in enumerate(raw):
            coded[row, column] = 2 if math.isnan(float(value)) else mapping[float(value)]
    return coded


def mona(x):
    """Divisive clustering of binary variables. ``variable`` and ``step`` drop the leading slot."""
    data = _as_binary(x)
    n, p = data.shape
    ner = [0] * (n + 1)
    kwan = [0] * (n + 1)
    nban = [0] * (n + 1)
    lava = [0] * (n + 1)
    jlack = [0] * (p + 1)
    nhalf = (n + 1) // 2

    def get(i, j):
        return int(data[i - 1, j - 1])

    def put(i, j, value):
        data[i - 1, j - 1] = value

    has_na = False
    for l in range(1, n + 1):
        missing = sum(get(l, j) > 1 for j in range(1, p + 1))
        if missing == p:
            raise ValueError("No clustering performed, an object was found with all values missing.")
        if missing:
            has_na = True
            break
    if has_na:
        lack = 0
        for j in range(1, p + 1):
            j0 = sum(get(l, j) == 0 for l in range(1, n + 1))
            j1 = sum(get(l, j) == 1 for l in range(1, n + 1))
            jlack[j] = n - j0 - j1
            if jlack[j] != 0:
                lack += 1
            if jlack[j] >= nhalf:
                raise ValueError(
                    "No clustering performed, found variable with more than half values missing."
                )
            if j0 == 0 or j1 == 0:
                raise ValueError(
                    "No clustering performed, a variable was found with all non missing values identical."
                )
        if lack == p:
            raise ValueError("No clustering performed, all variables have at least one missing value.")
        for j in range(1, p + 1):
            if jlack[j] == 0:
                continue
            lama = -1
            syn = True
            jma = -1
            for ja in range(1, p + 1):
                if jlack[ja] != 0:
                    continue
                a = b = c = d = 0
                for k in range(1, n + 1):
                    if get(k, j) != 1:
                        if get(k, ja) == 0:
                            a += 1
                        elif get(k, ja) == 1:
                            b += 1
                    else:
                        if get(k, ja) == 0:
                            c += 1
                        elif get(k, ja) == 1:
                            d += 1
                kal = a * d - b * c
                kalf = abs(kal)
                if kalf >= lama:
                    lama = kalf
                    jma = ja
                    if kal < 0:
                        syn = False
            for k in range(1, n + 1):
                if get(k, j) > 1:
                    if syn:
                        put(k, j, get(k, jma))
                    elif get(k, jma) == 1:
                        put(k, j, 0)
                    elif get(k, jma) == 0:
                        put(k, j, 1)

    for k in range(1, n + 1):
        ner[k] = k
    npass = 1
    kwan[1] = n
    nclu = 1
    ka = 1
    label = "L310"
    while label != "done":
        if label == "L500":
            npass += 1
            label = "done"
            for ka in range(1, n + 1):
                if kwan[ka] >= 2:
                    label = "L310"
                    break
            continue
        if label == "L410":
            ka += abs(kwan[ka])
            if ka > n:
                label = "L500"
                continue
            if kwan[ka] < 2:
                continue
            label = "L310"
            continue
        kb = ka + kwan[ka] - 1
        lama = -1
        jnat = p
        jma = jtel = jtelz = -1
        for j in range(1, p + 1):
            eligible = nclu == 1
            if not eligible:
                j0 = j1 = 0
                for k in range(ka, kb + 1):
                    value = get(ner[k], j)
                    if value == 0:
                        j0 += 1
                    elif value == 1:
                        j1 += 1
                eligible = j1 != 0 and j0 != 0
            if not eligible:
                continue
            jnat -= 1
            lams = 0
            a = b = c = d = 0
            for jb in range(1, p + 1):
                if jb == j:
                    continue
                a = b = c = d = 0
                for k in range(ka, kb + 1):
                    n_k = ner[k]
                    if get(n_k, j) == 0:
                        if get(n_k, jb) == 0:
                            a += 1
                        elif get(n_k, jb) == 1:
                            b += 1
                    else:
                        if get(n_k, jb) == 0:
                            c += 1
                        elif get(n_k, jb) == 1:
                            d += 1
                lams += abs(a * d - b * c)
            if lama < lams:
                lama = lams
                jtel = c + d
                jtelz = a + b
                jma = j
        if jnat < p:
            nel = ner[ka]
            if get(nel, jma) == 1:
                nzf = 0
                jtel2 = jtel
            else:
                nzf = 1
                jtel2 = jtelz
            jres = kb - ka + 1 - jtel2
            km = ka + jtel2
            k = ka
            n_b = 0
            while k < km:
                n_k = ner[k]
                if get(n_k, jma) == nzf:
                    c = 0
                    for b in range(k, kb + 1):
                        n_b = ner[b]
                        if get(n_b, jma) != nzf:
                            c = b - 1
                            break
                    for a in range(k, c + 1):
                        d = c + k - a
                        ner[d + 1] = ner[d]
                    ner[k] = n_b
                    continue
                k += 1
            nclu += 1
            nban[km] = npass
            kwan[ka] = jtel2
            kwan[km] = jres
            lava[km] = jma
            ka += kwan[ka]
        else:
            kwan[ka] = -kwan[ka]
        if kb == n:
            label = "L500"
        else:
            label = "L410"
    return {
        "data": data.astype(int).tolist(),
        "order": ner[1:],
        "variable": lava[2:],
        "step": nban[2:],
    }
