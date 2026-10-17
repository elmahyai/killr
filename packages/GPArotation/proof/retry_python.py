import csv
import sys
import time

import numpy as np

sys.path.insert(0, 'packages/GPArotation')
sys.path.insert(0, 'packages/boot')
import GPArotation as g
from boot import rng

A = np.array([[.8,.1,.2],[.2,.7,.1],[.1,.2,.9],[.6,.2,.3],[.2,.8,.4]], float)
seed = 20261017


def prep(name):
    if name == 'Random.Start':
        rng.set_seed(seed)


cases = {
    'Random.Start': lambda: g.Random_Start(3),
    'oblimax': lambda: g.oblimax(A, maxit=200),
    'bifactorQ': lambda: g.bifactorQ(A, maxit=200),
    'lpT': lambda: g.lpT(A, maxit=200),
    'lpQ': lambda: g.lpQ(A, maxit=200),
    'GPForth.lp': lambda: g.GPForth_lp(A, maxit=200),
    'GPFoblq.lp': lambda: g.GPFoblq_lp(A, maxit=200),
}

rvals = {}
with open('packages/GPArotation/docs/output/retry_r.csv') as fh:
    for row in csv.reader(fh):
        rvals[row[0]] = (float(row[1]), np.array([float(x) for x in row[2:]]))

out_lines = []
for name, fn in cases.items():
    prep(name)
    result = fn()
    if name == 'Random.Start':
        pv = np.asarray(result, float).ravel(order='F')
    else:
        pv = np.r_[result['loadings'].ravel(order='F'), result['Table'][-1, 1]]
    ts = []
    for _ in range(20):
        prep(name)
        t = time.perf_counter()
        fn()
        ts.append((time.perf_counter() - t) * 1000)
    r_ms, rv = rvals[name]
    d = np.abs(pv - rv)
    d = d[np.isfinite(d)]
    maxd = float(np.max(d)) if len(d) else 0.0
    py_ms = float(np.median(ts))
    speed = r_ms / py_ms if py_ms else float('nan')
    line = (f'{name} max_abs_diff={maxd:.3e} matches={maxd <= 1e-8} '
            f'r_ms={r_ms:.6f} python_ms={py_ms:.6f} speedup={speed:.3f}')
    print(line)
    out_lines.append(line)

with open('packages/GPArotation/docs/output/retry_python.txt', 'w') as fh:
    fh.write('\n'.join(out_lines) + '\n')
