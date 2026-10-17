import statistics
import time
import numpy as np
A = np.loadtxt("/home/ahmed/killr_projects/killr/packages/quantreg/quantreg/data/check_design.txt")
data = {"y": A[:, 3], "x1": A[:, 1], "x2": A[:, 2]}
from quantreg import rq
fit = rq("y ~ x1 + x2", tau=[0.25, 0.5, 0.75], data=data)
from quantreg import summary_rqs

def one():
    return summary_rqs(fit, se='nid')[0]['coefficients'][:, 1]
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
