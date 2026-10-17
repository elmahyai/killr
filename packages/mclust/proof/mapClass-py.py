import importlib.util
import statistics
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
_module_path = Path(__file__).resolve().parent.parent / "mclust" / "map_class.py"
_spec = importlib.util.spec_from_file_location("map_class", _module_path)
assert _spec and _spec.loader
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
mapClass = _mod.mapClass


def flatten(out):
    vals = []
    for key in sorted(out["aTOb"].keys(), key=lambda x: (len(x), x)):
        vals.extend(out["aTOb"][key])
    for key in sorted(out["bTOa"].keys(), key=lambda x: (len(x), x)):
        vals.extend(out["bTOa"][key])
    return vals


def one():
    a = np.array([1, 1, 2, 2, 3], dtype=int)
    b = np.array([1, 2, 2, 3, 3], dtype=int)
    return flatten(mapClass(a, b))


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
for item in value:
    print("%.17g" % item)
print("%.17g" % statistics.median(elapsed))
