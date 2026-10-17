import statistics
import time
import numpy as np
import scipy.sparse as sp
from boot.rng import set_seed, unif
A = np.loadtxt("/home/ahmed/killr_projects/killr/packages/quantreg/quantreg/data/check_design.txt")
X = A[:, :3].copy()
y = A[:, 3]
# Sparse design: the slope entries with |x| < 0.5 are structural zeros; the intercept stays.
slopes = X[:, 1:3]
slopes[np.abs(slopes) < 0.5] = 0.0
X[:, 1:3] = slopes
def one():
    from quantreg.boot import boot_rq_spwy
    set_seed(1)
    a = sp.csr_matrix(X)
    n = len(y)
    U = np.array([unif() for _ in range(n * 200)]).reshape((n, 200), order="F")
    W = np.asarray(a.T @ ((U < 0.5) - 0.5))
    return np.asarray(boot_rq_spwy(W, a, y, tau=0.5)).ravel(order="F")
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
