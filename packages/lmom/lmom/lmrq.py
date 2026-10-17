from __future__ import annotations

import numpy as np

from ._common import _lmr_from_quantile


def lmrq(qfunc, bounds=(0.0, 1.0), symm=False, order=1, ratios=True,
         trim=0, acc=1e-6, subdiv=100, verbose=False, **kwargs):
    """Population L-moments computed from a quantile function."""
    if trim:
        raise NotImplementedError("trimmed population L-moments are not implemented")
    if np.ndim(order) == 0:
        highest = int(order)
    else:
        highest = max(int(v) for v in order)
    lmom = _lmr_from_quantile(qfunc, highest, max(40, int(subdiv)))
    if ratios and highest >= 3:
        lmom[2:] /= lmom[1]
    return lmom if np.ndim(order) == 0 else lmom[np.asarray(order, dtype=int) - 1]
