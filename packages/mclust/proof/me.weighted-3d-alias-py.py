import statistics
import sys
import time

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/mclust")

import numpy as np

from mclust.mstep_loglik_icl import me_weighted

# Usage: python proof/me.weighted-3d-alias-py.py <modelName>
model = sys.argv[1]
i = np.arange(1, 41)
if model == "X":
    n, d, G = 40, 1, 2
    y = (i / 10 + ((i * i) % 7) / 3).reshape(-1, 1)
else:
    n, d, G = 40, 3, 3
    y = np.column_stack([
        i / 20 + ((i * 37) % 23) / 5,
        ((i * 11) % 17) / 4 - i / 30 + (i % 3),
        i / 13 + ((i * 7) % 19) / 6 - (i % 4) / 5,
    ])
raw = np.zeros((n, G))
for j in range(1, G + 1):
    raw[:, j - 1] = 1 + 2 * (((i % G) + 1) == j) + 0.3 * ((i + j) % 4)
z = raw / raw.sum(axis=1, keepdims=True)
w = (1 + (i % 5)).astype(float)


def sigma_of(variance):
    s = variance.get("sigma")
    if s is None:
        s = variance["sigmasq"]
    return np.asarray(s, dtype=float).ravel(order="F")


def fit_values(fit):
    p = fit["parameters"]
    named = [("loglik", float(fit["loglik"])), ("bic", float(fit["bic"]))]
    named += [(f"z{k + 1}", float(v)) for k, v in enumerate(
        np.asarray(fit["z"], dtype=float).ravel(order="F"))]
    named += [(f"pro{k + 1}", float(v)) for k, v in enumerate(
        np.asarray(p["pro"], dtype=float).ravel(order="F"))]
    named += [(f"mean{k + 1}", float(v)) for k, v in enumerate(
        np.asarray(p["mean"], dtype=float).ravel(order="F"))]
    named += [(f"sigma{k + 1}", float(v)) for k, v in enumerate(sigma_of(p["variance"]))]
    return named


def one():
    a = me_weighted(y, model, z)
    b = me_weighted(y, model, z, weights=w)
    return {"A": fit_values(a), "B": fit_values(b)}


res = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000.0)
for case in ("A", "B"):
    for name, value in res[case]:
        print("%s_%s %.17g" % (case, name, value))
print("translated_ms %.17g" % statistics.median(elapsed))
