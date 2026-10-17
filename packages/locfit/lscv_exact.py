"""lscv.exact: R's exact least-squares cross-validation bandwidth criterion.

R calls the C routine slscv (kdecri case 3 with the Gaussian kernel, the exact
density LSCV). The crate's ``slscv`` is that routine. The result is R's
two-element ``c(criterion, degrees of freedom)``.
"""

from __future__ import annotations

import numpy as np

from ._kernel import slscv


def lscv_exact(x, h=0.0):
    alpha = getattr(x, "alpha", None)
    if alpha is not None:
        h = np.asarray(alpha, dtype=float)[1]
    h = float(h)
    if h <= 0:
        raise ValueError("lscv.exact: h must be positive.")
    return slscv(np.asarray(x, dtype=float), h)
