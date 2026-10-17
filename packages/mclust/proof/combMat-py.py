import importlib.util
import statistics
import time
from pathlib import Path

import numpy as np

_comb_mat_path = Path(__file__).resolve().parents[1] / "mclust" / "comb_mat.py"
_spec = importlib.util.spec_from_file_location("mclust_comb_mat", _comb_mat_path)
_mod = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(_mod)
combMat = _mod.combMat


def one():
    mats = [
        combMat(5, 2, 4),
        combMat(5, 4, 2),
        combMat(3, 1, 2),
        combMat(6, 2, 5),
        combMat(4, 1, 1),
        combMat(5, np.array([], dtype=float), 3),
        combMat(5, 2, np.array([], dtype=float)),
    ]
    return np.concatenate([m.ravel(order="F") for m in mats])


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
for item in value:
    print("%.17g" % item)
print("%.17g" % statistics.median(elapsed))
