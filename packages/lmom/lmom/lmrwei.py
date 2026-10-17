import numpy as np

from ._common import lmr


def lmrwei(para=(0.0, 1.0, 1.0), nmom: int = 3):
    p = np.asarray(para, dtype=np.float64)
    if p.size != 3 or p[1] <= 0 or p[2] <= 0:
        raise ValueError("distribution parameters invalid")
    values = lmr("lmr_gev", (0.0, p[1] / p[2], 1.0 / p[2]), nmom)
    values = values.copy()
    values[0] = p[0] + p[1] - values[0]
    if values.size >= 3:
        values[2] = -values[2]
    return values
