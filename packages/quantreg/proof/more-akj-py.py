import statistics
import time
import numpy as np
A = np.loadtxt("/home/ahmed/killr_projects/killr/packages/quantreg/quantreg/data/check_design.txt")
y = A[:, 3]
from quantreg.more import akj

def one():
    a = akj([1, 2, 3, 4, 5], z=[1, 3, 5], h=1)
    b = akj(y)
    return np.concatenate([
        a['dens'], a['psi'], a['score'], [a['h']],
        b['dens'], b['psi'], b['score'], [b['h']],
    ])
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
