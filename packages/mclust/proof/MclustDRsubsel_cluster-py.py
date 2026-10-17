import importlib.util
import statistics
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from proof._mclust_dr_subsel_fixtures import load_dr_fixture

_spec = importlib.util.spec_from_file_location(
    "mclust_dr_subsel_cluster",
    Path(__file__).resolve().parents[1] / "mclust" / "mclust_dr_subsel_cluster.py",
)
_mod = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(_mod)


def one():
    dr = load_dr_fixture()
    out = _mod.MclustDRsubsel_cluster(dr, g=[1, 2, 3], model_names=["VEI", "EEE"], verbose=False)
    b = np.asarray(out["basisx"], dtype=float)
    return [float(out["numdir"]), float(out["lambda"]), *b.reshape(-1, order="F").tolist()]


value = one()
elapsed = []
for _ in range(20):
    t0 = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - t0) * 1000)

for item in value:
    print(f"{item:.17g}")
print(f"{statistics.median(elapsed):.17g}")
