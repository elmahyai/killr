"""lfmarg: R's lfmarg(), the marginal evaluation grid of a fit or of a box.

For a numeric ``xlim`` the dimension is ``length(m)``. For a fit-like mapping
the dimension is ``fit["mi"]["d"]`` and the box is ``fit["box"]``. Each margin
is R's ``seq(xlim[i], xlim[i + d], length.out = m[i])``.
"""

from __future__ import annotations

from collections.abc import Mapping
import math

import numpy as np


def lfmarg(xlim, m=40):
    if isinstance(xlim, Mapping):
        if "box" not in xlim:
            raise NotImplementedError(
                "the fit's bounding box is not returned by crates/locfit")
        d = int(xlim["mi"]["d"])
        box = np.asarray(xlim["box"], dtype=float)
    else:
        box = np.asarray(xlim, dtype=float)
        m = np.atleast_1d(np.asarray(m, dtype=float))
        d = len(m)
    m = np.resize(np.atleast_1d(np.asarray(m, dtype=float)), d)
    return [np.linspace(box[i], box[i + d], math.ceil(m[i])) for i in range(d)]
