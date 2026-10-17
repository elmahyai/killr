import statistics
import time
import numpy as np
from quantreg.auxiliary import knots, rearrange, stepfun
kx = [0.5, 1.2, 1.2, 2.0, 3.1, 3.1, 4.5]
ky = [0.3, 1.0, 0.2, 2.5, 0.9, 1.7, 3.3, 0.4]
f1 = stepfun(kx, ky)
f2 = stepfun(kx, ky, right=True)
grid = [-1, 0.5, 0.9, 1.2, 1.5, 2.0, 2.7, 3.1, 4.0, 4.5, 6]

def one():
    r1 = rearrange(f1)
    r2 = rearrange(f2)
    r3 = rearrange(f1, 1, 4)
    return np.concatenate([knots(r1), r1(grid), knots(r2), r2(grid), knots(r3), r3(grid)])
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
