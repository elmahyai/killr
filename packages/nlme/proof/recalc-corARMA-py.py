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
from nlme.corarma import corARMA
from nlme.glsapvar import ConLin
from nlme.initialize import Initialize
from nlme.recalc import recalc

SUBJ = {"Subject": ["a", "a", "a", "a", "b", "b", "b", "b", "c", "c", "c"]}


def one():
    a = Initialize(corARMA([0.3, -0.2, 0.1], form="~ 1 | Subject", p=2, q=1), SUBJ)
    b = Initialize(corARMA([0.4], form="~ 1 | Subject", p=0, q=1), SUBJ)
    c1 = Initialize(corARMA([0.5], form="~ 1 | Subject", p=1, q=0), SUBJ)
    parts = []
    for model in (a, b, c1):
        con = ConLin(
            Xy=np.arange(1, 23, dtype=np.float64).reshape(11, 2, order="F"),
            dims={"N": 11, "p": 2},
            logLik=0.5,
        )
        r = recalc(model, con)
        parts.append(np.ravel(r.Xy, order="F"))
        parts.append(np.asarray([float(r.logLik)], dtype=np.float64))
    return np.concatenate(parts).astype(np.float64)


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
