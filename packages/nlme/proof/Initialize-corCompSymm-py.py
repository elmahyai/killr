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

from nlme.corcompsymm import coef, corCompSymm
from nlme.initialize import Initialize

DATA = {
    "Subject": ["a", "a", "a", "a", "b", "b", "b", "b", "c", "c", "c"],
}


def one():
    cc0 = Initialize(corCompSymm(0.5, form="~ 1 | Subject"), DATA)
    cc1 = Initialize(corCompSymm(-0.2, form="~ 1 | Subject"), DATA)
    return np.concatenate(
        [
            np.asarray([cc0.value], dtype=np.float64),
            np.asarray(coef(cc0, unconstrained=True).values, dtype=np.float64).ravel(),
            np.asarray([cc0.inf], dtype=np.float64),
            np.asarray(cc0.factor, dtype=np.float64).ravel(),
            np.asarray([cc0.log_det], dtype=np.float64),
            np.asarray(coef(cc0, unconstrained=False).values, dtype=np.float64).ravel(),
            np.asarray([cc1.value], dtype=np.float64),
            np.asarray([cc1.inf], dtype=np.float64),
            np.asarray(cc1.factor, dtype=np.float64).ravel(),
            np.asarray([cc1.log_det], dtype=np.float64),
            np.asarray(coef(cc1, unconstrained=False).values, dtype=np.float64).ravel(),
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
