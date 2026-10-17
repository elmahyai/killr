"""McKinnon's unit-root critical-value table (``unitrootTable``)."""

from __future__ import annotations

import numpy as np

from urca.qunitroot import _match, qunitroot

_TREND = ("c", "nc", "ct", "ctt")
_STAT = ("t", "n")
_P = (0.010, 0.025, 0.050, 0.100, 0.900, 0.950, 0.975, 0.990)
_P_LABELS = ("0.010", "0.025", "0.050", "0.100", "0.900", "0.950", "0.975", "0.990")
_N_LABELS = (" 25", " 50", "100", "250", "500", "Inf")


class UnitrootTable(np.ndarray):
    """Matrix of critical values with R-style dimnames and ``control`` metadata."""

    def __new__(cls, input_array, rownames, colnames, control):
        obj = np.asarray(input_array).view(cls)
        obj.rownames = list(rownames)
        obj.colnames = list(colnames)
        obj.control = dict(control)
        return obj

    def __array_finalize__(self, obj):
        if obj is None:
            return
        self.rownames = getattr(obj, "rownames", None)
        self.colnames = getattr(obj, "colnames", None)
        self.control = getattr(obj, "control", None)


def unitrootTable(trend="c", statistic="t"):
    """Return McKinnon's finite-sample unit-root critical-value table."""
    trend = _match(trend, _TREND)
    statistic = _match(statistic, _STAT)
    rows = []
    for label in _N_LABELS[:-1]:
        size = int(label.strip())
        rows.append(qunitroot(_P, n=size, trend=trend, statistic=statistic))
    rows.append(qunitroot(_P, trend=trend, statistic=statistic))
    table = np.round(np.vstack(rows), 3)
    control = {"table": "unitroot", "trend": trend, "statistic": statistic}
    return UnitrootTable(table, _N_LABELS, _P_LABELS, control)
