import statistics
import time
import numpy as np
from boot.rng import set_seed, unif
from quantreg.boot import boot_rq_pwy

A = np.loadtxt("/home/ahmed/killr_projects/killr/packages/quantreg/quantreg/data/check_design.txt")
X = A[:, :3]
y = A[:, 3]
# Fixed inputs, built once and not timed: 200 replicates of the weighted design t(X) %*% ((U < 0.5) - 0.5).
set_seed(1)
n = len(y)
U = np.array([unif() for _ in range(n * 200)]).reshape((n, 200), order="F")
W = X.T @ ((U < 0.5) - 0.5)


def one():
    return np.asarray(boot_rq_pwy(W, X, y, tau=0.5)).ravel(order="F")


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
