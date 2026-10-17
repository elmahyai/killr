import statistics
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mclust.cdens_v_vei_vev_vii_vvi_vvv import cdensV

n = 40
p = 3
G = 3
i = np.arange(1, n + 1, dtype=float)
x = np.column_stack([np.sin(0.7 * i), 0.7 * np.cos(1.3 * i) + 0.1 * i / n, np.sin(0.4 * i + 1) - 0.5 * i / n])
x1 = x[:, 0]
mu1 = np.array([-0.4, 0.3, 1.1])
pro = np.array([0.3, 0.45, 0.25])
sig = np.array([0.6, 1.4, 0.9])
pars = {"pro": pro, "mean": mu1, "variance": {"sigmasq": sig}}


def one():
    a = cdensV(x1, logarithm=True, parameters=pars)
    b = cdensV(x1, logarithm=False, parameters=pars)
    return np.concatenate([np.asarray(a).ravel(order="F"), np.asarray(b).ravel(order="F")])


value = one()
elapsed = []
for _ in range(20):
    t0 = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - t0) * 1000)
print("\n".join("%.17g" % v for v in value))
print("%.17g" % statistics.median(elapsed))
