import statistics
import time
import numpy as np
A = np.loadtxt("/home/ahmed/killr_projects/killr/packages/quantreg/quantreg/data/check_design.txt")
X = A[:, :3]
y = A[:, 3]
data = {"y": y, "x1": X[:, 1], "x2": X[:, 2]}
from quantreg import lprq
lp = lprq([1,2,3,4,5,6,7,8], [1,1,2,2,3,4,5,7], h=2, tau=0.5, m=5)

def one():
    return np.concatenate([lp['xx'], lp['fv'], lp['dv']])
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
