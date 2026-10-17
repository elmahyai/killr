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

from nlme.corsymm import coef, corSymm


def one():
    cs1 = corSymm(form="~ 1 | Subject")
    free = coef(cs1, unconstrained=True).values
    return np.concatenate(
        [
            np.asarray(cs1.value, dtype=np.float64),
            np.asarray(free, dtype=np.float64),
        ]
    )


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
parts = ",".join("%.17g" % float(part) for part in value)
print('{"value":[%s],"median_ms":%.17g}' % (parts, statistics.median(elapsed)))
