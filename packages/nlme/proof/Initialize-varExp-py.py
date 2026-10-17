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
from nlme.initialize import Initialize
from nlme.var_power import coef, var_weights
from nlme.varexp import varExp

DAT = {"age": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0], "Sex": ["F", "F", "M", "M", "F", "M"]}


def one():
    g1 = Initialize(varExp(0.2, form="~age|Sex"), DAT)
    s1 = Initialize(varExp(0.3, form="~age"), DAT)
    u1 = Initialize(varExp(form="~age"), DAT)
    return np.concatenate(
        [
            np.ravel(coef(g1, unconstrained=False, allCoef=True).values),
            np.ravel(var_weights(g1)),
            np.asarray([g1.log_lik]),
            np.ravel(coef(s1, unconstrained=True).values),
            np.ravel(var_weights(s1)),
            np.asarray([s1.log_lik]),
            np.ravel(coef(u1, unconstrained=True).values),
            np.ravel(var_weights(u1)),
            np.asarray([u1.log_lik]),
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
