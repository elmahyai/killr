import statistics
import time
import numpy as np
from quantreg import bandwidth_rq

def one():
    return np.array([bandwidth_rq(0.5, 100), bandwidth_rq(0.9, 50, hs=False, alpha=0.1)])
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
