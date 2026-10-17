import statistics
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mclust.mstep_vei_vii_vvi import mstep_vii


def my_prior(data, G, modelName, shrinkage, mean, scale, dof):
    return {"shrinkage": shrinkage, "mean": mean, "scale": scale, "dof": dof}


i = np.arange(1, 41, dtype=float)
x = np.column_stack([np.sin(i), 0.7 * np.cos(i) + 0.1 * i, 0.5 * np.sin(1.3 * i) + i / 20])
w = np.column_stack([1 + np.cos(i), 2 + np.sin(i / 2), 1.5 + np.cos(i / 3)])
s3 = w[:, 0] + w[:, 1] + w[:, 2]
z3 = w / s3[:, None]
s2 = w[:, 0] + w[:, 1]
z2 = np.column_stack([w[:, 0], w[:, 1]]) / s2[:, None]
pri = {"functionName": my_prior, "shrinkage": 0.5, "mean": np.array([0.1, -0.2, 0.3]), "scale": 2.0, "dof": 5}


def pack(m):
    v = m["parameters"]
    var = v["variance"]
    return np.concatenate([
        np.ravel(v["pro"], order="F"),
        np.ravel(v["mean"], order="F"),
        np.ravel(var["sigmasq"], order="F"),
        np.ravel(var["sigma"], order="F"),
        np.array([m["returnCode"]], dtype=float),
    ])


def one():
    a1 = mstep_vii(x, z3)
    a2 = mstep_vii(x, z2)
    a3 = mstep_vii(x, z3, prior=pri)
    return np.concatenate([pack(a1), pack(a2), pack(a3)])


value = one()
elapsed = []
for _ in range(20):
    t0 = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - t0) * 1000)
print("\n".join("%.17g" % v for v in value))
print("%.17g" % statistics.median(elapsed))
