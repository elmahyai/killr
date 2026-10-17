import statistics
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from quantreg.rqss import rqss  # noqa: E402
from quantreg.rqss_methods import summary_rqss  # noqa: E402

n = 60
i = np.arange(1, n + 1, dtype=float)
x = 2 * np.sin(i)
z = np.cos(0.7 * i)
y = np.sin(x) + 0.5 * z + 0.3 * np.sin(7 * i)
data = {"y": y, "x": x, "z": z}

f1 = rqss("y ~ qss(x, lambda=2) + z", data, tau=0.5)
f2 = rqss("y ~ qss(x, lambda=2) + qss(z, lambda=1, Dorder=0)", data, tau=0.5)
g = rqss("y ~ qss(x, lambda=2) + qss(z, lambda=1)", data, tau=0.5)


def one():
    s1 = summary_rqss(f1)
    s2 = summary_rqss(f2)
    sg = summary_rqss(g, cov=True)
    parts = [
        np.ravel(s1["coef"]), [s1["fidelity"], s1["edf"], s1["n"]],
        np.ravel(s2["coef"]), np.ravel(s2["qsstab"]), [s2["fidelity"], s2["edf"], s2["n"]],
        np.ravel(sg["coef"]), np.ravel(sg["qsstab"]), [sg["fidelity"], sg["edf"], sg["n"]],
        np.ravel(sg["Vcov"]), np.ravel(sg["V"]),
    ]
    parts += [np.ravel(v) for v in sg["Vqss"]]
    return np.concatenate([np.asarray(p, dtype=float).reshape(-1) for p in parts])


one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
value = one()
array = np.atleast_1d(np.asarray(value, dtype=float)).reshape(-1)
# NaN and Inf are written as the same fixed sentinels as the R proof.
array = np.where(np.isnan(array), -9e99, np.where(np.isinf(array), np.where(array > 0, 9e99, -9e98), array))
print(','.join(f'{item:.17g}' for item in array))
print(f'{statistics.median(elapsed):.17g}')
