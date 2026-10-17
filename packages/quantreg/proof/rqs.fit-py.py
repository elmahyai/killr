import statistics
import time
import numpy as np
A = np.loadtxt("/home/ahmed/killr_projects/killr/packages/quantreg/quantreg/data/check_design.txt")
X = A[:, :3]
y = A[:, 3]
Y = np.column_stack([y, 2 * y - X[:, 1], X[:, 1] + 0.3 * y])
from quantreg.auxiliary import rqs_fit

def one():
    a = rqs_fit(X, Y, tau=0.25)
    b = rqs_fit(X, Y, tau=0.75)
    return np.concatenate([a.reshape(-1), b.reshape(-1)])
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
