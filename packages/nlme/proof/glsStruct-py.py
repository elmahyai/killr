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

from nlme.corar1 import coef, corAR1
from nlme.glsstruct import glsStruct
from nlme.varexp import varExp


def one():
    cs = corAR1(0.2, form="~ 1 | Mare")
    a = glsStruct(corStruct=cs)
    b = glsStruct()
    d = glsStruct(corStruct=cs, varStruct=varExp(0.2, form="~age"))
    return np.asarray(
        [
            len(a),
            len(b),
            len(d),
            float("glsStruct" in a.classes),
            float("modelStruct" in a.classes),
            float(a.names == ("corStruct",)),
            float(d.names == ("corStruct", "varStruct")),
            float(type(d.varStruct).__name__ == "VarExp"),
            float(coef(a.corStruct, unconstrained=True).values[0]),
            float(coef(a.corStruct, unconstrained=False).values[0]),
        ],
        dtype=np.float64,
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
