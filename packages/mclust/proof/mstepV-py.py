import statistics
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mclust.mstep_models import mstepV

# Deterministic inputs shared with mstepV-r.R.
k = np.arange(20)
x = ((7 * k) % 17) / 4 - 2
z = np.column_stack([((3 * k + c) % 7 + 1) / 8 for c in (0, 5, 10)])


def my_prior(data, G, modelName, **kwargs):
    p = data.shape[1] if data.ndim == 2 else 1
    mean = data.mean(axis=0) if data.ndim == 2 else float(np.mean(data))
    return {"shrinkage": 0.5, "mean": mean, "scale": 2.0, "dof": p + 3}


prior = {"functionName": my_prior}


def vals(f):
    p = f["parameters"]
    return list(p["pro"]) + list(p["mean"]) + list(p["variance"]["sigmasq"]) + [f["returnCode"]]


def one():
    return mstepV(x, z)


value = vals(mstepV(x, z)) + vals(mstepV(x, z, prior=prior))
elapsed = []
for _ in range(20):
    t0 = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - t0) * 1000)
print("\n".join("%.17g" % v for v in value))
print("%.17g" % statistics.median(elapsed))
