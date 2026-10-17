import statistics
import time
import numpy as np
from quantreg.rqss import rqss

n = 60
i = np.arange(1, n + 1, dtype=float)
x = 2 * np.sin(i)
z = np.cos(0.7 * i)
y = -0.4 * x + np.sin(x) + 0.5 * z + 0.3 * np.sin(7 * i)
data = {"y": y, "x": x, "z": z}

def one():
    out = []
    f1 = rqss("y ~ qss(x, constraint='I', lambda=2) + z", data, tau=0.5)
    out.append(f1.coef)
    out.append([f1.objective])
    f2 = rqss("y ~ qss(x, constraint='C', lambda=2) + z", data, tau=0.5)
    out.append(f2.coef)
    out.append([f2.objective])
    return np.concatenate([np.asarray(v, dtype=float).reshape(-1) for v in out])

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
