import statistics
import time
import numpy as np
from boot.rng import set_seed
A = np.loadtxt("/home/ahmed/killr_projects/killr/packages/quantreg/quantreg/data/check_design.txt")
X = A[:, :3]
y = A[:, 3]
def one():
    from quantreg.boot import boot_rq_mcmb
    set_seed(1)
    return np.asarray(boot_rq_mcmb(X, y, tau=0.5, R=200)).ravel(order='F')
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
