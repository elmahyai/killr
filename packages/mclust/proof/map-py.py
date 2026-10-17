import importlib.util
import statistics
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
_module_path = Path(__file__).resolve().parent.parent / "mclust" / "map_util.py"
_spec = importlib.util.spec_from_file_location("map_util", _module_path)
assert _spec and _spec.loader
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
map_fn = _mod.map


def one():
    z = np.array(
        [[0.9, 0.05, 0.05], [0.1, 0.8, 0.1], [0.2, 0.2, 0.6]],
        dtype=float,
    )
    return map_fn(z)


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
for item in value:
    print("%.17g" % item)
print("%.17g" % statistics.median(elapsed))
