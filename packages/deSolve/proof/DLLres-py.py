import json
import statistics
import sys
import time

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/deSolve")
from deSolve.DLLres import DLLres

pars = np.array([1.0, 1e6, 1.0], dtype=np.float64)
y = np.array([2.0, 3.0, 6.0], dtype=np.float64)
dy = np.array([0.0, 0.0, 0.0], dtype=np.float64)
prod = np.column_stack(
    [
        np.arange(0, 101, 10, dtype=np.float64),
        np.linspace(0.1, 0.5, 11, dtype=np.float64),
    ]
)
outnames = ["CONC", "Prod"]
eval_times = np.arange(0, 50.1, 2.5, dtype=np.float64)


def chemres_callable(t, state, ydot, parms, prod_rate):
    del t
    k = parms[0]
    ka = parms[1]
    r_rate = parms[2]
    ra = ka * state[2]
    rb = ka / k * state[0] * state[1]
    delta = np.array(
        [
            -ydot[0] + ra - rb,
            -ydot[1] + ra - rb - r_rate * state[1],
            -ydot[2] - ra + rb + prod_rate,
        ],
        dtype=np.float64,
    )
    var = np.array([state[0] + state[1] + state[2], prod_rate], dtype=np.float64)
    return delta, var


def one():
    vals = []
    for t in eval_times:
        out = DLLres(
            res=chemres_callable,
            times=t,
            y=y,
            dy=dy,
            parms=pars,
            dllname="deSolve",
            initfunc="initparms",
            initforc="initforcs",
            forcings=prod,
            nout=2,
            outnames=outnames,
        )
        vals.extend(out["delta"].tolist())
        vals.extend(np.asarray(out["var"]).tolist())
    return vals


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

print(
    json.dumps(
        {
            "value": [float(item) for item in value],
            "median_ms": statistics.median(elapsed),
        }
    )
)
