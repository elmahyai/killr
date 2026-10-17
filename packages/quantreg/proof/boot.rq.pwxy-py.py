import statistics
import time
import numpy as np
from boot.rng import set_seed
A = np.loadtxt("/home/ahmed/killr_projects/killr/packages/quantreg/quantreg/data/check_design.txt")
X = A[:, :3]
y = A[:, 3]
def one():
    from quantreg import rq_fit_fnb
    from quantreg.boot import boot_rq_pwxy
    set_seed(1)
    coef = rq_fit_fnb(X, y, tau=0.5)["coefficients"]
    f = boot_rq_pwxy(X, y, tau=0.5, coef=coef, R=200)
    return np.concatenate([
        np.asarray(f['B']).ravel(order='F'),
        np.asarray(f['nit']).ravel(order='F'),
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
