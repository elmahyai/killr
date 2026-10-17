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
from nlme.initialize import Initialize

DATA = {
    "Subject": ["a", "a", "a", "a", "b", "b", "b", "b", "c", "c", "c"],
}


def one():
    cs0 = Initialize(corSymm(form="~ 1 | Subject"), DATA)
    cs1 = Initialize(
        corSymm([0.3, 0.1, 0.2, 0.05, 0.1, 0.25], form="~ 1 | Subject"),
        DATA,
    )
    return np.concatenate(
        [
            np.asarray(cs0.value, dtype=np.float64).ravel(),
            np.asarray(coef(cs0, unconstrained=True).values, dtype=np.float64).ravel(),
            np.asarray(cs0.factor, dtype=np.float64).ravel(),
            np.asarray([cs0.log_det], dtype=np.float64),
            np.asarray([cs0.max_cov], dtype=np.float64),
            np.asarray(cs1.value, dtype=np.float64).ravel(),
            np.asarray(coef(cs1, unconstrained=False).values, dtype=np.float64).ravel(),
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
