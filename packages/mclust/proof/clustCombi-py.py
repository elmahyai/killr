import statistics
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/mclust")
from mclust.clust_combi import clust_combi

proof_dir = Path(__file__).resolve().parent
G = 6
mod = {
    "data": np.loadtxt(proof_dir / "clustCombi_data.csv"),
    "z": np.loadtxt(proof_dir / "clustCombi_z.csv"),
    "G": G,
}


def flatten(out):
    vals = []
    for k in range(G, 0, -1):
        vals.extend(out["combiz"][k].reshape(-1, order="F"))
    for k in range(G - 1, 0, -1):
        vals.extend(out["combiM"][k].reshape(-1, order="F"))
    for k in range(G, 0, -1):
        vals.extend(out["classification"][k].reshape(-1))
    return vals


def one():
    return flatten(clust_combi(object=mod))


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
for item in value:
    print("%.17g" % item)
print("%.17g" % statistics.median(elapsed))
