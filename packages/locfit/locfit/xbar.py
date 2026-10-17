"""Mean evaluation specification: translation of locfit 1.5-9.12 ``xbar``."""

from __future__ import annotations

import numpy as np

from ._common import LfEvs


def xbar():
    """Return the ``lf_evs`` record with type ``"xbar"`` (scalars, as in R)."""
    return LfEvs(type="xbar", xev=0.0, mg=0.0, cut=0.0,
                 ll=np.array([0.0]), ur=np.array([0.0]))


__all__ = ["xbar"]
