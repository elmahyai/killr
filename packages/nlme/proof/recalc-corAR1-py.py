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
from nlme.corar1 import corAR1
from nlme.glsapvar import ConLin
from nlme.initialize import Initialize
from nlme.recalc import recalc

SUBJ = {"Subject": ["a", "a", "a", "a", "b", "b", "b", "b", "c", "c", "c"]}


def one():
    ca = Initialize(corAR1(0.2, form="~ 1 | Subject"), SUBJ)
    con = ConLin(
        Xy=np.arange(1, 23, dtype=np.float64).reshape(11, 2, order="F"),
        dims={"N": 11, "p": 2},
        logLik=0.5,
    )
    r = recalc(ca, con)
    return np.concatenate([np.ravel(r.Xy, order="F"), np.asarray([float(r.logLik)])])

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
