import statistics
import sys
import time

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/mclust")
from mclust.me_evi import meEVI
from mclust.em_control import em_control


def my_prior(data, G, modelName, shrinkage, mean, scale, dof):
    return {"shrinkage": shrinkage, "mean": mean, "scale": scale, "dof": dof}


prior_p = {"functionName": my_prior, "shrinkage": 0.1, "mean": [1.2, 0.8], "scale": 0.9, "dof": 4}

i = np.arange(1, 41)
g = (i > 20).astype(float)
x1 = ((i * 37) % 11) / 11 + 2.5 * g
x2 = ((i * 23) % 13) / 13 + 1.5 * g
X = np.column_stack([x1, x2])
w = ((i * 7) % 19) / 19
z2 = np.column_stack([0.2 + 0.6 * w, 0.8 - 0.6 * w])
z3 = np.column_stack([0.9 * (0.2 + 0.6 * w), 0.9 * (0.8 - 0.6 * w), np.full(40, 0.1)])


def flat(r):
    variance = r["parameters"]["variance"]
    values = [
        r["loglik"],
        r["returnCode"],
        r["info"]["iterations"],
        r["info"]["error"],
        variance["scale"],
    ]
    values += list(np.asarray(variance["shape"], dtype=float).ravel(order="F"))
    values += list(np.asarray(r["parameters"]["mean"], dtype=float).ravel(order="F"))
    values += list(np.asarray(r["parameters"]["pro"], dtype=float).ravel(order="F"))
    values += list(np.asarray(variance["sigma"], dtype=float).ravel(order="F"))
    if r["parameters"]["Vinv"] is not None:
        values.append(r["parameters"]["Vinv"])
    values += list(np.asarray(r["z"], dtype=float).ravel(order="F"))
    return values


def one():
    ctl = em_control()
    a = meEVI(X, z2, prior=None, control=ctl, Vinv=None, warn=False)
    b = meEVI(X, z2, prior=prior_p, control=ctl, Vinv=None, warn=False)
    c = meEVI(X, z3, prior=None, control=ctl, Vinv=0, warn=False)
    return [float(v) for v in flat(a) + flat(b) + flat(c)]


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
for item in value:
    print("%.17g" % item)
print("%.17g" % statistics.median(elapsed))
