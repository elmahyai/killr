import statistics
import time
from quantreg import combos

def one():
    return list(combos(5, 2).ravel(order='F')) + list(combos(6, 3).ravel(order='F'))
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
