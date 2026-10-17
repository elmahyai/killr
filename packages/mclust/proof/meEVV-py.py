import statistics
import sys
import time

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/mclust")

import numpy as np

from mclust.me_evv import me_evv
from mclust.model_metadata import priorControl


def flat(*parts):
    out = []
    for part in parts:
        out.extend(np.asarray(part, dtype=float).ravel(order="F").tolist())
    return out


def pack(fit):
    info = fit["info"]
    var = fit["parameters"]["variance"]
    return flat(
        fit["z"],
        fit["parameters"]["mean"],
        var["scale"],
        var["shape"],
        var["orientation"],
        var["sigma"],
        fit["parameters"]["pro"],
        [fit["loglik"]],
        [info["iterations"], info["error"]],
        [fit["returnCode"]],
    )


def one():
    idx = np.arange(1, 61)
    x1 = np.sin(idx * 0.37) * 1.3 + np.where(idx % 2 == 0, 3.0, -2.0)
    x2 = np.cos(idx * 0.53) * 1.1 + 0.4 * x1 + np.where(idx % 3 == 0, 2.5, 0.0)
    X = np.column_stack([x1, x2])
    z1 = 1 / (1 + np.exp(-(x1 - 0) * 1.2))
    Z = np.column_stack([z1, 1 - z1])
    # With a prior, the R return code is the only value that carries over.
    return pack(me_evv(X, Z)) + [me_evv(X, Z, prior=priorControl())["returnCode"]]


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
for item in value:
    print("%.17g" % item)
print("%.17g" % statistics.median(elapsed))
