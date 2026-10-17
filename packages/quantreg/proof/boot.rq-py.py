import statistics
import time
import numpy as np
from boot.rng import set_seed, sample_int
A = np.loadtxt("/home/ahmed/killr_projects/killr/packages/quantreg/quantreg/data/check_design.txt")
X = A[:, :3]
y = A[:, 3]
data = {"y": y, "x1": X[:, 1], "x2": X[:, 2]}
def one():
    from quantreg import boot_rq
    set_seed(1)
    xy = boot_rq(X, y, tau=0.5, r=3)["B"].ravel(order="F")
    set_seed(1)
    wxy = boot_rq(X, y, tau=0.5, r=2, bsmethod="wxy")["B"].ravel(order="F")
    set_seed(1)
    jack = boot_rq(X, y, tau=0.5, r=2, bsmethod="jack")["B"].ravel(order="F")
    return np.concatenate([xy, wxy, jack])
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
