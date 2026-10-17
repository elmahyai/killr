import statistics
import time
from mass import con2tr


def one():
    import numpy as np
    obj = {'x': [1, 2], 'y': [10, 20, 30], 'z': np.array([[1, 3, 5], [2, 4, 6]], float)}
    out = con2tr(obj)
    return out['x'] + out['y'] + out['z']

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
