import importlib.util
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from proof._mclust_dr_subsel_fixtures import load_dr_fixture

_spec = importlib.util.spec_from_file_location(
    "mclust_dr_subsel1cycle",
    Path(__file__).resolve().parents[1] / "mclust" / "mclust_dr_subsel1cycle.py",
)
_mod = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(_mod)


def flatten(out):
    rows = [float(x) for x in out["subset"]]
    for key in ("G", "BIC", "BIC.dif"):
        for row in out["tab"]:
            rows.append(float(row[key]))
    return rows


def one():
    dr = load_dr_fixture()
    out = _mod.MclustDRsubsel1cycle(dr, g=[1, 2, 3], model_names=["VEI", "EEE"], verbose=False)
    return flatten(out)


value = one()
elapsed = []
for _ in range(20):
    t0 = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - t0) * 1000)

for item in value:
    print(f"{item:.17g}")
print(f"{statistics.median(elapsed):.17g}")
