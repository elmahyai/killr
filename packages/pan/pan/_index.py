"""Index work that the R wrappers pan.R do before the sampler is called.

Shared by pan() and pan_bd(). The R code builds the missing-data patterns from the
0/1 observed matrix (rmat), the pattern of each row (patt), the row order by pattern
(iposn), and the first and last row of each pattern block (pstfin). It also packs the
hyperparameters a, Binv, c and Dinv into one vector (hyp). Index arrays are 1-based,
as in pan.f, and are returned that way.
"""

from collections import Counter

import numpy as np


def as_response(y):
    """y as an ntot x r float matrix; a vector becomes one column, as pan() does."""
    y = np.asarray(y, dtype=float)
    return y.reshape(-1, 1) if y.ndim == 1 else y


def as_pred(pred):
    """pred as an ntot x pcol float matrix; a vector becomes one column."""
    pred = np.asarray(pred, dtype=float)
    return pred.reshape(-1, 1) if pred.ndim == 1 else pred


def missing_patterns(y):
    """Returns patt, rmat, iposn, pstfin and npatt for the response y (ntot x r).

    The strings are built as pan.R builds them: revcpatt has one character per response
    column, the all-missing row is '2' in every column, and the names are sorted with
    rev(table()), so the highest pattern comes first.
    """
    ntot, r = y.shape
    obs = (~np.isnan(y)).astype(np.int64)
    rev = [""] * ntot
    for i in range(r):
        rev = [f"{obs[k, i]}{rev[k]}" for k in range(ntot)]
    nul0 = "0" * r
    nul2 = "2" * r
    rev = [nul2 if s == nul0 else s for s in rev]

    counts = Counter(rev)
    names_desc = sorted(counts, reverse=True)  # rev(table(revcpatt))
    tmp = [counts[n] for n in names_desc]
    npatt = len(names_desc) - (1 if nul2 in counts else 0)

    first = {}
    for k, s in enumerate(rev):
        first.setdefault(s, k)  # !duplicated(revcpatt)
    upatt = list(first)
    urows = [obs[first[s]] for s in upatt]
    order = sorted(range(len(upatt)), key=lambda i: upatt[i], reverse=True)  # rev(order(upatt))
    upatt = [upatt[i] for i in order]
    urows = [urows[i] for i in order]
    if nul2 in upatt:
        upatt, urows = upatt[1:], urows[1:]
    rmat = np.array(urows, dtype=np.int64).reshape(npatt, r)

    patt = np.zeros(ntot, dtype=np.int64)
    for i in range(npatt):
        patt[[k for k, s in enumerate(rev) if s == upatt[i]]] = i + 1

    iposn = np.argsort(patt, kind="stable").astype(np.int64) + 1
    pstfin = np.zeros((npatt, 2), dtype=np.int64)
    if (patt == 0).any():
        st = tmp[0] + 1
        for i in range(1, npatt + 1):
            pstfin[i - 1] = (st, st + tmp[i] - 1)
            st += tmp[i]
    else:
        st = 1
        for i in range(npatt):
            pstfin[i] = (st, st + tmp[i] - 1)
            st += tmp[i]
    return patt, rmat, iposn, pstfin, npatt


def _matrix(x):
    """prior$Binv or prior$Dinv as a matrix: a scalar becomes a 1 x 1 matrix."""
    x = np.asarray(x, dtype=float)
    return x.reshape(1, 1) if x.size == 1 else x


def kernel_y(y):
    """The response as the kernel takes it: NA becomes -999.99, as pan.R does."""
    return np.where(np.isnan(y), -999.99, y)


def hyp_full(prior, r, q):
    """pan(): a, Binv upper by rows, c, then Dinv (rq x rq) upper by rows."""
    binv = _matrix(prior["Binv"])
    dinv = prior["Dinv"]
    if np.size(dinv) == 1:
        # pan.R sets Dinv to matrix(prior$Binv, 1, 1); the first element of Binv is used.
        dinv = np.array([[np.asarray(prior["Binv"], dtype=float).ravel()[0]]])
    dinv = _matrix(dinv)
    rq = r * q
    h = [float(prior["a"])]
    h += [binv[i, j] for i in range(r) for j in range(i, r)]
    h.append(float(prior["c"]))
    h += [dinv[i, j] for i in range(rq) for j in range(i, rq)]
    return np.array(h, dtype=float)


def hyp_bd(prior, r, q):
    """pan.bd(): a, Binv upper by rows, c (length r), then Dinv (q x q x r) upper by layers."""
    binv = _matrix(prior["Binv"])
    dinv = prior["Dinv"]
    if np.size(dinv) == 1:
        # pan.bd sets Dinv to matrix(prior$Binv, 1, 1), as pan() does.
        dinv = np.array([[np.asarray(prior["Binv"], dtype=float).ravel()[0]]])
    dinv = np.asarray(dinv, dtype=float)
    c = np.asarray(prior["c"], dtype=float).ravel()
    h = [float(prior["a"])]
    h += [binv[i, j] for i in range(r) for j in range(i, r)]
    h += list(c[:r])
    for l in range(r):
        h += [dinv[i, j, l] for i in range(q) for j in range(i, q)]
    return np.array(h, dtype=float)
