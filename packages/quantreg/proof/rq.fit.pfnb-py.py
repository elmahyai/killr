import statistics
import time
import numpy as np
from boot.rng import set_seed
A = np.loadtxt("/home/ahmed/killr_projects/killr/packages/quantreg/quantreg/data/check_design.txt")
X = A[:, :3]
y = A[:, 3]
def one():
    from quantreg.interior import rq_fit_pfnb
    set_seed(1)
    f = rq_fit_pfnb(X, y, tau=0.5)
    return np.concatenate([
        np.asarray(f['coefficients']).ravel(order='F'),
        np.asarray(f['dual']).ravel(order='F'),
        np.asarray(f['nit']).ravel(order='F'),
        np.asarray(f['flag']).ravel(order='F'),
    ])
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
