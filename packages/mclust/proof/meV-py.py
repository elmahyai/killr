import statistics
import sys
import time

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/mclust")

import numpy as np

from mclust.me_v import me_v
from mclust.model_metadata import priorControl


def flat(*parts):
    out = []
    for part in parts:
        out.extend(np.asarray(part, dtype=float).ravel(order="F").tolist())
    return out


def pack(fit):
    info = fit["info"]
    return flat(
        fit["z"],
        fit["parameters"]["mean"],
        fit["parameters"]["variance"]["sigmasq"],
        fit["parameters"]["pro"],
        [fit["loglik"]],
        [info["iterations"], info["error"]],
        [fit["returnCode"]],
    )


def one():
    idx = np.arange(1, 61)
    x1 = np.sin(idx * 0.37) * 1.3 + np.where(idx % 2 == 0, 3.0, -2.0)
    zu = 1 / (1 + np.exp(-(x1 - 0.5) * 1.5))
    ZU = np.column_stack([zu, 1 - zu])
    return pack(me_v(x1, ZU)) + pack(me_v(x1, ZU, prior=priorControl()))


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
for item in value:
    print("%.17g" % item)
print("%.17g" % statistics.median(elapsed))
