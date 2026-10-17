import statistics
import time
import numpy as np
A = np.loadtxt("/home/ahmed/killr_projects/killr/packages/quantreg/quantreg/data/check_design.txt")
xa = np.array([0.1, 0.5, 0.1, 0.9, 0.5, 0.3, 0.7, 0.2])
ya = np.array([0.2, 0.4, 0.2, 0.1, 0.4, 0.8, 0.6, 0.3])
xc = A[:6, 1]
yc = A[:6, 2]
dums = {"x": [0.25, 0.65], "y": [0.5, 0.45]}
def flat(F):
    M = F.toarray()
    return np.concatenate([np.array(M.shape, dtype=float), M.reshape(-1)])
def one():
    from quantreg.rqss import triogram_fidelity
    a = triogram_fidelity(xa, ya)
    b = triogram_fidelity(xa, ya, dummies=dums)
    c0 = triogram_fidelity(xc, yc)
    return np.concatenate([
        a["x"], a["y"], flat(a["F"]),
        b["x"], b["y"], flat(b["F"]), np.array(b["dummies"]["x"]), np.array(b["dummies"]["y"]),
        c0["x"], c0["y"], flat(c0["F"]),
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
