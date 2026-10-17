"""Forward selection for linear regression.

Translated from statmod 1.5.2 ``forward`` in ``R/forward.R``.
"""

from __future__ import annotations

import numpy as np


def _qr_resid(x: np.ndarray, y: np.ndarray) -> np.ndarray:
    q_factor, _r = np.linalg.qr(x, mode="reduced")
    if y.ndim == 1:
        return y - q_factor @ (q_factor.T @ y)
    return y - q_factor @ (q_factor.T @ y)


def forward(y, x, xkept=None, intercept=True, nvar=None):
    """Return column indices of ``x`` in forward selection order."""
    y = np.asarray(y, dtype=float).reshape(-1)
    n = y.size

    x = np.asarray(x, dtype=float)
    if x.ndim == 0:
        x = x.reshape(n, 1)
    elif x.ndim == 1:
        x = x.reshape(n, 1)
    if x.shape[0] != n:
        raise ValueError("nrow of x must match length of y")

    if xkept is not None:
        xkept = np.asarray(xkept, dtype=float)
        if xkept.ndim == 0:
            xkept = xkept.reshape(n, 1)
        elif xkept.ndim == 1:
            xkept = xkept.reshape(n, 1)
        if xkept.shape[0] != n:
            raise ValueError("nrow of xkept must match length of y")

    if intercept:
        if xkept is None:
            xkept = np.ones((n, 1), dtype=float)
        else:
            xkept = np.column_stack([np.ones(n, dtype=float), xkept])

    if xkept is None:
        rank_xkept = 0
    else:
        y = _qr_resid(xkept, y)
        x = _qr_resid(xkept, x)
        rank_xkept = int(np.linalg.matrix_rank(xkept))

    if nvar is None:
        nvar = x.shape[1]
    nvar = int(min(nvar, x.shape[1], n - rank_xkept))
    if nvar <= 0:
        return np.array([], dtype=float)

    orderin = np.zeros(nvar, dtype=int)
    candidates = np.arange(1, x.shape[1] + 1, dtype=int)

    x = np.array(x, dtype=float, copy=True)
    y = np.array(y, dtype=float, copy=True)

    for nin in range(nvar):
        if x.shape[1] == 1:
            orderin[nin] = candidates[0]
            break

        y_norm = np.sqrt(np.sum(y * y))
        y = y / y_norm
        col_norms = np.sqrt(np.sum(x * x, axis=0))
        x = x / col_norms

        b_y_x = x.T @ y
        bestj = int(np.argmax(np.abs(b_y_x)))
        bestx = x[:, bestj]

        orderin[nin] = candidates[bestj]
        keep = np.ones(x.shape[1], dtype=bool)
        keep[bestj] = False
        candidates = candidates[keep]
        x = x[:, keep]

        coef = b_y_x[bestj]
        y = y - coef * bestx
        b_x_x = x.T @ bestx
        x = x - np.outer(bestx, b_x_x)

    return orderin.astype(float)
