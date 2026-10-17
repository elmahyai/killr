import statistics
import time
import numpy as np
from quantreg.rqss import qss, rqss

x = 2 * np.sin(np.arange(1, 41, dtype=float))
y = -0.4 * x + np.sin(x) + 0.3 * np.cos(5 * np.arange(1, 41, dtype=float))
data = {"y": y, "x": x}

def one():
    out = []
    for cons in ("I", "C"):
        q = qss(x, constraint=cons, lambda_=2)
        out += [q.knots, q.F.toarray().reshape(-1), q.A.toarray().reshape(-1),
                q.R.toarray().reshape(-1), q.r, [q.lambda_]]
        f = rqss(f"y ~ qss(x, constraint='{cons}', lambda=2)", data, tau=0.5)
        out += [f.qss[0].xyz.reshape(-1), f.coef, [f.fidelity]]
    return np.concatenate([np.asarray(v, dtype=float).reshape(-1) for v in out])

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
