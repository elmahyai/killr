"""Darken colors in HCL, HLS, or combined space (colorspace 2.1-4 darken)."""

from __future__ import annotations

import numpy as np

from colorspace.lighten import lighten


def darken(col, amount=0.1, space="combined", method="relative", fixup=True):
    """Algorithmically darken colors by lightening with the amount negated.

    R passes ``-1 * amount`` to ``lighten``. The ``method`` and ``fixup``
    arguments are forwarded as R forwards ``...``.
    """
    negated = -1.0 * np.asarray(amount, dtype=np.float64)
    if negated.ndim == 0:
        negated = float(negated)
    return lighten(col, amount=negated, method=method, space=space, fixup=fixup)
