"""Multiple correspondence analysis."""

import numpy as np


def mjca(obj, nd=2, lambda_="adjusted", supcol=None, subsetcat=None,
         ps=":", maxit=50, epsilon=1e-4, reti=False, **kwargs):
    lambda_ = kwargs.pop("lambda", lambda_)
    data = np.asarray(obj)
    if data.ndim != 2:
        raise ValueError("obj must be a two-dimensional response-pattern matrix")
    levels = [list(dict.fromkeys(data[:, j].tolist())) for j in range(data.shape[1])]
    z = np.zeros((len(data), sum(map(len, levels))))
    offset = 0
    for j, lev in enumerate(levels):
        for i, value in enumerate(data[:, j]):
            z[i, offset + lev.index(value)] = 1
        offset += len(lev)
    b = z.T @ z
    cm = b.sum(axis=0) / b.sum()
    s = (b / b.sum() - np.outer(cm, cm)) / np.sqrt(np.outer(cm, cm))
    vals, vecs = np.linalg.eigh(s)
    order = np.argsort(vals)[::-1]
    vals, vecs = vals[order], vecs[:, order]
    q = data.shape[1]
    maxdim = max(0, z.shape[1] - q)
    vals = np.maximum(vals[:maxdim], 0)
    if lambda_ == "indicator":
        eig = vals
        scale = np.sqrt(eig)
    elif lambda_ == "Burt":
        eig = vals ** 2
        scale = eig
    elif lambda_ in ("adjusted", "JCA"):
        eig = (q / (q - 1)) ** 2 * (np.sqrt(vals) - 1 / q) ** 2
        eig = eig[np.sqrt(vals) >= 1 / q]
        scale = np.sqrt(eig)
    else:
        raise ValueError("invalid lambda")
    # R retains the full available coordinate matrices for indicator/Burt
    # solutions; ``nd`` controls the requested JCA solution.
    nout = len(eig) if lambda_ in ("indicator", "Burt") else min(int(nd), len(eig))
    colcoord = vecs[:, :nout] / np.sqrt(cm)[:, None]
    rowcoord = (z / q) @ colcoord
    if lambda_ == "Burt":
        rowcoord = rowcoord / eig[:nout]
    elif lambda_ in ("adjusted", "JCA"):
        rowcoord = rowcoord / np.sqrt(eig[:nout])
    else:
        rowcoord = rowcoord / np.sqrt(eig[:nout])
    return {
        "sv": np.sqrt(eig[:nout]), "nd": min(int(nd), len(eig)), "rownames": list(range(len(data))),
        "rowmass": np.full(len(data), 1 / len(data)),
        "rowcoord": rowcoord, "colcoord": colcoord,
        "colmass": cm, "colnames": [
            f"{j}{ps}{value}" for j, lev in enumerate(levels) for value in lev
        ],
        "rowsup": [], "colsup": [], "N": b, "levels": levels,
    }
