import statistics
import time
from mass import Null


def one():
    import numpy as np
    return Null(np.column_stack([np.ones(4), np.arange(1, 5)])).ravel(order='F')

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
