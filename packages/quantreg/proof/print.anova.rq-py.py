import statistics
import time
import numpy as np
from boot.rng import set_seed, sample_int
A = np.loadtxt("/home/ahmed/killr_projects/killr/packages/quantreg/quantreg/data/check_design.txt")
X = A[:, :3]
y = A[:, 3]
data = {"y": y, "x1": X[:, 1], "x2": X[:, 2]}
def one():
    from quantreg import rq, anova_rqs, print_anova_rq
    fit = rq("y ~ x1 + x2", tau=[0.25, 0.5, 0.75], data=data)
    return print_anova_rq(anova_rqs(fit, se="nid", joint=True))
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
