"""Residual variance accessor: translation of locfit 1.5-9.12 ``rv``."""

from __future__ import annotations

import numpy as np

from ._common import field


def rv(fit):
    """Return ``fit$dp["rv"]`` as a float (NaN when absent, as R gives NA)."""
    return float(field(field(fit, "dp"), "rv", np.nan))


__all__ = ["rv"]
