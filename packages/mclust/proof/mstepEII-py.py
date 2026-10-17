import statistics
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mclust.mstep_models import mstepEII

# Deterministic inputs shared with mstepEII-r.R.
i = np.arange(20)
x = np.array([[((7 * a + 13 * b) % 17) / 4 - 2 for b in range(3)] for a in i], dtype=float)
z = np.column_stack([((3 * i + c) % 7 + 1) / 8 for c in (0, 5, 10)])


def my_prior(data, G, modelName, **kwargs):
    p = data.shape[1] if data.ndim == 2 else 1
    mean = data.mean(axis=0) if data.ndim == 2 else float(np.mean(data))
    return {"shrinkage": 0.5, "mean": mean, "scale": 2.0, "dof": p + 3}


prior = {"functionName": my_prior}


def vals(f):
    p = f["parameters"]
    v = p["variance"]
    return (list(p["pro"]) + list(np.ravel(p["mean"], order="F")) + [v["sigmasq"]]
            + list(np.ravel(v["sigma"], order="F")) + [f["returnCode"]])


def one():
    return mstepEII(x, z)


value = vals(mstepEII(x, z)) + vals(mstepEII(x, z, prior=prior))
elapsed = []
for _ in range(20):
    t0 = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - t0) * 1000)
print("\n".join("%.17g" % v for v in value))
print("%.17g" % statistics.median(elapsed))
