"""Proof: Python hc(modelName="VVV") and hcVVV on the same fixed inputs as hc-vvv-r.R.

Run from packages/mclust:
    /home/ahmed/killr_projects/killr/.venv/bin/python proof/hc-vvv-py.py

Writes docs/output/hc-vvv-python.txt in the record layout of hc-vvv-r.R:
"case|key<TAB>values". Keys per case: dim, hc (the 2 x m merge matrix, column-major),
merge, height and order from the hclust fields, and time_ms, the median of 20 timed
calls of the translated function (time.perf_counter, milliseconds) after one untimed call.
"""

from __future__ import annotations

import math
import statistics
import sys
import time
from pathlib import Path

import numpy as np

PKG = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG))

from mclust.hc import _partition, _prep, hc  # noqa: E402
from mclust.hc_variants import hcVVV  # noqa: E402
from mclust.plot_hc import as_hclust_loglik, as_hclust_merge  # noqa: E402

# Fixed inputs, the same values as hc-vvv-r.R. math.sin and math.cos are the C library
# functions R calls, so the inputs are bit-identical to R's.
i_a = np.arange(1, 91)
g_a = (i_a - 1) // 30
xa = np.column_stack([
    ((i_a * 37) % 11) / 11 + 2.5 * g_a + 0.05 * i_a / 90,
    ((i_a * 23) % 13) / 13 + 1.5 * g_a + 0.4 * (((i_a * 37) % 11) / 11) + 0.01 * i_a,
])

i_b = np.arange(1, 61)
g_b = (i_b - 1) // 30
xb = np.array([[math.sin(0.37 * a) + 2.5 * g + 0.05 * a / 60] for a, g in zip(i_b.tolist(), g_b.tolist())])


def mk3(i, g):
    n = len(i)
    x = np.zeros((n, 3))
    for r, (a, gg) in enumerate(zip(i.tolist(), g.tolist())):
        for j in range(1, 4):
            x[r, j - 1] = (math.sin(0.37 * a + 1.3 * j) + 0.4 * math.cos(0.11 * a * j)
                           + 1.5 * gg * (j / 3) + 0.05 * a / n * j)
    return x


i_c = np.arange(1, 121)
g_c = (i_c - 1) // 60
xc = mk3(i_c, g_c)

i_d = np.arange(1, 84)
g_d = np.where(i_d <= 40, 0, np.where(i_d <= 80, 1, 2))
xd = mk3(i_d, g_d)

example = np.array([[1, 2], [2, 1], [8, 9], [9, 8], [4, 4]], dtype=float)

cases = [
    {"id": "A1-svd", "fun": "hc", "x": xa[g_a == 0], "use": "SVD", "partition": None},
    {"id": "A2-svd", "fun": "hc", "x": xa[g_a == 1], "use": "SVD", "partition": None},
    {"id": "A3-svd", "fun": "hc", "x": xa[g_a == 2], "use": "SVD", "partition": None},
    {"id": "A2-vars", "fun": "hc", "x": xa[g_a == 1], "use": "VARS", "partition": None},
    {"id": "A2-partition-svd", "fun": "hc", "x": xa[g_a == 1], "use": "SVD",
     "partition": np.repeat(np.arange(1, 11), 3)},
    {"id": "A2-std", "fun": "hc", "x": xa[g_a == 1], "use": "STD", "partition": None},
    {"id": "A2-pcs", "fun": "hc", "x": xa[g_a == 1], "use": "PCS", "partition": None},
    {"id": "A2-pcr", "fun": "hc", "x": xa[g_a == 1], "use": "PCR", "partition": None},
    {"id": "A2-sph", "fun": "hc", "x": xa[g_a == 1], "use": "SPH", "partition": None},
    {"id": "B1-svd", "fun": "hc", "x": xb[g_b == 0], "use": "SVD", "partition": None},
    {"id": "C1-svd", "fun": "hc", "x": xc[g_c == 0], "use": "SVD", "partition": None},
    {"id": "D1-svd", "fun": "hc", "x": xd[g_d == 0], "use": "SVD", "partition": None},
    {"id": "hcVVV-example", "fun": "hcVVV", "x": example, "use": None,
     "partition": np.array([1, 1, 2, 2, 3])},
    {"id": "hcVVV-A2", "fun": "hcVVV", "x": xa[g_a == 1], "use": None, "partition": None},
]


def run_case(cs):
    if cs["fun"] == "hcVVV":
        return hcVVV(cs["x"], partition=cs["partition"])
    return hc(cs["x"], modelName="VVV", use=cs["use"], partition=cs["partition"])


def fmt(values):
    arr = np.asarray(values, dtype=float).ravel(order="F")
    return " ".join("%.17g" % v for v in arr)


def initial_of(out, cs):
    """The initialPartition attribute: set by hc(), and by hand for hcVVV()."""
    init = getattr(out, "initialPartition", None)
    if init is not None:
        return np.asarray(init).reshape(-1)
    return _partition(cs["partition"], cs["x"].shape[0]).astype(int)


lines = []
for cs in cases:
    out = run_case(cs)
    x = cs["x"]
    n = x.shape[0]
    pairs = np.asarray(out, dtype=float)
    lines.append(f"{cs['id']}|dim\t{fmt(pairs.shape)}")
    lines.append(f"{cs['id']}|hc\t{fmt(pairs)}")
    # R: data = the prepared Z for hc(), the input itself for hcVVV().
    if cs["fun"] == "hcVVV":
        z = x
    else:
        z = _prep(x, cs["use"])
    obj = {"pairs": pairs, "data": z, "modelName": "VVV", "initialPartition": initial_of(out, cs)}
    what = "merge" if z.shape[1] == 1 else "loglik"
    hcl = as_hclust_merge(obj) if what == "merge" else as_hclust_loglik(obj)
    lines.append(f"{cs['id']}|what\t{what}")
    lines.append(f"{cs['id']}|merge\t{fmt(hcl['merge'])}")
    lines.append(f"{cs['id']}|height\t{fmt(hcl['height'])}")
    lines.append(f"{cs['id']}|order\t{fmt(hcl['order'])}")

for cs in cases:
    run_case(cs)
    elapsed = []
    for _ in range(20):
        started = time.perf_counter()
        run_case(cs)
        elapsed.append((time.perf_counter() - started) * 1000)
    lines.append(f"{cs['id']}|time_ms\t{'%.17g' % statistics.median(elapsed)}")

out_path = PKG / "docs" / "output" / "hc-vvv-python.txt"
out_path.parent.mkdir(parents=True, exist_ok=True)
out_path.write_text("\n".join(lines) + "\n")
print(f"{len(lines)} records written to {out_path.relative_to(PKG)}")
