"""Signed area and zeros of a piecewise linear graph."""

from __future__ import annotations

import numpy as np


def piecewise(x, y, abs=False):
    abscissa = np.asarray(x, dtype=float).reshape(-1)
    ordinate = np.asarray(y, dtype=float).reshape(-1)
    areas = [0.0]
    zeros = [float(abscissa[0])] if ordinate[0] == 0 else []
    for i in range(1, abscissa.size):
        if ordinate[i] * ordinate[i - 1] >= 0:
            if ordinate[i] == 0:
                zeros.append(float(abscissa[i]))
            areas.append((ordinate[i] + ordinate[i - 1]) * (abscissa[i] - abscissa[i - 1]) / 2.0)
        else:
            crossing = (abscissa[i - 1] * ordinate[i] - abscissa[i] * ordinate[i - 1]) / (ordinate[i] - ordinate[i - 1])
            zeros.append(float(crossing))
            areas.append(ordinate[i - 1] * (crossing - abscissa[i - 1]) / 2.0)
            areas.append(ordinate[i] * (abscissa[i] - crossing) / 2.0)
    total = float(np.sum(np.abs(areas) if abs else areas))
    return {"area": total, "zeros": None if not zeros else np.array(zeros, dtype=float)}
