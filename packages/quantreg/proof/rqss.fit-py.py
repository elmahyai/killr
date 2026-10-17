import statistics
import time
import numpy as np
from quantreg.rqss import rqss_fit

n = 60
i = np.arange(1, n + 1, dtype=float)
x = 2 * np.sin(i)
z = np.cos(0.7 * i)
y = np.sin(x) + 0.5 * z + 0.3 * np.sin(7 * i)
X = np.column_stack([np.ones(n), x, z])

def one():
    f = rqss_fit(X, y, tau=0.3)
    resid = f["resid"]
    rho = np.sum(resid * (0.3 - (resid < 0)))
    return np.concatenate([f["coefficients"], [rho]])

one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
value = one()
array = np.atleast_1d(np.asarray(value, dtype=float)).reshape(-1)
print(','.join(f'{item:.17g}' for item in array))
print(f'{statistics.median(elapsed):.17g}')
