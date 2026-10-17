import statistics
import sys
import time
from pathlib import Path

import numpy as np

# interp is not installed in the project venv; load its Python package from the repo.
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "interp"))

A = np.loadtxt("/home/ahmed/killr_projects/killr/packages/quantreg/quantreg/data/check_design.txt")
Xs = np.column_stack([
    np.array([0.1, 0.5, 0.9, 0.3, 0.7, 0.2]),
    np.array([0.2, 0.4, 0.1, 0.8, 0.6, 0.3]),
])
X = np.column_stack([A[:, 1], A[:, 2]])


def vec(v):
    if v is None:
        return np.array([-1.0])
    v = np.asarray(v, dtype=float).reshape(-1)
    return np.concatenate([np.array([v.shape[0]], dtype=float), v])


def mat(M):
    if M is None:
        return np.array([-1.0])
    dense = M.toarray()
    return np.concatenate([np.array(dense.shape, dtype=float), dense.reshape(-1)])


def pack(s):
    return np.concatenate([
        vec(s["x"]["x"]),
        vec(s["x"]["y"]),
        mat(s["F"]),
        mat(s["A"]),
        np.array([float(s["lambda"])]),
        mat(s["R"]),
        vec(s["r"]),
    ])


def one():
    from quantreg.rqss import qss2
    n = qss2(Xs, constraint="N", lambda_=2)
    v = qss2(X, constraint="V", lambda_=1.5)
    c = qss2(X, constraint="C", lambda_=0.5)
    return np.concatenate([pack(n), pack(v), pack(c)])


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
