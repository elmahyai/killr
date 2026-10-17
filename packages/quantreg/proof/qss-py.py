import statistics
import time
import numpy as np
from quantreg.rqss import qss

x = 2 * np.sin(np.arange(1, 13, dtype=float))

def one():
    out = []
    for dorder in (1, 0):
        q = qss(x, lambda_=2, Dorder=dorder)
        out += [q.knots, q.F.toarray().reshape(-1), q.A.toarray().reshape(-1), [q.lambda_]]
    return np.concatenate([np.asarray(v, dtype=float).reshape(-1) for v in out])

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
