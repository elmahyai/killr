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

from nlme.corcompsymm import corCompSymm, initialize
from nlme.corfactor import corFactor

DATA = {
    "y": list(range(1, 13)),
    "Subject": ["A", "A", "A", "A", "B", "B", "B", "B", "C", "C", "C", "C"],
}


def one():
    cs1 = initialize(corCompSymm(0.5, form="~ 1 | Subject"), DATA)
    factor = corFactor(cs1)
    return np.concatenate(
        [
            np.asarray(factor.values, dtype=np.float64),
            np.asarray([factor.log_det], dtype=np.float64),
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
