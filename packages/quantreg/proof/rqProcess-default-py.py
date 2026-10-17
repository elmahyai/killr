import statistics
import time
import numpy as np
A = np.loadtxt("/home/ahmed/killr_projects/killr/packages/quantreg/quantreg/data/check_design.txt")
X = A[:, :3]
y = A[:, 3]
taus = np.arange(1, 100) / 100
from quantreg.khmal import rq_process
def one():
    a = rq_process(X, y, taus, null_h="location")
    b = rq_process(X, y, taus, null_h="location-scale")
    return np.concatenate([
        a['qtaus'], a['Vhat'].ravel(order='F'), a['vhat'].ravel(order='F'), [a['n']],
        b['qtaus'], b['Vhat'].ravel(order='F'), b['vhat'].ravel(order='F'), [b['n']],
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
