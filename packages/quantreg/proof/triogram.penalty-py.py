import statistics
import sys
import time
from pathlib import Path

import numpy as np

# interp is not installed in the project venv; load its Python package from the repo.
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "interp"))

A = np.loadtxt("/home/ahmed/killr_projects/killr/packages/quantreg/quantreg/data/check_design.txt")
xs = np.array([0.1, 0.5, 0.9, 0.3, 0.7, 0.2])
ys = np.array([0.2, 0.4, 0.1, 0.8, 0.6, 0.3])
xd = A[:, 1]
yd = A[:, 2]


def mat(M):
    dense = M.toarray()
    return np.concatenate([np.array(dense.shape, dtype=float), dense.reshape(-1)])


def one():
    from quantreg.rqss import triogram_penalty
    a = triogram_penalty(xs, ys)
    b = triogram_penalty(xd, yd)
    return np.concatenate([mat(a), mat(b)])


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
