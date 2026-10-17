import importlib.util
import statistics
import sys
import time
from pathlib import Path

import numpy as np

_module_path = Path(__file__).resolve().parent.parent / "mclust" / "logsumexp.py"
_spec = importlib.util.spec_from_file_location("logsumexp", _module_path)
assert _spec and _spec.loader
_mod = importlib.util.module_from_spec(_spec)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
_spec.loader.exec_module(_mod)
logsumexp = _mod.logsumexp


def one():
    x = np.array([-1.2, -0.5, -2.1, -0.3, -1.0, -1.8], dtype=float).reshape(2, 3, order="F")
    v = np.array([0.0, np.log(0.3), np.log(0.7)])
    return logsumexp(x, v)


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
for item in value:
    print("%.17g" % item)
print("%.17g" % statistics.median(elapsed))
