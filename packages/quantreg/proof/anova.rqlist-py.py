import statistics
import time
import numpy as np
from boot.rng import set_seed, sample_int
A = np.loadtxt("/home/ahmed/killr_projects/killr/packages/quantreg/quantreg/data/check_design.txt")
X = A[:, :3]
y = A[:, 3]
data = {"y": y, "x1": X[:, 1], "x2": X[:, 2]}
def one():
    from quantreg import rq, anova_rqlist, print_anova_rq
    full = rq("y ~ x1 + x2", tau=0.5, data=data)
    slope = rq("y ~ x1", tau=0.5, data=data)
    intercept = rq("y ~ 1", tau=0.5, data=data)
    a = print_anova_rq(anova_rqlist([full, slope, intercept], test="Wald", se="nid"))
    b = print_anova_rq(anova_rqlist([full, slope], test="rank"))
    return np.concatenate([a, b])
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
