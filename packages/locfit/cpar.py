"""Local-polynomial coefficient accessor."""

import numpy as np


def cpar(x, *args, **kwargs):
    """Return local-polynomial coefficients with a ``cpar`` style label."""
    lp = kwargs.pop("lp", None)
    if lp is None:
        try:
            from .lp import lp
        except ImportError as exc:
            raise ImportError("cpar requires the locfit lp translation") from exc
    result = np.asarray(lp(x, *args, style="cpar", **kwargs))
    return result
