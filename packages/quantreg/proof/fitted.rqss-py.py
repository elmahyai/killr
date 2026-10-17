import statistics
import time
import numpy as np
from quantreg.rqss import rqss, fitted_rqss, resid_rqss, log_lik_rqss, aic_rqss, print_rqss

n = 60
i = np.arange(1, n + 1, dtype=float)
x = 2 * np.sin(i)
z = np.cos(0.7 * i)
y = np.sin(x) + 0.5 * z + 0.3 * np.sin(7 * i)
data = {"y": y, "x": x, "z": z}
f1 = rqss("y ~ qss(x, lambda=2) + z", data, tau=0.5)
f2 = rqss("y ~ qss(x, lambda=2) + qss(z, lambda=1, Dorder=0)", data, tau=0.5)

def one():
    return np.concatenate([np.asarray(fitted_rqss(f1), dtype=float), np.asarray(fitted_rqss(f2), dtype=float)])

one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
value = one()
array = np.atleast_1d(np.asarray(value, dtype=float)).reshape(-1)
print(",".join(f"{item:.17g}" for item in array))
print(f"{statistics.median(elapsed):.17g}")

