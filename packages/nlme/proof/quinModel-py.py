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

from nlme.quinmodel import quinModel

Subject = np.array([1, 1, 1, 2, 2, 2], dtype=np.float64)
times = np.array([0, 1, 3, 0, 2, 5], dtype=np.float64)
conc = np.array([np.nan, np.nan, 1.2, np.nan, np.nan, 0.85], dtype=np.float64)
dose = np.array([100, np.nan, np.nan, 150, np.nan, np.nan], dtype=np.float64)
interval = np.full(6, np.nan, dtype=np.float64)
lV = np.full(6, np.log(50.0), dtype=np.float64)
lKa = np.full(6, np.log(1.2), dtype=np.float64)
lCl = np.full(6, np.log(2.5), dtype=np.float64)


def one():
    return quinModel(Subject, times, conc, dose, interval, lV, lKa, lCl)


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
