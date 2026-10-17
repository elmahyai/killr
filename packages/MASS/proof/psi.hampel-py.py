import importlib.util
import statistics
import time
from pathlib import Path

import numpy as np

_MODULE = Path(__file__).resolve().parents[1] / "mass" / "psi_hampel.py"
_SPEC = importlib.util.spec_from_file_location("psi_hampel", _MODULE)
assert _SPEC is not None and _SPEC.loader is not None
_psi_hampel_mod = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_psi_hampel_mod)
psi_hampel = _psi_hampel_mod.psi_hampel


def one():
    u = np.array([-10.0, -5.0, -3.0, 0.0, 3.0, 5.0, 10.0])
    return np.concatenate(
        [
            np.asarray(psi_hampel(u), dtype=float).reshape(-1),
            np.asarray(psi_hampel(u, deriv=1), dtype=float).reshape(-1),
        ]
    )


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
flat = np.asarray(value, dtype=float).reshape(-1)
print("\n".join("%.17g" % item for item in flat))
print("%.17g" % statistics.median(elapsed))
