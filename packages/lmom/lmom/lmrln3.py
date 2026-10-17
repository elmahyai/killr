import numpy as np

from ._common import lmr


def lmrln3(para=(0.0, 0.0, 1.0), nmom: int = 3):
    p = np.asarray(para, dtype=np.float64)
    if p.size != 3 or p[2] <= 0:
        raise ValueError("distribution parameters invalid")
    expmu = np.exp(p[1])
    return lmr("lmr_gno", (p[0] + expmu, expmu * p[2], -p[2]), nmom)
