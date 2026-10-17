import statistics
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
_py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
_site = ROOT / ".venv" / "lib" / _py_ver / "site-packages"
sys.path[:0] = [
    str(ROOT / "packages" / "nlme"),
    str(_site),
    str(ROOT / "crates" / "onecomp"),
]
from nlme.pdmat import fingerprint_pd_mat
from nlme.pdnatural import pdNatural


def one():
    m3 = np.array([[4, 1.2, 0.5], [1.2, 3, 0.7], [0.5, 0.7, 2]], dtype=np.float64)
    m2 = np.array([[4, 1.2], [1.2, 3]], dtype=np.float64)
    return np.concatenate(
        [
            fingerprint_pd_mat(pdNatural(m3)),
            fingerprint_pd_mat(pdNatural(m2)),
            fingerprint_pd_mat(pdNatural(np.array([0.1, -0.2, 0.3]))),
        ]
    )


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(
    '{"value":[%s],"median_ms":%.17g}'
    % (",".join("%.17g" % float(part) for part in value), statistics.median(elapsed))
)
