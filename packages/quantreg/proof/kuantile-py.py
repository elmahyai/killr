import statistics
import time
import numpy as np
from quantreg import kuantile
xd = np.sin(np.arange(1, 93)) * 10 + np.arange(1, 93) / 7

def one():
    x = [3, 1, 4, 1, 5, 9, 2, 6]
    a = kuantile(x, [0.25, 0.5, 0.75])['y']
    b = kuantile(x, [0.2, 0.8], type=5)['y']
    d1 = kuantile(xd, np.arange(1, 100) / 100)['y']
    d2 = kuantile(xd, np.arange(5, 97) / 100)['y']
    d3 = kuantile(xd, np.arange(1, 93) / 93)['y']
    return np.concatenate([a, b, d1, d2, d3])
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
