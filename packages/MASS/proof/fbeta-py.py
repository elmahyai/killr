import statistics
import time
from mass import fbeta


def one():
    return fbeta([0.3, 0.5], 2, 3)

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
