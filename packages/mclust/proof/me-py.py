"""Python side of the `me` proof. Same fixed inputs and output layout as me-r.R."""

import statistics
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mclust.me import me  # noqa: E402

# Fixed inputs.
# Case A: one-dimensional, n = 40, G = 2 (E, V, X models).
# Case B: two-dimensional, n = 40, G = 2.
# Case C: three-dimensional, n = 60, G = 3.
ia = np.arange(1, 41)
ga = (ia > 20).astype(float)
wa = ((ia * 7) % 19) / 19
za = np.column_stack([0.2 + 0.6 * wa, 0.8 - 0.6 * wa])
xa = ((ia * 37) % 11) / 11 + 2.5 * ga
xb = np.column_stack([((ia * 37) % 11) / 11 + 2.5 * ga, ((ia * 23) % 13) / 13 + 1.5 * ga])
ic = np.arange(1, 61)
xc = np.zeros((60, 3))
for j in range(1, 4):
    xc[:, j - 1] = ((ic * (3 * j + 5)) % 17) / 17 + 0.25 * ((ic + j) % 3)
rc = np.zeros((60, 3))
for k in range(1, 4):
    rc[:, k - 1] = 1 + ((ic * (k + 2)) % 7)
zc = rc / rc.sum(axis=1, keepdims=True)

one_d = ["E", "V", "X"]
multi = ["EII", "VII", "EEI", "VEI", "EVI", "VVI", "EEE", "EVE", "VEE", "VVE",
         "EEV", "VEV", "EVV", "VVV", "XII", "XXI", "XXX"]
specs = []
for m in one_d:
    specs.append({"case": "A", "model": m, "data": xa, "z": za})
for m in multi:
    specs.append({"case": "B", "model": m, "data": xb, "z": za})
    specs.append({"case": "C", "model": m, "data": xc, "z": zc})


def fields_of(o):
    out = {}
    out["returnCode"] = o.get("returnCode")
    out["loglik"] = o.get("loglik")
    out["z"] = o.get("z")
    p = o.get("parameters", {})
    out["pro"] = p.get("pro")
    out["mean"] = p.get("mean")
    v = p.get("variance", {})
    for nm in ["Sigma", "sigma", "sigmasq", "scale", "shape", "orientation",
               "cholsigma", "cholSigma"]:
        out[nm] = v.get(nm)
    return {k: val for k, val in out.items() if val is not None}


def fmt(x):
    a = np.asarray(x, dtype=float).ravel(order="F")
    return " ".join("nan" if np.isnan(v) else "%.17g" % v for v in a)


def me_call(s):
    return me(s["data"], s["model"], s["z"], warn=False)


def run_all():
    return [me_call(s) for s in specs]


# One untimed call over all specs, which also gives the values to compare.
results = run_all()
lines = []
for s, o in zip(specs, results):
    for nm, val in fields_of(o).items():
        lines.append(f"{s['case']}|{s['model']}|{nm}\t{fmt(val)}")

elapsed = []
for _ in range(20):
    t0 = time.perf_counter()
    run_all()
    elapsed.append((time.perf_counter() - t0) * 1000)

print("\n".join(lines))
print("TIMING_MEDIAN_MS\t%.17g" % statistics.median(elapsed))
