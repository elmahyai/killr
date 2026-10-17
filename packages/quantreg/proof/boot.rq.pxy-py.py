import statistics, time
import numpy as np
from boot.rng import set_seed, sample_int
A = np.loadtxt("/home/ahmed/killr_projects/killr/packages/quantreg/quantreg/data/check_design.txt")
X = A[:, :3]; y = A[:, 3]
def one():
    from quantreg import rq_fit_fnb, boot_rq_pxy
    set_seed(1)
    coef = rq_fit_fnb(X, y, tau=0.5)["coefficients"]
    U = np.asarray(sample_int(40, 80, replace=True)).reshape((40, 2), order="F")
    return boot_rq_pxy(X, y, U, tau=0.5, coef=coef).ravel(order="F")
one()
elapsed = []
for _ in range(20):
    s = time.perf_counter(); one(); elapsed.append((time.perf_counter()-s)*1000)
value = one()
arr = np.atleast_1d(np.asarray(value, dtype=float)).reshape(-1)
print(",".join(f"{v:.17g}" for v in arr))
print(f"{statistics.median(elapsed):.17g}")
