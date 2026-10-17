import statistics
import time
from quantreg import q489
x = [3, 1, 4, 1, 5, 9, 2, 6]

def one():
    return [q489(x, 0.5), q489(x, 0.25)]
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
