import statistics
import sys
import time
import types
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
if "nlme" not in sys.modules:
    _pkg = types.ModuleType("nlme")
    _pkg.__path__ = [str(ROOT / "nlme")]
    sys.modules["nlme"] = _pkg

from nlme.corlin import corLin, initialize
from nlme.cormatrix import corMatrix

DATA = {
    "x": [0.0, 1.0, 0.5, 2.0],
    "y": [0.0, 0.0, 1.0, 0.5],
}


def one():
    cs = initialize(corLin(2.5, form="~ x + y", metric="eu"), DATA)
    return np.ravel(corMatrix(cs), order="F")


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
