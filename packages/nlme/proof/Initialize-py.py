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

from nlme.corlin import corLin
from nlme.corlin import corMatrix as corlin_matrix
from nlme.corratio import corRatio
from nlme.corratio import corMatrix as corratio_matrix
from nlme.corspher import corSpher
from nlme.corspher import corMatrix as corspher_matrix
from nlme.initialize import Initialize

DATA = {
    "x": [0.0, 1.0, 0.5, 2.0],
    "y": [0.0, 0.0, 1.0, 0.5],
}


def one():
    a = Initialize(corLin(2.5, form="~ x + y", metric="eu"), DATA)
    b = Initialize(corRatio(1.8, form="~ x + y", metric="eu"), DATA)
    d = Initialize(corSpher(2.5, form="~ x + y", metric="eu"), DATA)
    return np.concatenate(
        [
            np.ravel(corlin_matrix(a), order="F"),
            np.ravel(corratio_matrix(b), order="F"),
            np.ravel(corspher_matrix(d), order="F"),
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
