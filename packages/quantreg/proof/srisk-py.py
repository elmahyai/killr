import statistics
import time
X = [[0.02, 0.01, -0.01], [0.03, 0.0, 0.02], [-0.02, 0.04, 0.01], [0.01, -0.01, 0.02]]
from quantreg import srisk
fit = srisk(X, mu=0.01, lambda_=1e6)

def one():
    return list(fit['pihat']) + [fit['muhat'], fit['sigma']]
one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
value = one()
import numpy as np
array = np.atleast_1d(np.asarray(value, dtype=float)).reshape(-1)
print(','.join(f'{item:.17g}' for item in array))
print(f'{statistics.median(elapsed):.17g}')
