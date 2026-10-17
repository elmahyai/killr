import statistics
import time
import numpy as np
from quantreg.rqss import qss1

x = 2 * np.sin(np.arange(1, 13, dtype=float))

def one():
    q = qss1(x, lambda_=2)
    F = q.F.toarray()
    A = q.A.toarray()
    return np.concatenate([q.knots, F.reshape(-1), A.reshape(-1), [q.lambda_]])

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
