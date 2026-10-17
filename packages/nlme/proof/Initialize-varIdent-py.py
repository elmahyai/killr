import statistics
import sys
import time
from pathlib import Path

import types

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
if "nlme" not in sys.modules:
    _pkg = types.ModuleType("nlme")
    _pkg.__path__ = [str(ROOT / "nlme")]
    sys.modules["nlme"] = _pkg

from nlme.initialize import Initialize
from nlme.var_ident import _NlmeFrame, coef, var_weights, varIdent


def one():
    data = _NlmeFrame(
        {
            "y": np.arange(1, 10, dtype=np.float64),
            "grp": np.array(["A", "A", "B", "B", "C", "C", "A", "B", "C"], dtype=object),
        }
    )
    vf1 = Initialize(varIdent(value={"B": 2.0, "C": 3.0}, form="~1 | grp"), data)
    vf2 = Initialize(
        varIdent(value={"B": 2.0}, fixed={"C": 3.0}, form="~1 | grp"),
        data,
    )
    vf3 = Initialize(varIdent(form="~1"), data)
    return np.concatenate(
        [
            np.ravel(coef(vf1, unconstrained=True).values),
            np.ravel(coef(vf1, unconstrained=False, allCoef=True).values),
            np.ravel(var_weights(vf1)),
            np.asarray([vf1.log_lik], dtype=np.float64),
            np.ravel(coef(vf2, unconstrained=True).values),
            np.ravel(coef(vf2, unconstrained=False, allCoef=True).values),
            np.ravel(var_weights(vf2)),
            np.asarray([vf2.log_lik], dtype=np.float64),
            np.ravel(coef(vf3, unconstrained=True).values),
            np.ravel(var_weights(vf3)),
            np.asarray([vf3.log_lik], dtype=np.float64),
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
