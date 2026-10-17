import statistics
import sys
import time
import types
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
# Load the nlme modules without running nlme/__init__.py (it imports phenoModel).
if "nlme" not in sys.modules:
    _pkg = types.ModuleType("nlme")
    _pkg.__path__ = [str(ROOT / "nlme")]
    sys.modules["nlme"] = _pkg
from nlme.corar1 import coef as coef_ar1
from nlme.corarma import coef, corARMA
from nlme.corfactor import corFactor
from nlme.initialize import Initialize
from nlme.logdet import logDet

SUBJ = {"Subject": ["a", "a", "a", "a", "b", "b", "b", "b", "c", "c", "c"]}


def one():
    a = Initialize(corARMA([0.3, -0.2, 0.1], form="~ 1 | Subject", p=2, q=1), SUBJ)
    b = Initialize(corARMA([0.4], form="~ 1 | Subject", p=0, q=1), SUBJ)
    c1 = Initialize(corARMA([0.5], form="~ 1 | Subject", p=1, q=0), SUBJ)
    return np.concatenate(
        [
            np.ravel(a.value),
            np.asarray([a.max_lag], dtype=np.float64),
            np.ravel(corFactor(a).values),
            np.asarray([logDet(a)], dtype=np.float64),
            np.ravel(coef(a, unconstrained=False).values),
            np.ravel(b.value),
            np.asarray([b.max_lag], dtype=np.float64),
            np.ravel(corFactor(b).values),
            np.asarray([logDet(b)], dtype=np.float64),
            np.ravel(coef(b, unconstrained=False).values),
            np.ravel(np.asarray([c1.value], dtype=np.float64)),
            np.ravel(corFactor(c1).values),
            np.asarray([logDet(c1)], dtype=np.float64),
            np.ravel(coef_ar1(c1, unconstrained=False).values),
        ]
    ).astype(np.float64)


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
