import statistics
import time
from mass import kde2d


def one():
    density = kde2d([1, 1.2, 1.4, 2, 2.2], [3, 3.1, 2.8, 5, 5.2], n=5)
    return density['z'].ravel(order='F')

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
if isinstance(value, str):
    print(value)
else:
    import numpy as np
    flat = np.asarray(value, dtype=float).reshape(-1)
    print("\n".join("%.17g" % item for item in flat))
print("%.17g" % statistics.median(elapsed))
